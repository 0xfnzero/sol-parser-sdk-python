"""同笔交易 PumpFun 后处理（对齐 Rust ``pumpfun_fee_enrich``）。"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .dex_parsers import Z
from .event_types import DexEvent, PumpFunCreateEvent, PumpFunCreateV2TokenEvent, PumpFunTradeEvent
from .grpc_types import EventType


def _empty_pubkey_or_string(value: str) -> bool:
    return value == "" or value == Z


def _fill_str_if_empty(dst: object, attr: str, value: str) -> None:
    if _empty_pubkey_or_string(getattr(dst, attr, "")) and not _empty_pubkey_or_string(value):
        setattr(dst, attr, value)


def _fill_int_if_zero(dst: object, attr: str, value: int) -> None:
    if getattr(dst, attr, 0) == 0 and value != 0:
        setattr(dst, attr, value)


def _buy_like_mint_fee(ev: DexEvent) -> Optional[Tuple[str, str]]:
    if not isinstance(ev.data, PumpFunTradeEvent):
        return None
    t = ev.data
    if t.mint == Z or not t.mint:
        return None
    if ev.type == EventType.PUMP_FUN_TRADE:
        if t.is_buy:
            return (t.mint, t.fee_recipient)
        return None
    if ev.type in (
        EventType.PUMP_FUN_BUY,
        EventType.PUMP_FUN_BUY_EXACT_SOL_IN,
    ):
        return (t.mint, t.fee_recipient)
    return None


def enrich_create_v2_observed_fee_recipient(events: List[DexEvent]) -> None:
    mint_to_fee: Dict[str, str] = {}
    for e in events:
        p = _buy_like_mint_fee(e)
        if not p:
            continue
        mint, fee = p
        if fee and fee != Z:
            mint_to_fee.setdefault(mint, fee)
    if not mint_to_fee:
        return
    for e in events:
        if e.type != EventType.PUMP_FUN_CREATE_V2:
            continue
        if not isinstance(e.data, PumpFunCreateV2TokenEvent):
            continue
        c = e.data
        if _empty_pubkey_or_string(c.observed_fee_recipient) and c.mint in mint_to_fee:
            c.observed_fee_recipient = mint_to_fee[c.mint]


def enrich_create_v2_from_create_events(events: List[DexEvent]) -> None:
    creates: Dict[str, PumpFunCreateEvent] = {}
    for e in events:
        if e.type != EventType.PUMP_FUN_CREATE or not isinstance(e.data, PumpFunCreateEvent):
            continue
        c = e.data
        if not _empty_pubkey_or_string(c.mint):
            creates.setdefault(c.mint, c)

    if not creates:
        return

    for e in events:
        if e.type != EventType.PUMP_FUN_CREATE_V2 or not isinstance(e.data, PumpFunCreateV2TokenEvent):
            continue
        c2 = e.data
        c = creates.get(c2.mint)
        if c is None:
            continue

        for attr in ("name", "symbol", "uri", "bonding_curve", "user", "creator", "token_program", "quote_mint"):
            _fill_str_if_empty(c2, attr, getattr(c, attr))
        for attr in (
            "timestamp",
            "virtual_token_reserves",
            "virtual_sol_reserves",
            "real_token_reserves",
            "token_total_supply",
            "virtual_quote_reserves",
        ):
            _fill_int_if_zero(c2, attr, getattr(c, attr))
        c2.is_cashback_enabled = c2.is_cashback_enabled or c.is_cashback_enabled
        c2.is_mayhem_mode = c2.is_mayhem_mode or c.is_mayhem_mode


def enrich_pumpfun_trades_from_create_instructions(events: List[DexEvent]) -> None:
    flags: Dict[str, Tuple[bool, bool]] = {}
    for e in events:
        if e.type not in (EventType.PUMP_FUN_CREATE, EventType.PUMP_FUN_CREATE_V2):
            continue
        if not isinstance(e.data, (PumpFunCreateEvent, PumpFunCreateV2TokenEvent)):
            continue
        c = e.data
        if c.mint and c.mint != Z:
            flags.setdefault(c.mint, (c.is_cashback_enabled, c.is_mayhem_mode))
    if not flags:
        return
    for e in events:
        if not isinstance(e.data, PumpFunTradeEvent):
            continue
        t = e.data
        if not t.mint or t.mint == Z or t.mint not in flags:
            continue
        cashback_enabled, mayhem_mode = flags[t.mint]
        t.is_cashback_coin = t.is_cashback_coin or cashback_enabled
        t.mayhem_mode = t.mayhem_mode or mayhem_mode
        if cashback_enabled:
            t.track_volume = True


def enrich_pumpfun_same_tx_post_merge(events: List[DexEvent]) -> None:
    enrich_create_v2_from_create_events(events)
    enrich_create_v2_observed_fee_recipient(events)
    enrich_pumpfun_trades_from_create_instructions(events)
