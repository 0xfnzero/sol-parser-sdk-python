"""Yellowstone 交易：outer + inner 指令解析、合并、CreateV2 fee 回填（对齐 Rust ``grpc/instruction_parser`` 主流程）。"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

import base58

from .account_dispatcher import fill_accounts_with_owned_keys, fill_data
from .event_types import DexEvent
from .grpc_types import (
    EventMetadata,
    EventType,
    EventTypeFilter,
    SubscribeUpdateTransactionInfo,
    event_type_filter_allows_instruction_parsing,
)
from .inner_instruction_parser import parse_inner_instruction
from .instructions import parse_inner_compiled_instruction_if_supported, parse_instruction_unified
from .merger import try_merge_dex_events
from .pumpfun_fee_enrich import enrich_pumpfun_same_tx_post_merge


def collect_program_invokes(msg: Any, meta: Any) -> Dict[bytes, List[Tuple[int, int]]]:
    """从已解析的 ``Message`` + ``TransactionStatusMeta`` 收集各 program_id 的 (outer, inner) 指令索引。"""
    invokes_raw: Dict[bytes, List[Tuple[int, int]]] = {}
    static_keys: List[bytes] = [bytes(x) for x in msg.account_keys]
    w_keys: List[bytes] = [bytes(x) for x in meta.loaded_writable_addresses]
    r_keys: List[bytes] = [bytes(x) for x in meta.loaded_readonly_addresses]
    keys_len = len(static_keys)
    wlen = len(w_keys)

    def get_key_raw(i: int) -> Optional[bytes]:
        if i < keys_len:
            return static_keys[i]
        if i < keys_len + wlen:
            return w_keys[i - keys_len]
        j = i - keys_len - wlen
        if j < len(r_keys):
            return r_keys[j]
        return None

    for i, ix in enumerate(msg.instructions):
        raw_pid = get_key_raw(ix.program_id_index)
        if raw_pid:
            invokes_raw.setdefault(raw_pid, []).append((i, -1))

    for inner in meta.inner_instructions:
        outer_idx = inner.index
        for j, inner_ix in enumerate(inner.instructions):
            raw_pid = get_key_raw(inner_ix.program_id_index)
            if raw_pid:
                invokes_raw.setdefault(raw_pid, []).append((int(outer_idx), j))

    return invokes_raw


def apply_account_fill_to_events(
    events: List[DexEvent],
    tx_pb: Any,
    meta_pb: Any,
) -> None:
    """对已解析的 ``solana_storage_pb2.Transaction`` + ``TransactionStatusMeta`` 应用账户填充 + ``fill_data``。"""
    if not events or tx_pb is None or meta_pb is None:
        return
    msg = tx_pb.message
    if not msg.account_keys and not msg.instructions:
        return
    invokes_raw = collect_program_invokes(msg, meta_pb)
    invokes_str: Dict[str, List[Tuple[int, int]]] = {
        base58.b58encode(k).decode("ascii"): v for k, v in invokes_raw.items()
    }
    for ev in events:
        fill_accounts_with_owned_keys(ev, meta_pb, tx_pb, invokes_raw)
        fill_data(ev, meta_pb, tx_pb, invokes_str)
    recent_bh = ""
    if msg.recent_blockhash:
        recent_bh = base58.b58encode(bytes(msg.recent_blockhash)).decode("ascii")
    for ev in events:
        if isinstance(ev.data, object) and hasattr(ev.data, "metadata"):
            m = ev.data.metadata
            if isinstance(m, EventMetadata) and recent_bh:
                m.recent_blockhash = recent_bh


def enrich_dex_events_with_subscribe_tx_info(
    events: List[DexEvent],
    info: SubscribeUpdateTransactionInfo,
) -> None:
    """对仅由日志解析得到的事件补全账户字段（对齐 Rust ``fill_accounts_with_owned_keys`` + ``fill_data``）。

    需要 ``info.transaction_raw`` / ``info.meta_raw``（Yellowstone 订阅里通常有）。
    无 raw 时静默跳过。
    """
    if not events:
        return
    try:
        from . import solana_storage_pb2 as sol_pb
    except ImportError:
        return
    if not info.transaction_raw or not info.meta_raw:
        return
    tx = sol_pb.Transaction()
    tx.ParseFromString(info.transaction_raw)
    meta = sol_pb.TransactionStatusMeta()
    meta.ParseFromString(info.meta_raw)
    apply_account_fill_to_events(events, tx, meta)


def detect_pumpfun_create_from_logs(log_messages: List[str]) -> bool:
    """对齐 Rust ``detect_pumpfun_create``：Program data 前缀匹配 create 日志。"""
    needle = "Program data: G3KpTd7rY3Y"
    return any(needle in log for log in log_messages)


def should_parse_instructions(filter: Optional[EventTypeFilter]) -> bool:
    if filter is None:
        return True
    inc = getattr(filter, "include_only", None)
    if inc is None:
        return True
    if not inc:
        return False
    return event_type_filter_allows_instruction_parsing(list(inc))


_DLMM_EVENT_TYPES = {
    EventType.METEORA_DLMM_SWAP,
    EventType.METEORA_DLMM_ADD_LIQUIDITY,
    EventType.METEORA_DLMM_REMOVE_LIQUIDITY,
    EventType.METEORA_DLMM_INITIALIZE_POOL,
    EventType.METEORA_DLMM_INITIALIZE_BIN_ARRAY,
    EventType.METEORA_DLMM_CREATE_POSITION,
    EventType.METEORA_DLMM_CLOSE_POSITION,
    EventType.METEORA_DLMM_CLAIM_FEE,
}


def _is_dlmm_event_cpi(data: bytes) -> bool:
    return len(data) >= 16 and (
        data[:8] == bytes((228, 69, 165, 46, 81, 203, 154, 29))
        or data[8:16] == bytes((155, 167, 108, 32, 122, 76, 173, 64))
    )


def merge_instruction_events(events: List[Tuple[Any, ...]]) -> List[DexEvent]:
    """对齐 Rust ``merge_instruction_events``。"""
    if not events:
        return []
    normalized = events if all(len(item) == 5 for item in events) else [
        (item[0], item[1], None, False, item[2]) if len(item) == 3 else item
        for item in events
    ]
    normalized.sort(key=lambda x: (x[0], 0 if x[1] is None else 1 + x[1]))
    result: List[DexEvent] = []
    outer_target: Optional[Tuple[int, int]] = None
    dlmm_targets: List[Tuple[int, Optional[int], int]] = []

    for outer_idx, inner_idx, stack_height, is_dlmm_event_cpi, event in normalized:
        if inner_idx is None:
            result.append(event)
            target_idx = len(result) - 1
            outer_target = (outer_idx, target_idx)
            dlmm_targets = (
                [(outer_idx, stack_height, target_idx)] if event.type in _DLMM_EVENT_TYPES else []
            )
            continue

        if is_dlmm_event_cpi:
            for candidate_idx in range(len(dlmm_targets) - 1, -1, -1):
                target_outer, target_height, target_idx = dlmm_targets[candidate_idx]
                direct_child = (
                    target_height is None
                    or stack_height is None
                    or stack_height == target_height + 1
                )
                if target_outer == outer_idx and direct_child:
                    del dlmm_targets[candidate_idx + 1:]
                    if try_merge_dex_events(result[target_idx], event):
                        break
            else:
                result.append(event)
            continue

        target_idx: Optional[int] = None
        if outer_target is not None and outer_target[0] == outer_idx:
            if try_merge_dex_events(result[outer_target[1]], event):
                target_idx = outer_target[1]
        if target_idx is None:
            result.append(event)
            target_idx = len(result) - 1

        if event.type in _DLMM_EVENT_TYPES:
            if stack_height is None:
                dlmm_targets.clear()
            else:
                while dlmm_targets and (
                    dlmm_targets[-1][0] != outer_idx
                    or (
                        dlmm_targets[-1][1] is not None
                        and dlmm_targets[-1][1] >= stack_height
                    )
                ):
                    dlmm_targets.pop()
            dlmm_targets.append((outer_idx, stack_height, target_idx))

    return result


def _meta_dict(
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
    recent_blockhash: str = "",
) -> dict:
    m: dict = {
        "signature": signature,
        "slot": slot,
        "tx_index": tx_index,
        "block_time_us": 0 if block_time_us is None else block_time_us,
        "grpc_recv_us": grpc_recv_us,
    }
    if recent_blockhash:
        m["recent_blockhash"] = recent_blockhash
    return m


def parse_instructions_enhanced_from_subscribe_tx_info(
    info: SubscribeUpdateTransactionInfo,
    slot: int,
    filter: Optional[EventTypeFilter] = None,
    block_time_us: Optional[int] = None,
    grpc_recv_us: Optional[int] = None,
) -> List[DexEvent]:
    """从 ``grpc_client`` 转换后的 ``SubscribeUpdateTransactionInfo``（raw 字节）解析指令事件。"""
    try:
        from . import solana_storage_pb2 as sol_pb
    except ImportError:
        return []
    if not info.transaction_raw or not info.meta_raw:
        return []
    tx = sol_pb.Transaction()
    tx.ParseFromString(info.transaction_raw)
    meta = sol_pb.TransactionStatusMeta()
    meta.ParseFromString(info.meta_raw)
    sig = base58.b58encode(bytes(info.signature)).decode("ascii") if info.signature else ""
    msg = tx.message
    if not msg.account_keys and not msg.instructions:
        return []
    return parse_instructions_enhanced_from_parsed(
        msg, meta, sig, slot, int(info.index), block_time_us, grpc_recv_us, filter, tx
    )


def parse_instructions_enhanced_from_parsed(
    msg: Any,
    meta: Any,
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: Optional[int],
    filter: Optional[EventTypeFilter],
    transaction_pb: Any = None,
) -> List[DexEvent]:
    """接受已 Parse 的 ``Message`` 与 ``TransactionStatusMeta``（来自 ``solana_storage_pb2``）。"""
    if not should_parse_instructions(filter):
        return []

    grpc_us = int(time.time() * 1_000_000) if grpc_recv_us is None else grpc_recv_us
    try:
        from . import solana_storage_pb2 as sol_pb
    except ImportError:
        return []

    if transaction_pb is None:
        tx_try = sol_pb.Transaction()
        tx_try.message.CopyFrom(msg)
        transaction_pb = tx_try

    recent_bh = ""
    if msg.recent_blockhash:
        recent_bh = base58.b58encode(bytes(msg.recent_blockhash)).decode("ascii")

    static_keys: List[bytes] = [bytes(x) for x in msg.account_keys]
    w_keys: List[bytes] = [bytes(x) for x in meta.loaded_writable_addresses]
    r_keys: List[bytes] = [bytes(x) for x in meta.loaded_readonly_addresses]
    keys_len = len(static_keys)
    wlen = len(w_keys)

    def get_key_raw(i: int) -> Optional[bytes]:
        if i < keys_len:
            return static_keys[i]
        if i < keys_len + wlen:
            return w_keys[i - keys_len]
        j = i - keys_len - wlen
        if j < len(r_keys):
            return r_keys[j]
        return None

    def get_key_b58(i: int) -> str:
        raw = get_key_raw(i)
        if raw is None:
            return ""
        return base58.b58encode(raw).decode("ascii")

    invokes_raw = collect_program_invokes(msg, meta)

    is_created_buy = detect_pumpfun_create_from_logs(list(meta.log_messages))

    result: List[Tuple[Any, ...]] = []

    for i, ix in enumerate(msg.instructions):
        pid_idx = ix.program_id_index
        pid = get_key_b58(pid_idx)
        data = bytes(ix.data)
        acct_bytes = bytes(ix.accounts)
        accounts = [get_key_b58(b) for b in acct_bytes]
        ev = parse_instruction_unified(
            data, accounts, signature, slot, tx_index, block_time_us, grpc_us, filter, pid
        )
        if ev:
            result.append((i, None, 1, False, ev))

    for inner in meta.inner_instructions:
        outer_idx = inner.index
        for j, inner_ix in enumerate(inner.instructions):
            pid = get_key_b58(inner_ix.program_id_index)
            data = bytes(inner_ix.data)
            accounts = [get_key_b58(b) for b in bytes(inner_ix.accounts)]
            ev = parse_inner_compiled_instruction_if_supported(
                data,
                accounts,
                signature,
                slot,
                tx_index,
                block_time_us,
                grpc_us,
                filter,
                pid,
            ) or parse_inner_instruction(
                data,
                pid,
                _meta_dict(signature, slot, tx_index, block_time_us, grpc_us, recent_bh),
                filter,
                is_created_buy,
            )
            if ev:
                result.append((
                    int(outer_idx),
                    j,
                    int(inner_ix.stack_height) if inner_ix.HasField("stack_height") else None,
                    pid == METEORA_DLMM_PROGRAM_ID and _is_dlmm_event_cpi(data),
                    ev,
                ))

    merged = merge_instruction_events(result)
    enrich_pumpfun_same_tx_post_merge(merged)

    invokes_str: Dict[str, List[Tuple[int, int]]] = {
        base58.b58encode(k).decode("ascii"): v for k, v in invokes_raw.items()
    }

    for ev in merged:
        fill_accounts_with_owned_keys(ev, meta, transaction_pb, invokes_raw)
        fill_data(ev, meta, transaction_pb, invokes_str)

    for ev in merged:
        if isinstance(ev.data, object) and hasattr(ev.data, "metadata"):
            m = ev.data.metadata
            if isinstance(m, EventMetadata):
                m.recent_blockhash = recent_bh
    return merged
