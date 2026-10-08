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
    RaydiumClmmClosePositionEvent,
    RaydiumClmmOpenPositionEvent,
    RaydiumClmmOpenPositionWithTokenExtNftEvent,
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
    if _empty(e.pool):
        e.pool = get(2)


def fill_clmm_decrease_liquidity_accounts(e: RaydiumClmmDecreaseLiquidityEvent, get: AccountGetter) -> None:
    if _empty(e.user):
        e.user = get(0)
    if _empty(e.pool):
        e.pool = get(3)


def fill_clmm_open_position_accounts(e: RaydiumClmmOpenPositionEvent, get: AccountGetter) -> None:
    if _empty(e.user):
        e.user = get(0)
    if _empty(e.position_nft_mint):
        e.position_nft_mint = get(2)


def fill_clmm_open_position_with_token_ext_nft_accounts(
    e: RaydiumClmmOpenPositionWithTokenExtNftEvent,
    get: AccountGetter,
) -> None:
    if _empty(e.user):
        e.user = get(0)
    if _empty(e.position_nft_mint):
        e.position_nft_mint = get(2)


def fill_clmm_close_position_accounts(e: RaydiumClmmClosePositionEvent, get: AccountGetter) -> None:
    if _empty(e.user):
        e.user = get(0)
    if _empty(e.position_nft_mint):
        e.position_nft_mint = get(1)


def fill_cpmm_swap_accounts(e: RaydiumCpmmSwapEvent, get: AccountGetter) -> None:
    if _empty(e.pool_id):
        e.pool_id = get(3)


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
    if _empty(e.amm):e.amm=get(1)
    modern=_empty(get(8)) and not _empty(get(7))
    if modern:
        for field,index in [('token_program',0),('amm_authority',2),('pool_coin_token_account',3),('pool_pc_token_account',4),('user_source_token_account',5),('user_destination_token_account',6),('user_source_owner',7)]:
            if _empty(getattr(e,field)):setattr(e,field,get(index))
    elif _empty(e.user_source_owner):e.user_source_owner=get(16) if _empty(get(17)) else get(17)


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


def clmm_position_matches(mint: str, position: str) -> bool:
    """Match a candidate PDA to the log mint without a crypto dependency.

    This checks seed hashes against an existing instruction address; it does
    not create or validate a new PDA or prove transaction authorization.
    """
    import base58
    import hashlib
    if _empty(mint) or _empty(position):
        return False
    try:
        raw_mint = base58.b58decode(mint)
        target = base58.b58decode(position)
    except ValueError:
        return False
    if len(raw_mint) != 32 or len(target) != 32:
        return False
    program = base58.b58decode("CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK")
    return any(hashlib.sha256(b"position" + raw_mint + bytes([bump]) + program + b"ProgramDerivedAddress").digest() == target for bump in range(255, -1, -1))
