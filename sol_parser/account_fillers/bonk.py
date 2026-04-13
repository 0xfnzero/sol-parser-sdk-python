"""Bonk 账户填充（对齐 ``account_fillers/bonk.rs``）。"""

from __future__ import annotations

from typing import Callable

from ..event_types import BonkPoolCreateEvent, BonkTradeEvent

Z = "11111111111111111111111111111111"


def _empty(s: str) -> bool:
    return not s or s == Z


AccountGetter = Callable[[int], str]


def fill_trade_accounts(e: BonkTradeEvent, get: AccountGetter) -> None:
    if _empty(e.user):
        e.user = get(0)
    if _empty(e.pool_state):
        e.pool_state = get(1)


def fill_pool_create_accounts(e: BonkPoolCreateEvent, get: AccountGetter) -> None:
    if _empty(e.pool_state):
        e.pool_state = get(1)
    if _empty(e.creator):
        e.creator = get(8)
