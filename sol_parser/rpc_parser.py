"""RPC Transaction Parser - 支持直接从 RPC 解析交易"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple, TypedDict, Union
from dataclasses import dataclass

import base58

from .dex_parsers import DexEvent, dispatch_program_data, parse_trade_from_data
from .grpc_types import EventTypeFilter, EventType, IncludeOnlyFilter
from .instructions import parse_instruction_unified
from .pumpfun_fee_enrich import enrich_create_v2_observed_fee_recipient


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
    accounts: Union[List[int], bytes]
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
    #: 该笔交易在区块中的序号（``getTransaction`` 的 ``transactionIndex``；单交易拉取时可能为 0）
    transaction_index: int = 0


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
    block_tx_index = int(getattr(tx, "transaction_index", 0) or 0)

    events: List[DexEvent] = []

    # 解析外层指令
    for i, ix in enumerate(msg.instructions):
        ev = _parse_rpc_instruction(
            ix,
            msg.account_keys,
            signature,
            slot,
            block_tx_index,
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
                block_tx_index,
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
            block_tx_index,
            block_time_us,
            grpc_recv_us,
            filter,
            is_created_buy,
            recent_blockhash,
        )
        if ev:
            if ev.type in (EventType.PUMP_FUN_CREATE, EventType.PUMP_FUN_CREATE_V2):
                is_created_buy = True
            events.append(ev)

    enrich_create_v2_observed_fee_recipient(events)

    tx_pb, meta_pb = rpc_response_to_solana_storage(tx)
    if tx_pb is not None and meta_pb is not None:
        from .grpc_instruction_parser import apply_account_fill_to_events

        apply_account_fill_to_events(events, tx_pb, meta_pb)

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
    acc_iter = ix.accounts if isinstance(ix.accounts, (list, tuple)) else list(ix.accounts)
    for acc_idx in acc_iter:
        if acc_idx < len(account_keys):
            accounts.append(account_keys[acc_idx])

    f: EventTypeFilter = filter if filter is not None else IncludeOnlyFilter([])
    return parse_instruction_unified(
        data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us, f, program_id
    )


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


def _ix_data_from_rpc(ix: dict) -> bytes:
    raw = ix.get("data")
    if raw is None or raw == "":
        return b""
    if isinstance(raw, str):
        try:
            return base58.b58decode(raw)
        except Exception:
            return b""
    return b""


def _account_keys_from_message(msg: dict) -> List[str]:
    keys = msg.get("accountKeys") or msg.get("account_keys") or []
    out: List[str] = []
    for k in keys:
        if isinstance(k, str):
            out.append(k)
        elif isinstance(k, dict):
            pk = k.get("pubkey") or k.get("pubKey")
            if pk:
                out.append(str(pk))
    return out


def _parse_rpc_compiled_ix(ix: dict, account_keys: List[str]) -> RpcCompiledInstruction:
    if "programIdIndex" in ix:
        pidx = int(ix["programIdIndex"])
    elif "programId" in ix:
        pid = ix["programId"]
        try:
            pidx = account_keys.index(pid)
        except ValueError:
            pidx = 0
    else:
        pidx = 0
    accounts = ix.get("accounts") or []
    if isinstance(accounts, str):
        try:
            accounts = list(base58.b58decode(accounts))
        except Exception:
            accounts = []
    elif not isinstance(accounts, list):
        accounts = []
    acc_list = [int(x) for x in accounts]
    return RpcCompiledInstruction(
        program_id_index=pidx,
        accounts=acc_list,
        data=_ix_data_from_rpc(ix),
    )


def rpc_get_transaction_result_dict_to_response(
    result: Optional[dict],
) -> Optional[RpcTransactionResponse]:
    """将 ``getTransaction`` 的 JSON ``result`` 转为 :class:`RpcTransactionResponse`。

    支持 ``encoding: json`` / ``jsonParsed`` 下的 ``transaction`` 对象；若为仅 ``base64`` 数组则返回 ``None``（需另行解码）。
    """
    if not result or not isinstance(result, dict):
        return None
    tfield = result.get("transaction")
    if tfield is None:
        return None
    if isinstance(tfield, list):
        return None
    if not isinstance(tfield, dict):
        return None

    slot = int(result.get("slot", 0))
    block_time = result.get("blockTime")
    if block_time is not None:
        block_time = int(block_time)
    tx_idx_raw = result.get("transactionIndex")
    if tx_idx_raw is None:
        tx_idx_raw = result.get("transaction_index")
    transaction_index = int(tx_idx_raw) if tx_idx_raw is not None else 0

    tx_body = tfield
    sigs = tx_body.get("signatures") or []
    if not isinstance(sigs, list):
        sigs = []
    msg_dict = tx_body.get("message")
    if not isinstance(msg_dict, dict):
        return None

    account_keys = _account_keys_from_message(msg_dict)
    instructions: List[RpcCompiledInstruction] = []
    for ix in msg_dict.get("instructions") or []:
        if not isinstance(ix, dict):
            continue
        if "programIdIndex" not in ix and "programId" not in ix:
            continue
        instructions.append(_parse_rpc_compiled_ix(ix, account_keys))

    header = None
    h = msg_dict.get("header")
    if isinstance(h, dict):
        header = RpcMessageHeader(
            num_required_signatures=int(h.get("numRequiredSignatures", 0)),
            num_readonly_signed_accounts=int(h.get("numReadonlySignedAccounts", 0)),
            num_readonly_unsigned_accounts=int(h.get("numReadonlyUnsignedAccounts", 0)),
        )

    lookups: List[RpcMessageAddressTableLookup] = []
    for lu in msg_dict.get("addressTableLookups") or []:
        if not isinstance(lu, dict):
            continue
        wi = lu.get("writableIndexes") or lu.get("writable_indexes") or []
        ri = lu.get("readonlyIndexes") or lu.get("readonly_indexes") or []
        ak = lu.get("accountKey") or lu.get("account_key") or ""
        lookups.append(
            RpcMessageAddressTableLookup(
                account_key=str(ak),
                writable_indexes=[int(x) for x in wi],
                readonly_indexes=[int(x) for x in ri],
            )
        )

    recent = msg_dict.get("recentBlockhash") or msg_dict.get("recent_blockhash") or ""
    message = RpcMessage(
        account_keys=account_keys,
        header=header,
        recent_blockhash=str(recent),
        instructions=instructions,
        address_table_lookups=lookups,
    )

    rpc_tx = RpcTransaction(signatures=[str(s) for s in sigs], message=message)

    meta_dict = result.get("meta")
    if meta_dict is None:
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
    else:
        inner_groups: List[RpcInnerInstructionGroup] = []
        for g in meta_dict.get("innerInstructions") or meta_dict.get("inner_instructions") or []:
            if not isinstance(g, dict):
                continue
            ixs: List[RpcCompiledInstruction] = []
            for ix in g.get("instructions") or []:
                if not isinstance(ix, dict):
                    continue
                ixs.append(_parse_rpc_compiled_ix(ix, account_keys))
            inner_groups.append(
                RpcInnerInstructionGroup(index=int(g.get("index", 0)), instructions=ixs)
            )
        loaded = None
        la = meta_dict.get("loadedAddresses") or meta_dict.get("loaded_addresses")
        if isinstance(la, dict):
            loaded = RpcLoadedAddresses(
                writable=[str(x) for x in la.get("writable", [])],
                readonly=[str(x) for x in la.get("readonly", [])],
            )
        logs = meta_dict.get("logMessages") or meta_dict.get("log_messages") or []
        if not isinstance(logs, list):
            logs = []
        meta = RpcTransactionMeta(
            fee=int(meta_dict.get("fee", 0)),
            pre_balances=[int(x) for x in meta_dict.get("preBalances") or meta_dict.get("pre_balances") or []],
            post_balances=[int(x) for x in meta_dict.get("postBalances") or meta_dict.get("post_balances") or []],
            log_messages=[str(x) for x in logs],
            inner_instructions=inner_groups,
            pre_token_balances=[],
            post_token_balances=[],
            loaded_addresses=loaded,
            compute_units_consumed=meta_dict.get("computeUnitsConsumed"),
        )

    return RpcTransactionResponse(
        slot=slot,
        block_time=block_time,
        meta=meta,
        transaction=rpc_tx,
        transaction_index=transaction_index,
    )


def rpc_response_to_solana_storage(
    rpc_tx: RpcTransactionResponse,
) -> Tuple[Optional[Any], Optional[Any]]:
    """将 :class:`RpcTransactionResponse` 转为 ``solana_storage_pb2`` 的 Transaction + TransactionStatusMeta。"""
    try:
        from . import solana_storage_pb2 as sol_pb
    except ImportError:
        return None, None
    if rpc_tx.transaction is None or rpc_tx.transaction.message is None:
        return None, None
    if rpc_tx.meta is None:
        return None, None

    tx = sol_pb.Transaction()
    for sig in rpc_tx.transaction.signatures:
        tx.signatures.append(base58.b58decode(sig))

    msg = rpc_tx.transaction.message
    out_msg = tx.message
    for k in msg.account_keys:
        out_msg.account_keys.append(base58.b58decode(k))
    if msg.recent_blockhash:
        out_msg.recent_blockhash = base58.b58decode(msg.recent_blockhash)
    for ix in msg.instructions:
        c = out_msg.instructions.add()
        c.program_id_index = ix.program_id_index
        acc = ix.accounts
        c.accounts = bytes(acc) if not isinstance(acc, bytes) else acc
        c.data = ix.data
    if msg.header:
        out_msg.header.num_required_signatures = msg.header.num_required_signatures
        out_msg.header.num_readonly_signed_accounts = msg.header.num_readonly_signed_accounts
        out_msg.header.num_readonly_unsigned_accounts = msg.header.num_readonly_unsigned_accounts
    for lu in msg.address_table_lookups:
        l = out_msg.address_table_lookups.add()
        l.account_key = base58.b58decode(lu.account_key)
        l.writable_indexes = bytes(lu.writable_indexes)
        l.readonly_indexes = bytes(lu.readonly_indexes)

    m = rpc_tx.meta
    meta = sol_pb.TransactionStatusMeta()
    meta.fee = m.fee
    meta.pre_balances.extend(m.pre_balances)
    meta.post_balances.extend(m.post_balances)
    meta.log_messages.extend(m.log_messages)
    for group in m.inner_instructions:
        g = meta.inner_instructions.add()
        g.index = group.index
        for ix in group.instructions:
            ii = g.instructions.add()
            ii.program_id_index = ix.program_id_index
            acc = ix.accounts
            ii.accounts = bytes(acc) if not isinstance(acc, bytes) else acc
            ii.data = ix.data
    if m.loaded_addresses:
        for w in m.loaded_addresses.writable:
            meta.loaded_writable_addresses.append(base58.b58decode(w))
        for r in m.loaded_addresses.readonly:
            meta.loaded_readonly_addresses.append(base58.b58decode(r))
    return tx, meta


def enrich_dex_events_from_rpc_get_transaction_result(
    events: List[DexEvent],
    result: Optional[dict],
) -> None:
    """对已有事件列表用 ``getTransaction`` 的 JSON ``result`` 做与 gRPC 相同的账户补全。"""
    resp = rpc_get_transaction_result_dict_to_response(result)
    if resp is None:
        return
    tx_pb, meta_pb = rpc_response_to_solana_storage(resp)
    if tx_pb is None or meta_pb is None:
        return
    from .grpc_instruction_parser import apply_account_fill_to_events

    apply_account_fill_to_events(events, tx_pb, meta_pb)

