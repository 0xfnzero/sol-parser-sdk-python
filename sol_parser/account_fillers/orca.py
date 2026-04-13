"""Orca Whirlpool 账户填充（对齐 ``account_fillers/orca.rs``）。"""

from __future__ import annotations

from typing import Callable

from ..event_types import (
    OrcaWhirlpoolLiquidityDecreasedEvent,
    OrcaWhirlpoolLiquidityIncreasedEvent,
    OrcaWhirlpoolSwapEvent,
)

Z = "11111111111111111111111111111111"


def _empty(s: str) -> bool:
    return not s or s == Z


AccountGetter = Callable[[int], str]


def fill_whirlpool_swap_accounts(_e: OrcaWhirlpoolSwapEvent, _get: AccountGetter) -> None:
    pass


def fill_whirlpool_liquidity_increased_accounts(
    e: OrcaWhirlpoolLiquidityIncreasedEvent,
    get: AccountGetter,
) -> None:
    if _empty(e.position):
        e.position = get(3)


def fill_whirlpool_liquidity_decreased_accounts(
    e: OrcaWhirlpoolLiquidityDecreasedEvent,
    get: AccountGetter,
) -> None:
    if _empty(e.position):
        e.position = get(3)
