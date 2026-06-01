"""ShredStream gRPC 客户端：SubscribeEntries + bincode 解码 + DEX 外层指令。

限制：与 Rust 文档一致——不解析 inner CPI 日志；当前 Python 热路径只使用静态账户，
V0 ALT 加载账户用默认 pubkey 占位继续 best-effort 解析；若 program id 来自 ALT，
会按候选 program id 尝试 discriminator 解析。需安装 ``solders``（``pip install 'sol-parser-sdk-python[shredstream]'``）。
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Callable, Generator, List, Optional
from urllib.parse import urlparse

import base58
import grpc

from .entries_decode import decode_entries_bincode_flat
from .event_types import DexEvent
from .dex_parsers import Z
from .grpc_types import EventTypeFilter, event_type_filter_includes_pumpfun
from .instructions import (
    METEORA_DAMM_V2_PROGRAM_ID,
    METEORA_DLMM_PROGRAM_ID,
    METEORA_POOLS_PROGRAM_ID,
    ORCA_WHIRLPOOL_PROGRAM_ID,
    PUMP_FEES_PROGRAM_ID,
    PUMPFUN_PROGRAM_ID,
    PUMPSWAP_PROGRAM_ID,
    RAYDIUM_AMM_V4_PROGRAM_ID,
    RAYDIUM_CLMM_PROGRAM_ID,
    RAYDIUM_CPMM_PROGRAM_ID,
    RAYDIUM_LAUNCHLAB_PROGRAM_ID,
    parse_instruction_unified,
)
from .pumpfun_fee_enrich import enrich_pumpfun_same_tx_post_merge
from .shredstream_pumpfun import detect_pumpfun_create_mints, parse_pumpfun_shred_ix
from .shredstream_pb2 import SubscribeEntriesRequest
from .shredstream_pb2_grpc import ShredstreamProxyStub


@dataclass
class ShredStreamConfig:
    """对齐 Rust ``shredstream::config::ShredStreamConfig``。"""

    connection_timeout_ms: int = 8000
    request_timeout_ms: int = 15000
    max_decoding_message_size: int = 100 * 1024 * 1024
    reconnect_delay_ms: int = 1000
    max_reconnect_attempts: int = 3

    @staticmethod
    def low_latency() -> ShredStreamConfig:
        return ShredStreamConfig(
            connection_timeout_ms=5000,
            request_timeout_ms=10000,
            max_decoding_message_size=50 * 1024 * 1024,
            reconnect_delay_ms=100,
            max_reconnect_attempts=1,
        )

    @staticmethod
    def high_throughput() -> ShredStreamConfig:
        return ShredStreamConfig(
            connection_timeout_ms=10000,
            request_timeout_ms=30000,
            max_decoding_message_size=200 * 1024 * 1024,
            reconnect_delay_ms=2000,
            max_reconnect_attempts=5,
        )


def _parsed_endpoint(endpoint: str) -> tuple[str, str]:
    if "://" not in endpoint:
        endpoint = "http://" + endpoint
    p = urlparse(endpoint)
    return p.scheme, p.netloc or endpoint


def _ix_accounts_bytes(account_indices: object) -> bytes:
    if isinstance(account_indices, (bytes, bytearray, memoryview)):
        return bytes(account_indices)
    return bytes(list(account_indices))


def _static_ix_account_strings(keys: List[str], ix_accounts: bytes) -> List[str]:
    out: List[str] = []
    for i in ix_accounts:
        if i >= len(keys):
            out.append(Z)
            continue
        out.append(keys[i])
    return out


_UNKNOWN_PROGRAM_CANDIDATES = (
    PUMPFUN_PROGRAM_ID,
    PUMPSWAP_PROGRAM_ID,
    PUMP_FEES_PROGRAM_ID,
    RAYDIUM_LAUNCHLAB_PROGRAM_ID,
    RAYDIUM_CPMM_PROGRAM_ID,
    RAYDIUM_CLMM_PROGRAM_ID,
    RAYDIUM_AMM_V4_PROGRAM_ID,
    ORCA_WHIRLPOOL_PROGRAM_ID,
    METEORA_POOLS_PROGRAM_ID,
    METEORA_DAMM_V2_PROGRAM_ID,
    METEORA_DLMM_PROGRAM_ID,
)


def _pumpfun_filter_allows(filter: Optional[EventTypeFilter]) -> bool:
    return filter is None or event_type_filter_includes_pumpfun(filter)


def _filter_parsed_event(ev: Optional[DexEvent], filter: Optional[EventTypeFilter]) -> Optional[DexEvent]:
    if ev is None or filter is None:
        return ev
    return ev if filter.should_include(ev.type) else None


def _events_from_versioned_tx_wire(
    raw: bytes,
    signature: str,
    slot: int,
    tx_index: int,
    recv_us: int,
    filter: Optional[EventTypeFilter],
) -> List[DexEvent]:
    try:
        from solders.message import Message as LegacyMessage  # type: ignore
        from solders.message import MessageV0  # type: ignore
        from solders.transaction import VersionedTransaction  # type: ignore
    except ImportError:
        return []

    try:
        vt = VersionedTransaction.from_bytes(raw)
    except Exception:
        return []
    if not vt.signatures:
        return []
    sig = signature or base58.b58encode(bytes(vt.signatures[0])).decode("ascii")
    msg = vt.message
    out: List[DexEvent] = []

    if isinstance(msg, MessageV0):
        keys = [str(k) for k in msg.account_keys]
        ixs: List[tuple] = []
        for cix in msg.compiled_instructions:
            pid = keys[cix.program_id_index] if cix.program_id_index < len(keys) else None
            ixs.append((pid, bytes(cix.data), _ix_accounts_bytes(cix.accounts)))
    elif isinstance(msg, LegacyMessage):
        keys = [str(k) for k in msg.account_keys]
        ixs = []
        for ix in msg.instructions:
            pid = keys[ix.program_id_index] if ix.program_id_index < len(keys) else None
            ixs.append((pid, bytes(ix.data), _ix_accounts_bytes(ix.accounts)))
    else:
        return []

    created: set = set()
    mayhem: set = set()
    if _pumpfun_filter_allows(filter):
        for pid, data, ix_acc in ixs:
            if pid is not None and pid != PUMPFUN_PROGRAM_ID:
                continue
            c, m = detect_pumpfun_create_mints(PUMPFUN_PROGRAM_ID, data, ix_acc, keys)
            created |= c
            mayhem |= m

    for pid, data, ix_acc in ixs:
        if pid == PUMPFUN_PROGRAM_ID:
            if not _pumpfun_filter_allows(filter):
                continue
            ev = parse_pumpfun_shred_ix(
                data, keys, ix_acc, pid, sig, slot, tx_index, recv_us, created, mayhem
            )
            ev = _filter_parsed_event(ev, filter)
            if ev:
                out.append(ev)
            continue
        accounts = _static_ix_account_strings(keys, ix_acc)
        if pid is None:
            for candidate in _UNKNOWN_PROGRAM_CANDIDATES:
                if candidate == PUMPFUN_PROGRAM_ID:
                    if not _pumpfun_filter_allows(filter):
                        continue
                    ev = parse_pumpfun_shred_ix(
                        data, keys, ix_acc, PUMPFUN_PROGRAM_ID, sig, slot, tx_index, recv_us, created, mayhem
                    )
                    ev = _filter_parsed_event(ev, filter)
                else:
                    ev = parse_instruction_unified(
                        bytes(data), accounts, sig, slot, tx_index, None, recv_us, filter, candidate
                    )
                if ev:
                    out.append(ev)
                    break
            continue
        ev = parse_instruction_unified(
            bytes(data), accounts, sig, slot, tx_index, None, recv_us, filter, pid
        )
        if ev:
            out.append(ev)

    for ev in out:
        if hasattr(ev.data, "metadata"):
            ev.data.metadata.grpc_recv_us = recv_us
    enrich_pumpfun_same_tx_post_merge(out)
    return out


class ShredStreamClient:
    """阻塞式 gRPC 客户端（可在 asyncio 中用 ``asyncio.to_thread`` 包装）。"""

    def __init__(self, endpoint: str, config: Optional[ShredStreamConfig] = None):
        self.endpoint = endpoint
        self.config = config or ShredStreamConfig()

    @classmethod
    def new_with_config(cls, endpoint: str, config: ShredStreamConfig) -> ShredStreamClient:
        """对齐 Rust ``ShredStreamClient::new_with_config``。"""
        return cls(endpoint, config)

    def iter_dex_events(
        self,
        filter: Optional[EventTypeFilter] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
    ) -> Generator[DexEvent, None, None]:
        """订阅 ``SubscribeEntries``，解码每笔线交易中的 DEX 外层指令事件。"""
        f = filter
        scheme, target = _parsed_endpoint(self.endpoint)
        opts = [
            ("grpc.max_receive_message_length", self.config.max_decoding_message_size),
            ("grpc.max_send_message_length", self.config.max_decoding_message_size),
        ]
        if scheme == "https":
            channel = grpc.secure_channel(
                target, grpc.ssl_channel_credentials(), options=opts
            )
        else:
            channel = grpc.insecure_channel(target, options=opts)
        stub = ShredstreamProxyStub(channel)
        try:
            for entry in stub.SubscribeEntries(SubscribeEntriesRequest()):
                slot = entry.slot
                recv_us = int(time.time() * 1_000_000)
                try:
                    raws = decode_entries_bincode_flat(bytes(entry.entries))
                except Exception as e:
                    if on_error:
                        on_error(e)
                    continue
                for tx_counter, raw in enumerate(raws):
                    sig0 = ""
                    try:
                        from solders.transaction import VersionedTransaction  # type: ignore

                        sig0 = base58.b58encode(bytes(VersionedTransaction.from_bytes(raw).signatures[0])).decode("ascii")
                    except Exception:
                        pass
                    for ev in _events_from_versioned_tx_wire(raw, sig0, slot, tx_counter, recv_us, f):
                        yield ev
        finally:
            channel.close()
