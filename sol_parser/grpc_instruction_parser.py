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
    IncludeOnlyFilter,
    SubscribeUpdateTransactionInfo,
)
from .inner_instruction_parser import parse_inner_instruction
from .instructions import parse_instruction_unified
from .merger import merge_dex_events
from .pumpfun_fee_enrich import enrich_create_v2_observed_fee_recipient


def detect_pumpfun_create_from_logs(log_messages: List[str]) -> bool:
    """对齐 Rust ``detect_pumpfun_create``：Program data 前缀匹配 create 日志。"""
    needle = "Program data: G3KpTd7rY3Y"
    return any(needle in log for log in log_messages)


def should_parse_instructions(filter: Optional[EventTypeFilter]) -> bool:
    if filter is None:
        return True
    inc = getattr(filter, "include_only", None)
    if inc is None or not inc:
        return True
    need = {
        EventType.PUMP_FUN_MIGRATE,
        EventType.METEORA_DAMM_V2_SWAP,
        EventType.METEORA_DAMM_V2_ADD_LIQUIDITY,
        EventType.METEORA_DAMM_V2_CREATE_POSITION,
        EventType.METEORA_DAMM_V2_CLOSE_POSITION,
        EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY,
        EventType.METEORA_DAMM_V2_INITIALIZE_POOL,
    }
    return any(t in need for t in inc)


def merge_instruction_events(
    events: List[Tuple[int, Optional[int], DexEvent]],
) -> List[DexEvent]:
    """对齐 Rust ``merge_instruction_events``。"""
    if not events:
        return []
    events = sorted(events, key=lambda x: (x[0], x[1] if x[1] is not None else (1 << 30)))
    result: List[DexEvent] = []
    pending_outer: Optional[Tuple[int, DexEvent]] = None

    for outer_idx, inner_idx, event in events:
        if inner_idx is None:
            if pending_outer is not None:
                result.append(pending_outer[1])
            pending_outer = (outer_idx, event)
        else:
            if pending_outer is not None:
                po_idx, mut_outer = pending_outer
                pending_outer = None
                if po_idx == outer_idx:
                    merge_dex_events(mut_outer, event)
                    result.append(mut_outer)
                else:
                    result.append(mut_outer)
                    result.append(event)
            else:
                result.append(event)

    if pending_outer is not None:
        result.append(pending_outer[1])
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
        msg, meta, sig, slot, int(info.index), None, None, filter, tx
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
    f: EventTypeFilter = filter if filter is not None else IncludeOnlyFilter([])

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

    invokes_raw: Dict[bytes, List[Tuple[int, int]]] = {}

    is_created_buy = detect_pumpfun_create_from_logs(list(meta.log_messages))

    result: List[Tuple[int, Optional[int], DexEvent]] = []

    for i, ix in enumerate(msg.instructions):
        pid_idx = ix.program_id_index
        raw_pid = get_key_raw(pid_idx)
        if raw_pid:
            invokes_raw.setdefault(raw_pid, []).append((i, -1))
        pid = get_key_b58(pid_idx)
        data = bytes(ix.data)
        acct_bytes = bytes(ix.accounts)
        accounts = [get_key_b58(b) for b in acct_bytes]
        ev = parse_instruction_unified(
            data, accounts, signature, slot, tx_index, block_time_us, grpc_us, f, pid
        )
        if ev:
            result.append((i, None, ev))

    for inner in meta.inner_instructions:
        outer_idx = inner.index
        for j, inner_ix in enumerate(inner.instructions):
            raw_pid = get_key_raw(inner_ix.program_id_index)
            if raw_pid:
                invokes_raw.setdefault(raw_pid, []).append((int(outer_idx), j))
            pid = get_key_b58(inner_ix.program_id_index)
            data = bytes(inner_ix.data)
            ev = parse_inner_instruction(
                data,
                pid,
                _meta_dict(signature, slot, tx_index, block_time_us, grpc_us, recent_bh),
                f,
                is_created_buy,
            )
            if ev:
                result.append((int(outer_idx), j, ev))

    merged = merge_instruction_events(result)
    enrich_create_v2_observed_fee_recipient(merged)

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
