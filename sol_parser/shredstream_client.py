"""ShredStream gRPC 客户端：SubscribeEntries + bincode 解码 + PumpFun 外层指令（对齐 Node ``shredstream/client.ts`` 子集）。

限制：与 Rust 文档一致——不解析 inner CPI 日志、不解析 ALT 展开；需安装 ``solders``（``pip install 'sol-parser-sdk-python[shredstream]'``）。
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
from .grpc_types import EventTypeFilter, IncludeOnlyFilter
from .instructions import PUMPFUN_PROGRAM_ID, parse_instruction_unified
from .pumpfun_fee_enrich import enrich_create_v2_observed_fee_recipient
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


def _events_from_versioned_tx_wire(
    raw: bytes,
    signature: str,
    slot: int,
    tx_index: int,
    recv_us: int,
    filter: EventTypeFilter,
) -> List[DexEvent]:
    try:
        from solders.message import Message as LegacyMessage  # type: ignore
        from solders.message import MessageV0  # type: ignore
        from solders.transaction import VersionedTransaction  # type: ignore
    except ImportError:
        return []

    vt = VersionedTransaction.from_bytes(raw)
    if not vt.signatures:
        return []
    sig = signature or base58.b58encode(bytes(vt.signatures[0])).decode("ascii")
    msg = vt.message
    out: List[DexEvent] = []

    if isinstance(msg, MessageV0):
        keys = [str(k) for k in msg.account_keys]
        ixs: List[tuple] = []
        for cix in msg.compiled_instructions:
            pid = keys[cix.program_id_index]
            ixs.append((pid, bytes(cix.data), _ix_accounts_bytes(cix.accounts)))
    elif isinstance(msg, LegacyMessage):
        keys = [str(k) for k in msg.account_keys]
        ixs = []
        for ix in msg.instructions:
            pid = keys[ix.program_id_index]
            ixs.append((pid, bytes(ix.data), _ix_accounts_bytes(ix.accounts)))
    else:
        return []

    created: set = set()
    mayhem: set = set()
    for pid, data, ix_acc in ixs:
        c, m = detect_pumpfun_create_mints(pid, data, ix_acc, keys)
        created |= c
        mayhem |= m

    for pid, data, ix_acc in ixs:
        idxs = list(ix_acc)
        accounts = [keys[i] for i in idxs if i < len(keys)]
        if pid == PUMPFUN_PROGRAM_ID:
            ev = parse_pumpfun_shred_ix(
                data, keys, ix_acc, pid, sig, slot, tx_index, recv_us, created, mayhem
            )
            if ev:
                out.append(ev)
            continue
        ev = parse_instruction_unified(
            bytes(data), accounts, sig, slot, tx_index, None, recv_us, filter, pid
        )
        if ev:
            out.append(ev)

    for ev in out:
        if hasattr(ev.data, "metadata"):
            ev.data.metadata.grpc_recv_us = recv_us
    enrich_create_v2_observed_fee_recipient(out)
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
        """订阅 ``SubscribeEntries``，解码每笔线交易中的 PumpFun 外层指令事件。"""
        f: EventTypeFilter = filter if filter is not None else IncludeOnlyFilter([])
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
        recv_us = int(time.time() * 1_000_000)
        tx_counter = 0
        try:
            for entry in stub.SubscribeEntries(SubscribeEntriesRequest()):
                slot = entry.slot
                try:
                    raws = decode_entries_bincode_flat(bytes(entry.entries))
                except Exception as e:
                    if on_error:
                        on_error(e)
                    continue
                for raw in raws:
                    sig0 = ""
                    try:
                        from solders.transaction import VersionedTransaction  # type: ignore

                        sig0 = base58.b58encode(bytes(VersionedTransaction.from_bytes(raw).signatures[0])).decode("ascii")
                    except Exception:
                        pass
                    for ev in _events_from_versioned_tx_wire(raw, sig0, slot, tx_counter, recv_us, f):
                        yield ev
                    tx_counter += 1
        finally:
            channel.close()
