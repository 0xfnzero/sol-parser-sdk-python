"""Raydium 账户填充（对齐 ``account_fillers/raydium.rs``）。"""

from __future__ import annotations

from typing import Callable

from ..event_types import (
    RaydiumAmmV4DepositEvent,
    RaydiumAmmV4SwapEvent,
    RaydiumAmmV4WithdrawEvent,
    RaydiumClmmCreatePoolEvent,
    RaydiumClmmDecreaseLiquidityEvent,
    RaydiumClmmIncreaseLiquidityEvent,
    RaydiumClmmSwapEvent,
    RaydiumCpmmDepositEvent,
    RaydiumCpmmInitializeEvent,
    RaydiumCpmmSwapEvent,
    RaydiumCpmmWithdrawEvent,
)

Z = "11111111111111111111111111111111"


def _empty(s: str) -> bool:
    return not s or s == Z


AccountGetter = Callable[[int], str]


def fill_clmm_swap_accounts(e: RaydiumClmmSwapEvent, get: AccountGetter) -> None:
    if _empty(e.pool_state):
        e.pool_state = get(2)
    if _empty(e.sender):
        e.sender = get(0)


def fill_clmm_create_pool_accounts(e: RaydiumClmmCreatePoolEvent, get: AccountGetter) -> None:
    if _empty(e.creator):
        e.creator = get(0)


def fill_clmm_increase_liquidity_accounts(e: RaydiumClmmIncreaseLiquidityEvent, get: AccountGetter) -> None:
    if _empty(e.user):
        e.user = get(0)


def fill_clmm_decrease_liquidity_accounts(e: RaydiumClmmDecreaseLiquidityEvent, get: AccountGetter) -> None:
    if _empty(e.user):
        e.user = get(0)


def fill_cpmm_swap_accounts(_e: RaydiumCpmmSwapEvent, _get: AccountGetter) -> None:
    pass


def fill_cpmm_deposit_accounts(e: RaydiumCpmmDepositEvent, get: AccountGetter) -> None:
    if _empty(e.user):
        e.user = get(0)


def fill_cpmm_withdraw_accounts(e: RaydiumCpmmWithdrawEvent, get: AccountGetter) -> None:
    if _empty(e.user):
        e.user = get(0)


def fill_cpmm_initialize_accounts(e: RaydiumCpmmInitializeEvent, get: AccountGetter) -> None:
    if _empty(e.creator):
        e.creator = get(0)
    if _empty(e.pool):
        e.pool = get(3)


def fill_amm_v4_swap_accounts(e: RaydiumAmmV4SwapEvent, get: AccountGetter) -> None:
    if _empty(e.amm):
        e.amm = get(1)


def fill_amm_v4_deposit_accounts(e: RaydiumAmmV4DepositEvent, get: AccountGetter) -> None:
    if _empty(e.token_program):
        e.token_program = get(0)
    if _empty(e.amm_authority):
        e.amm_authority = get(2)


def fill_amm_v4_withdraw_accounts(e: RaydiumAmmV4WithdrawEvent, get: AccountGetter) -> None:
    if _empty(e.token_program):
        e.token_program = get(0)
    if _empty(e.amm_authority):
        e.amm_authority = get(2)
    if _empty(e.amm_open_orders):
        e.amm_open_orders = get(3)
