"""PumpSwap 账户填充（对齐 ``account_fillers/pumpswap.rs`` 子集，字段与 Python dataclass 一致）。"""

from __future__ import annotations

from typing import Any, Callable

from ..event_types import (
    PumpSwapBuyEvent,
    PumpSwapCreatePoolEvent,
    PumpSwapLiquidityAddedEvent,
    PumpSwapLiquidityRemovedEvent,
    PumpSwapSellEvent,
)

Z = "11111111111111111111111111111111"


def _empty(s: str) -> bool:
    return not s or s == Z


AccountGetter = Callable[[int], str]


def _fill_trade_common(
    e: PumpSwapBuyEvent | PumpSwapSellEvent,
    get: AccountGetter,
) -> None:
    if _empty(e.pool):
        e.pool = get(0)
    if _empty(e.user):
        e.user = get(1)
    if _empty(e.user_base_token_account):
        e.user_base_token_account = get(5)
    if _empty(e.user_quote_token_account):
        e.user_quote_token_account = get(6)
    if _empty(e.protocol_fee_recipient):
        e.protocol_fee_recipient = get(9)
    if _empty(e.protocol_fee_recipient_token_account):
        e.protocol_fee_recipient_token_account = get(10)


def fill_buy_accounts(e: PumpSwapBuyEvent, get: AccountGetter) -> None:
    _fill_trade_common(e, get)


def fill_sell_accounts(e: PumpSwapSellEvent, get: AccountGetter) -> None:
    _fill_trade_common(e, get)


def fill_trade_accounts(_e: Any, _get: AccountGetter) -> None:
    pass


def fill_create_pool_accounts(e: PumpSwapCreatePoolEvent, get: AccountGetter) -> None:
    if _empty(e.pool):
        e.pool = get(0)
    if _empty(e.creator):
        e.creator = get(2)
    if _empty(e.base_mint):
        e.base_mint = get(3)
    if _empty(e.quote_mint):
        e.quote_mint = get(4)
    if _empty(e.lp_mint):
        e.lp_mint = get(5)
    if _empty(e.user_base_token_account):
        e.user_base_token_account = get(6)
    if _empty(e.user_quote_token_account):
        e.user_quote_token_account = get(7)


def fill_liquidity_added_accounts(_e: PumpSwapLiquidityAddedEvent, _get: AccountGetter) -> None:
    pass


def fill_liquidity_removed_accounts(_e: PumpSwapLiquidityRemovedEvent, _get: AccountGetter) -> None:
    pass
