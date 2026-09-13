"""RaydiumLaunchlab 账户填充（对齐 ``account_fillers/raydium_launchlab.rs``）。"""

from __future__ import annotations

from typing import Callable

from ..event_types import RaydiumLaunchlabPoolCreateEvent, RaydiumLaunchlabTradeEvent

Z = "11111111111111111111111111111111"
RAYDIUM_LAUNCHLAB_PROGRAM_ID = "LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj"


def _empty(s: str) -> bool:
    return not s or s == Z


AccountGetter = Callable[[int], str]


def fill_trade_accounts(e: RaydiumLaunchlabTradeEvent, get: AccountGetter) -> None:
    if _empty(e.user):
        e.user = get(0)
    if _empty(e.pool_state):
        e.pool_state = get(4)
    if _empty(e.global_config):
        e.global_config = get(2)
    if _empty(e.platform_config):
        e.platform_config = get(3)
    if _empty(e.user_base_token):
        e.user_base_token = get(5)
    if _empty(e.user_quote_token):
        e.user_quote_token = get(6)
    if _empty(e.base_vault):
        e.base_vault = get(7)
    if _empty(e.quote_vault):
        e.quote_vault = get(8)
    if _empty(e.base_mint):
        e.base_mint = get(9)
    if _empty(e.quote_mint):
        e.quote_mint = get(10)
    if _empty(e.base_token_program):
        e.base_token_program = get(11)
    if _empty(e.quote_token_program):
        e.quote_token_program = get(12)


def fill_pool_create_accounts(e: RaydiumLaunchlabPoolCreateEvent, get: AccountGetter) -> None:
    if _empty(e.pool_state):
        e.pool_state = get(5)
    if _empty(e.creator):
        e.creator = get(1)
    if _empty(e.payer):
        e.payer = get(0)
    if _empty(e.global_config):
        e.global_config = get(2)
    if _empty(e.platform_config):
        e.platform_config = get(3)
    if _empty(e.base_mint):
        e.base_mint = get(6)
    if _empty(e.quote_mint):
        e.quote_mint = get(7)
    if _empty(e.base_vault):
        e.base_vault = get(8)
    if _empty(e.quote_vault):
        e.quote_vault = get(9)
    # initialize / initialize_v2 use token-program indices 11-12;
    # initialize_with_token_2022 uses 10-11 (detect via program id at end).
    try:
        if get(17) == RAYDIUM_LAUNCHLAB_PROGRAM_ID:
            bi, qi = 11, 12
        elif get(14) == RAYDIUM_LAUNCHLAB_PROGRAM_ID:
            bi, qi = 10, 11
        else:
            return
    except Exception:
        return
    if _empty(e.base_token_program):
        e.base_token_program = get(bi)
    if _empty(e.quote_token_program):
        e.quote_token_program = get(qi)
