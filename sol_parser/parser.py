from __future__ import annotations

import base58
import base64
import struct
import time
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from .dex_parsers import DexEvent, dispatch_program_data, parse_trade_from_data

if TYPE_CHECKING:
    from .grpc_types import SubscribeUpdateTransactionInfo
from .pumpfun_fee_enrich import enrich_create_v2_observed_fee_recipient


def _disc8(bs: bytes) -> int:
    return struct.unpack("<Q", bs)[0]


def decode_program_data_line(log: str) -> Optional[bytes]:
    p = "Program data: "
    i = log.find(p)
    if i < 0:
        return None
    s = log[i + len(p) :].strip()
    if len(s) > 2700:
        return None
    try:
        raw = base64.standard_b64decode(s)
    except Exception:
        return None
    if len(raw) < 8 or len(raw) > 2048:
        return None
    return raw


def _meta(
    sig: str,
    slot: int,
    tx_idx: int,
    block_us: Optional[int],
    grpc_us: int,
    recent_blockhash: str = "",
) -> dict:
    m: dict = {
        "signature": sig,
        "slot": slot,
        "tx_index": tx_idx,
        "block_time_us": 0 if block_us is None else block_us,
        "grpc_recv_us": grpc_us,
    }
    if recent_blockhash:
        m["recent_blockhash"] = recent_blockhash
    return m


def parse_log_optimized(
    log: str,
    signature: str,
    slot: int,
    tx_index: int = 0,
    block_time_us: Optional[int] = None,
    grpc_recv_us: Optional[int] = None,
    event_type_filter: Any = None,
    is_created_buy: bool = False,
    recent_blockhash: str = "",
) -> Optional[DexEvent]:
    """与 Go `ParseLogOptimized` 对齐；`event_type_filter` 预留与 TS 一致，当前未使用。"""
    _ = event_type_filter
    grpc = int(time.time() * 1_000_000) if grpc_recv_us is None else grpc_recv_us
    bt = 0 if block_time_us is None else block_time_us
    buf = decode_program_data_line(log)
    if not buf:
        return None
    disc = _disc8(buf[:8])
    data = buf[8:]
    meta = _meta(signature, slot, tx_index, block_time_us, grpc, recent_blockhash)
    return dispatch_program_data(disc, data, buf, meta, is_created_buy)


def parse_log_unified(
    log: str,
    signature: str,
    slot: int,
    block_time_us: Optional[int] = None,
    *,
    tx_index: int = 0,
) -> Optional[DexEvent]:
    grpc = int(time.time() * 1_000_000)
    return parse_log_optimized(
        log,
        signature,
        slot,
        tx_index,
        block_time_us,
        grpc,
        None,
        False,
        "",
    )


def parse_transaction_events(
    logs: List[str],
    signature: str,
    slot: int,
    block_time_us: Optional[int] = None,
    *,
    subscribe_tx_info: Optional["SubscribeUpdateTransactionInfo"] = None,
    tx_index: Optional[int] = None,
) -> List[DexEvent]:
    """对齐 Rust `parse_transaction_events` - 解析完整交易并返回所有 DEX 事件"""
    return parse_logs_only(
        logs,
        signature,
        slot,
        block_time_us,
        subscribe_tx_info=subscribe_tx_info,
        tx_index=tx_index,
    )


def parse_logs_only(
    logs: List[str],
    signature: str,
    slot: int,
    block_time_us: Optional[int] = None,
    *,
    subscribe_tx_info: Optional["SubscribeUpdateTransactionInfo"] = None,
    tx_index: Optional[int] = None,
) -> List[DexEvent]:
    """解析日志中的 Program data 事件。

    若传入 ``subscribe_tx_info`` 且含 ``transaction_raw`` / ``meta_raw``（Yellowstone 订阅），
    会在解析后调用 :func:`grpc_instruction_parser.enrich_dex_events_with_subscribe_tx_info`
    从指令账户补全 bonding_curve、creator_vault 等字段（与 Rust gRPC 路径一致）。

    ``tx_index`` 为区块内交易序号（与 gRPC ``SubscribeUpdateTransactionInfo.index`` 一致）。
    未显式传入且提供了 ``subscribe_tx_info`` 时，使用 ``subscribe_tx_info.index``。
    """
    resolved_tx_index = 0
    if tx_index is not None:
        resolved_tx_index = int(tx_index)
    elif subscribe_tx_info is not None:
        resolved_tx_index = int(getattr(subscribe_tx_info, "index", 0) or 0)
    out: List[DexEvent] = []
    for log in logs:
        ev = parse_log_unified(log, signature, slot, block_time_us, tx_index=resolved_tx_index)
        if ev:
            out.append(ev)
    enrich_create_v2_observed_fee_recipient(out)
    if subscribe_tx_info is not None:
        from .grpc_instruction_parser import enrich_dex_events_with_subscribe_tx_info

        enrich_dex_events_with_subscribe_tx_info(out, subscribe_tx_info)
    return out


def parse_transaction_events_streaming(
    logs: List[str],
    signature: str,
    slot: int,
    block_time_us: Optional[int],
    callback: Callable[[DexEvent], None],
    *,
    tx_index: int = 0,
) -> None:
    """对齐 Rust `parse_transaction_events_streaming`"""
    parse_logs_streaming(logs, signature, slot, block_time_us, callback, tx_index=tx_index)


def parse_logs_streaming(
    logs: List[str],
    signature: str,
    slot: int,
    block_time_us: Optional[int],
    callback: Callable[[DexEvent], None],
    *,
    tx_index: int = 0,
) -> None:
    """对齐 Rust `parse_logs_streaming` - 流式解析，每解析出一个事件立即回调"""
    for log in logs:
        ev = parse_log_unified(log, signature, slot, block_time_us, tx_index=tx_index)
        if ev:
            callback(ev)


class EventListener:
    """对齐 Rust `EventListener` trait"""

    def on_dex_event(self, event: DexEvent) -> None:
        raise NotImplementedError


def parse_transaction_with_listener(
    logs: List[str],
    signature: str,
    slot: int,
    block_time_us: Optional[int],
    listener: EventListener,
    *,
    subscribe_tx_info: Optional["SubscribeUpdateTransactionInfo"] = None,
    tx_index: Optional[int] = None,
) -> None:
    """对齐 Rust `parse_transaction_with_listener`"""
    events = parse_logs_only(
        logs,
        signature,
        slot,
        block_time_us,
        subscribe_tx_info=subscribe_tx_info,
        tx_index=tx_index,
    )
    for ev in events:
        listener.on_dex_event(ev)


class StreamingEventListener:
    """对齐 Rust `StreamingEventListener` trait"""

    def on_dex_event_streaming(self, event: DexEvent) -> None:
        raise NotImplementedError


def parse_transaction_with_streaming_listener(
    logs: List[str],
    signature: str,
    slot: int,
    block_time_us: Optional[int],
    listener: StreamingEventListener,
) -> None:
    """对齐 Rust `parse_transaction_with_streaming_listener`"""

    def callback(ev: DexEvent) -> None:
        listener.on_dex_event_streaming(ev)

    parse_logs_streaming(logs, signature, slot, block_time_us, callback)


def parse_log(
    log: str,
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
    is_created_buy: bool,
    recent_blockhash: str = "",
) -> Optional[DexEvent]:
    """对齐 Rust `parse_log` - 带完整 gRPC 元数据字段的日志解析"""
    return parse_log_optimized(
        log,
        signature,
        slot,
        tx_index,
        block_time_us,
        grpc_recv_us,
        None,
        is_created_buy,
        recent_blockhash,
    )


def warmup_parser() -> None:
    decode_program_data_line("Program data: AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")


__all__ = [
    "DexEvent",
    "decode_program_data_line",
    "dispatch_program_data",
    "parse_log",
    "parse_log_unified",
    "parse_log_optimized",
    "parse_logs_only",
    "parse_logs_streaming",
    "parse_transaction_events",
    "parse_transaction_events_streaming",
    "parse_transaction_with_listener",
    "parse_transaction_with_streaming_listener",
    "EventListener",
    "StreamingEventListener",
    "parse_trade_from_data",
    "warmup_parser",
]
