"""同笔交易中 CreateV2 与 Buy 分离时，将买入类事件的 fee_recipient 回填到 CreateV2（对齐 Rust ``pumpfun_fee_enrich``）。"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from .dex_parsers import Z
from .event_types import DexEvent, PumpFunCreateV2TokenEvent, PumpFunTradeEvent
from .grpc_types import EventType


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
    if ev.type in (EventType.PUMP_FUN_BUY, EventType.PUMP_FUN_BUY_EXACT_SOL_IN):
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
        if not c.observed_fee_recipient and c.mint in mint_to_fee:
            c.observed_fee_recipient = mint_to_fee[c.mint]
