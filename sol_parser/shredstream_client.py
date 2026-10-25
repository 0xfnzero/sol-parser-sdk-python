"""ShredStream gRPC 客户端：SubscribeEntries + bincode 解码 + DEX 外层指令。

限制：与 Rust 文档一致——不解析 inner CPI 日志；当前 Python 热路径只使用静态账户，
已知 Pump.fun 指令保留回调，未展开 ALT 地址保持默认值；ALT 只使用调用方预热缓存，不回退 RPC。Legacy/V0/V1 使用原生线格式解码。
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
from .grpc_types import (
    EventTypeFilter,
    event_type_filter_allows_instruction_parsing,
    event_type_filter_includes_pumpfun,
)
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
from .shredstream_pump_multi_hop import MULTI_HOP_SWAP, parse_curve_hops
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


def _should_parse_shred_instructions(filter: Optional[EventTypeFilter]) -> bool:
    if filter is None:
        return True
    include_only = getattr(filter, "include_only", None)
    if include_only is None:
        return True
    if not include_only:
        return False
    return event_type_filter_allows_instruction_parsing(list(include_only))


def _parse_decoded_shred(tx, keys, signature, slot, tx_index, recv_us, filter, best_effort=False):
    from .raw_instruction import INFRASTRUCTURE_PROGRAMS
    from .grpc_types import EventType
    from .grpc_types import EventMetadata
    if not _should_parse_shred_instructions(filter):
        return []
    msg = tx['message']
    signature = signature or tx['signatures'][0]
    instructions = [(keys[ix['programIdIndex']] if ix['programIdIndex'] < len(keys) else None,
                     (ix['data'] if isinstance(ix['data'], bytes) else base58.b58decode(ix['data'])), bytes(ix['accounts'])) for ix in msg['instructions']]
    created, mayhem = set(), set()
    if _pumpfun_filter_allows(filter):
        for pid, data, indices in instructions:
            if pid == PUMPFUN_PROGRAM_ID:
                c, m = detect_pumpfun_create_mints(pid, data, indices, keys)
                created |= c
                mayhem |= m
    out = []
    for index, (pid, data, indices) in enumerate(instructions):
        unknown = pid and pid not in _UNKNOWN_PROGRAM_CANDIDATES and pid not in INFRASTRUCTURE_PROGRAMS
        if (unknown and any(i < len(keys) and keys[i] == PUMPFUN_PROGRAM_ID for i in indices)
                and EventType.PUMP_FUN_TRADE not in (getattr(filter, "exclude_types", None) or ())
                and (getattr(filter, "include_only", None) is None or EventType.PUMP_FUN_TRADE in filter.include_only)):
            from .event_types import PumpFunTradeEvent
            from .trade_source import RawInstructionPayload, TradeParseStatus
            out.append(DexEvent(EventType.PUMP_FUN_TRADE, PumpFunTradeEvent(
                metadata=EventMetadata(signature=signature, slot=slot, tx_index=tx_index,
                    grpc_recv_us=recv_us, recent_blockhash=msg['recentBlockhash']),
                third_program=RawInstructionPayload(
                    program_id=pid, instruction_index=index,
                    accounts=[keys[i] if i < len(keys) else None for i in indices],
                    account_indices=list(indices), instruction_data=list(data)),
                parse_status=TradeParseStatus.UNRESOLVED)))
        if unknown:
            continue
        if pid == PUMPSWAP_PROGRAM_ID and data.startswith(MULTI_HOP_SWAP):
            if (EventType.PUMP_FUN_TRADE not in (getattr(filter, 'exclude_types', None) or ())
                    and (getattr(filter, "include_only", None) is None or EventType.PUMP_FUN_TRADE in filter.include_only)):
                hops = parse_curve_hops(data, indices, keys, index, EventMetadata(signature=signature,
                    slot=slot, tx_index=tx_index, grpc_recv_us=recv_us, recent_blockhash=msg['recentBlockhash']))
                for hop in hops:
                    hop.data.is_created_buy = hop.data.is_buy and hop.data.mint in created
                out.extend(hops)
            continue
        resolved = pid is not None and all(i < len(keys) for i in indices)
        if not resolved and not best_effort:
            if pid != PUMPFUN_PROGRAM_ID:
                continue
            minimum = {bytes([184,23,238,97,103,197,211,61]):27,
                       bytes([194,171,28,70,104,77,91,47]):27,
                       bytes([93,246,130,60,231,233,64,178]):26}.get(data[:8], 0)
            if len(indices) < minimum:
                continue
        if pid == PUMPFUN_PROGRAM_ID:
            if not _pumpfun_filter_allows(filter):continue
            event = _filter_parsed_event(parse_pumpfun_shred_ix(data, keys, indices, pid, signature,
                        slot, tx_index, recv_us, created, mayhem), filter)
        else:
            accounts = _static_ix_account_strings(keys, indices)
            event = None
            for program in ([pid] if pid else _UNKNOWN_PROGRAM_CANDIDATES):
                event = parse_instruction_unified(data, accounts, signature, slot, tx_index, None, recv_us, filter, program)
                if event:break
        if event:
            from .event_types import PumpFunTradeEvent
            if pid == PUMPFUN_PROGRAM_ID and isinstance(event.data, PumpFunTradeEvent):
                trade = event.data
                def missing(i):
                    return i < len(indices) and indices[i] >= len(keys)
                if trade.ix_name.endswith(('_v2', '_v3')):
                    for i, field in ((2, 'quote_mint'), (3, 'token_program'), (4, 'quote_token_program')):
                        if missing(i):setattr(trade, field, Z)
                elif missing(9 if trade.ix_name == 'sell' else 8):
                    trade.token_program = Z
                only = getattr(filter, 'include_only', None) or ()
                if EventType.PUMP_FUN_TRADE in only and not any(t in only for t in
                        (EventType.PUMP_FUN_BUY, EventType.PUMP_FUN_SELL, EventType.PUMP_FUN_BUY_EXACT_SOL_IN)):
                    event.type = EventType.PUMP_FUN_TRADE
            if hasattr(event.data, 'metadata'):event.data.metadata.recent_blockhash = msg['recentBlockhash']
            out.append(event)
    enrich_pumpfun_same_tx_post_merge(out)
    return out


def _decode_shred(raw, raw_instructions=True):
    from .wire_transaction import _decode_wire_transaction
    return _decode_wire_transaction(raw, raw_instructions=raw_instructions)[0]


def parse_shred_transaction_with_loaded_addresses(raw, writable, readonly, signature='', slot=0, tx_index=0, recv_us=0, filter=None):
    """Strict, offline parsing. Reject inconsistent ALT counts before producing events."""
    tx = _decode_shred(raw)
    return _parse_loaded_shred(tx, writable, readonly, signature, slot, tx_index, recv_us, filter)


def _parse_loaded_shred(tx, writable, readonly, signature, slot, tx_index, recv_us, filter):
    msg = tx['message']
    lookups = msg.get('addressTableLookups', [])
    if len(writable) != sum(len(l['writableIndexes']) for l in lookups) or len(readonly) != sum(len(l['readonlyIndexes']) for l in lookups):
        raise ValueError('ALT address counts do not match transaction')
    keys = [*msg['accountKeys'], *writable, *readonly]
    if any(ix['programIdIndex'] >= len(keys) or any(i >= len(keys) for i in ix['accounts']) for ix in msg['instructions']):
        raise ValueError('Unresolved instruction index')
    return _parse_decoded_shred(tx, keys, signature, slot, tx_index, recv_us, filter)


def parse_shred_transaction(raw, signature='', slot=0, tx_index=0, recv_us=0, filter=None, *, best_effort=False, address_lookup_resolver=None):
    """Static keys by default; optional slot-aware resolver must read only a prewarmed cache."""
    try:
        # Resolver callbacks retain the public JSON-compatible decoded shape.
        tx = _decode_shred(raw, raw_instructions=address_lookup_resolver is None)
    except (ValueError, IndexError, TypeError):
        return []
    if address_lookup_resolver is not None and tx['message'].get('addressTableLookups'):
        loaded = address_lookup_resolver(tx, slot)
        if loaded is None:return []
        return _parse_loaded_shred(tx, *loaded, signature, slot, tx_index, recv_us, filter)
    return _parse_decoded_shred(tx, tx['message']['accountKeys'], signature, slot, tx_index, recv_us, filter, best_effort)


def _events_from_versioned_tx_wire(raw, signature, slot, tx_index, recv_us, filter):
    return parse_shred_transaction(raw, signature, slot, tx_index, recv_us, filter)


def parse_shred_transaction_best_effort(raw, signature='', slot=0, tx_index=0, recv_us=0, filter=None):
    """Explicit legacy placeholder mapping; route adapters still require resolved keys."""
    return parse_shred_transaction(raw, signature, slot, tx_index, recv_us, filter, best_effort=True)


class ShredStreamClient:
    """阻塞式 gRPC 客户端（可在 asyncio 中用 ``asyncio.to_thread`` 包装）。"""

    def __init__(self, endpoint: str, config: Optional[ShredStreamConfig] = None):
        self.endpoint = endpoint
        self.config = config or ShredStreamConfig()
        self.address_lookup_resolver = None

    def with_address_lookup_resolver(self, resolver):
        """Set a synchronous slot-aware cache callback; no automatic RPC fallback."""
        self.address_lookup_resolver = resolver
        return self

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
                    try:
                        events = parse_shred_transaction(raw, slot=slot, tx_index=tx_counter, recv_us=recv_us,
                                                       filter=f, address_lookup_resolver=self.address_lookup_resolver)
                    except Exception as error:
                        if on_error:on_error(error)
                        continue
                    yield from events
        finally:
            channel.close()
