"""RPC Transaction Parser - 支持直接从 RPC 解析交易"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union
from dataclasses import dataclass

import base58

from .dex_parsers import DexEvent, dispatch_program_data, parse_trade_from_data
from .grpc_types import EventTypeFilter, EventType


class ParseError(Exception):
    """RPC 解析错误"""
    def __init__(self, kind: str, message: str):
        self.kind = kind
        self.message = message
        super().__init__(f"{kind}: {message}")


@dataclass
class RpcCompiledInstruction:
    """编译指令"""
    program_id_index: int
    accounts: List[int]
    data: bytes


@dataclass
class RpcInnerInstructionGroup:
    """内部指令组"""
    index: int
    instructions: List[RpcCompiledInstruction]


@dataclass
class RpcTokenBalance:
    """Token 余额"""
    account_index: int
    mint: str
    ui_token_amount: Dict[str, Any]


@dataclass
class RpcLoadedAddresses:
    """加载地址"""
    writable: List[str]
    readonly: List[str]


@dataclass
class RpcTransactionMeta:
    """交易元数据"""
    fee: int
    pre_balances: List[int]
    post_balances: List[int]
    log_messages: List[str]
    inner_instructions: List[RpcInnerInstructionGroup]
    pre_token_balances: List[RpcTokenBalance]
    post_token_balances: List[RpcTokenBalance]
    loaded_addresses: Optional[RpcLoadedAddresses]
    compute_units_consumed: Optional[int]


@dataclass
class RpcMessageHeader:
    """消息头"""
    num_required_signatures: int
    num_readonly_signed_accounts: int
    num_readonly_unsigned_accounts: int


@dataclass
class RpcMessageAddressTableLookup:
    """地址表查找"""
    account_key: str
    writable_indexes: List[int]
    readonly_indexes: List[int]


@dataclass
class RpcMessage:
    """消息"""
    account_keys: List[str]
    header: Optional[RpcMessageHeader]
    recent_blockhash: str
    instructions: List[RpcCompiledInstruction]
    address_table_lookups: List[RpcMessageAddressTableLookup]


@dataclass
class RpcTransaction:
    """交易"""
    signatures: List[str]
    message: Optional[RpcMessage]


@dataclass
class RpcTransactionResponse:
    """RPC 交易响应"""
    slot: int
    block_time: Optional[int]
    meta: Optional[RpcTransactionMeta]
    transaction: Optional[RpcTransaction]


class RpcClient:
    """RPC 客户端接口"""
    def get_transaction(
        self,
        signature: str,
        max_supported_transaction_version: int = 0
    ) -> Optional[RpcTransactionResponse]:
        raise NotImplementedError


def parse_transaction_from_rpc(
    rpc_client: RpcClient,
    signature: str,
    filter: Optional[EventTypeFilter] = None,
) -> Tuple[List[DexEvent], Optional[ParseError]]:
    """通过 RPC 拉取交易并解析

    Args:
        rpc_client: RPC 客户端
        signature: 交易签名
        filter: 可选的事件类型过滤器

    Returns:
        (events, error) 元组
    """
    try:
        tx = rpc_client.get_transaction(signature, max_supported_transaction_version=0)
    except Exception as e:
        return [], ParseError("RpcError", f"Failed to fetch transaction: {e}")

    if tx is None:
        return [], ParseError("RpcError", "Transaction not found or null response (try archive RPC for old txs)")

    grpc_recv_us = int(time.time() * 1_000_000)
    return parse_rpc_transaction(tx, signature, filter, grpc_recv_us)


def parse_rpc_transaction(
    tx: RpcTransactionResponse,
    signature: str,
    filter: Optional[EventTypeFilter],
    grpc_recv_us: int,
) -> Tuple[List[DexEvent], Optional[ParseError]]:
    """解析已获取的 RPC 交易

    Args:
        tx: RPC 交易响应
        signature: 交易签名
        filter: 可选的事件类型过滤器
        grpc_recv_us: gRPC 接收时间戳（微秒）

    Returns:
        (events, error) 元组
    """
    if tx.transaction is None or tx.transaction.message is None:
        return [], ParseError("ConversionError", "Transaction message is nil")

    msg = tx.transaction.message
    meta = tx.meta
    if meta is None:
        meta = RpcTransactionMeta(
            fee=0,
            pre_balances=[],
            post_balances=[],
            log_messages=[],
            inner_instructions=[],
            pre_token_balances=[],
            post_token_balances=[],
            loaded_addresses=None,
            compute_units_consumed=None,
        )

    slot = tx.slot
    block_time_us = tx.block_time * 1_000_000 if tx.block_time else None

    events: List[DexEvent] = []

    # 解析外层指令
    for i, ix in enumerate(msg.instructions):
        ev = _parse_rpc_instruction(
            ix,
            msg.account_keys,
            signature,
            slot,
            i,
            block_time_us,
            grpc_recv_us,
            filter,
        )
        if ev:
            events.append(ev)

    # 解析内层指令
    for group in meta.inner_instructions:
        for ix in group.instructions:
            ev = _parse_rpc_instruction(
                ix,
                msg.account_keys,
                signature,
                slot,
                group.index,
                block_time_us,
                grpc_recv_us,
                filter,
            )
            if ev:
                events.append(ev)

    # 解析日志
    is_created_buy = False
    recent_blockhash = msg.recent_blockhash

    from .parser import parse_log_optimized

    for log in meta.log_messages:
        ev = parse_log_optimized(
            log,
            signature,
            slot,
            0,
            block_time_us,
            grpc_recv_us,
            filter,
            is_created_buy,
            recent_blockhash,
        )
        if ev:
            # 检查是否是 PumpFun Create 事件
            if ev.get("PumpFunCreate") or ev.get("PumpFunCreateV2"):
                is_created_buy = True
            events.append(ev)

    return events, None


def _parse_rpc_instruction(
    ix: RpcCompiledInstruction,
    account_keys: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
    filter: Optional[EventTypeFilter],
) -> Optional[DexEvent]:
    """解析 RPC 指令"""
    # 获取程序 ID
    if ix.program_id_index >= len(account_keys):
        return None
    program_id = account_keys[ix.program_id_index]

    # 解析指令数据
    data = ix.data
    if len(data) == 0:
        return None

    # 构建账户列表
    accounts = []
    for acc_idx in ix.accounts:
        if acc_idx < len(account_keys):
            accounts.append(account_keys[acc_idx])

    # 根据程序 ID 路由到相应的解析器
    if program_id == PUMPFUN_PROGRAM_ID:
        if filter and not _filter_includes_pumpfun(filter):
            return None
        return _parse_pumpfun_instruction(data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us)

    elif program_id == PUMPSWAP_PROGRAM_ID:
        if filter and not _filter_includes_pumpswap(filter):
            return None
        return _parse_pumpswap_instruction(data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us)

    elif program_id == METEORA_DAMM_V2_PROGRAM_ID:
        if filter and not _filter_includes_meteora_damm_v2(filter):
            return None
        return _parse_meteora_damm_instruction(data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us)

    return None


def _filter_includes_pumpfun(filter: EventTypeFilter) -> bool:
    """检查过滤器是否包含 PumpFun 相关类型"""
    pumpfun_types = [
        EventType.PUMP_FUN_TRADE,
        EventType.PUMP_FUN_BUY,
        EventType.PUMP_FUN_SELL,
        EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
        EventType.PUMP_FUN_CREATE,
        EventType.PUMP_FUN_CREATE_V2,
        EventType.PUMP_FUN_COMPLETE,
        EventType.PUMP_FUN_MIGRATE,
    ]
    for t in pumpfun_types:
        if filter.should_include(t):
            return True
    return False


def _filter_includes_pumpswap(filter: EventTypeFilter) -> bool:
    """检查过滤器是否包含 PumpSwap 相关类型"""
    pumpswap_types = [
        EventType.PUMP_SWAP_BUY,
        EventType.PUMP_SWAP_SELL,
        EventType.PUMP_SWAP_CREATE_POOL,
        EventType.PUMP_SWAP_LIQUIDITY_ADDED,
        EventType.PUMP_SWAP_LIQUIDITY_REMOVED,
    ]
    for t in pumpswap_types:
        if filter.should_include(t):
            return True
    return False


def _filter_includes_meteora_damm_v2(filter: EventTypeFilter) -> bool:
    """检查过滤器是否包含 Meteora DAMM V2 相关类型"""
    meteora_types = [
        EventType.METEORA_DAMM_V2_SWAP,
        EventType.METEORA_DAMM_V2_ADD_LIQUIDITY,
        EventType.METEORA_DAMM_V2_CREATE_POSITION,
        EventType.METEORA_DAMM_V2_CLOSE_POSITION,
        EventType.METEORA_DAMM_V2_INITIALIZE_POOL,
        EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY,
    ]
    for t in meteora_types:
        if filter.should_include(t):
            return True
    return False


def _parse_pumpfun_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 PumpFun 指令"""
    # 解析 discriminator (前 8 字节)
    if len(data) < 8:
        return None

    # 这里需要根据具体的指令格式解析
    # 暂时返回 None，需要实现具体的解析逻辑
    return None


def _parse_pumpswap_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 PumpSwap 指令"""
    if len(data) < 8:
        return None

    return None


def _parse_meteora_damm_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 Meteora DAMM 指令"""
    if len(data) < 8:
        return None

    return None


def convert_rpc_to_grpc(
    rpc_tx: RpcTransactionResponse,
) -> Tuple[Optional[Any], Optional[Any], Optional[ParseError]]:
    """将 RPC 格式转换为 gRPC 格式

    Returns:
        (grpc_meta, grpc_tx, error) 元组
    """
    try:
        from . import geyser_pb2
    except ImportError:
        return None, None, ParseError(
            "ImportError",
            "需要 protobuf 生成的代码。请从 https://github.com/rpcpool/yellowstone-grpc 获取 proto 文件并生成 Python 代码。"
        )

    meta = rpc_tx.meta
    if meta is None:
        return None, None, ParseError("ConversionError", "meta is nil")

    # 转换 TransactionStatusMeta
    grpc_meta = geyser_pb2.TransactionStatusMeta(
        fee=meta.fee,
        pre_balances=meta.pre_balances,
        post_balances=meta.post_balances,
        log_messages=meta.log_messages,
    )

    # 转换内部指令
    for group in meta.inner_instructions:
        grpc_group = grpc_meta.inner_instructions.add()
        grpc_group.index = group.index
        for ix in group.instructions:
            grpc_ix = grpc_group.instructions.add()
            grpc_ix.program_id_index = ix.program_id_index
            grpc_ix.accounts = bytes(ix.accounts)
            grpc_ix.data = ix.data

    # 转换加载的地址
    if meta.loaded_addresses:
        for addr in meta.loaded_addresses.writable:
            grpc_meta.loaded_writable_addresses.append(base58.b58decode(addr))
        for addr in meta.loaded_addresses.readonly:
            grpc_meta.loaded_readonly_addresses.append(base58.b58decode(addr))

    # 转换交易
    if rpc_tx.transaction is None:
        return None, None, ParseError("ConversionError", "transaction is nil")

    tx = rpc_tx.transaction
    grpc_tx = geyser_pb2.Transaction()

    # 转换签名
    for sig in tx.signatures:
        grpc_tx.signatures.append(base58.b58decode(sig))

    # 转换消息
    if tx.message:
        msg = tx.message
        grpc_msg = grpc_tx.message

        # 转换账户密钥
        for key in msg.account_keys:
            grpc_msg.account_keys.append(base58.b58decode(key))

        # 转换最近区块哈希
        if msg.recent_blockhash:
            grpc_msg.recent_blockhash = base58.b58decode(msg.recent_blockhash)

        # 转换指令
        for ix in msg.instructions:
            grpc_ix = grpc_msg.instructions.add()
            grpc_ix.program_id_index = ix.program_id_index
            grpc_ix.accounts = bytes(ix.accounts)
            grpc_ix.data = ix.data

        # 转换地址表查找
        for lookup in msg.address_table_lookups:
            grpc_lookup = grpc_msg.address_table_lookups.add()
            grpc_lookup.account_key = base58.b58decode(lookup.account_key)
            grpc_lookup.writable_indexes = bytes(lookup.writable_indexes)
            grpc_lookup.readonly_indexes = bytes(lookup.readonly_indexes)

        # 转换消息头
        if msg.header:
            grpc_msg.header.num_required_signatures = msg.header.num_required_signatures
            grpc_msg.header.num_readonly_signed_accounts = msg.header.num_readonly_signed_accounts
            grpc_msg.header.num_readonly_unsigned_accounts = msg.header.num_readonly_unsigned_accounts

    return grpc_meta, grpc_tx, None


# 程序 ID 常量
PUMPFUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMPSWAP_PROGRAM_ID = "pAMMBay6oceH9fJKBRdGP4LmT4saRGfEE7xmrCaGWpZ"
METEORA_DAMM_V2_PROGRAM_ID = "dammbaKJpFxX3onKJ23VvQeyn8r8zPqowyyPAPKFqG"
