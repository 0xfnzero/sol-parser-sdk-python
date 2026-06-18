"""Meteora 账户填充（对齐 ``account_fillers/meteora.rs``，多数为占位）。"""

from __future__ import annotations

from typing import Any, Callable

AccountGetter = Callable[[int], str]


def fill_damm_v2_swap_accounts(_e: Any, _get: AccountGetter) -> None:
    pass


def fill_damm_v2_create_position_accounts(_e: Any, _get: AccountGetter) -> None:
    pass


def fill_damm_v2_close_position_accounts(_e: Any, _get: AccountGetter) -> None:
    pass


def fill_damm_v2_add_liquidity_accounts(_e: Any, _get: AccountGetter) -> None:
    pass


def fill_damm_v2_remove_liquidity_accounts(_e: Any, _get: AccountGetter) -> None:
    pass


def fill_damm_v2_initialize_pool_accounts(e: Any, get: AccountGetter) -> None:
    if getattr(e, "creator", "") == "":
        e.creator = get(0)
    if getattr(e, "position_nft_mint", "") == "":
        e.position_nft_mint = get(1)
    if getattr(e, "pool", "") == "":
        e.pool = get(6)
    if getattr(e, "position", "") == "":
        e.position = get(7)
    if getattr(e, "token_a_mint", "") == "":
        e.token_a_mint = get(8)
    if getattr(e, "token_b_mint", "") == "":
        e.token_b_mint = get(9)


def fill_pools_swap_accounts(_e: Any, _get: AccountGetter) -> None:
    pass


def fill_pools_add_liquidity_accounts(_e: Any, _get: AccountGetter) -> None:
    pass


def fill_pools_remove_liquidity_accounts(_e: Any, _get: AccountGetter) -> None:
    pass


def fill_dlmm_swap_accounts(_e: Any, _get: AccountGetter) -> None:
    pass


def fill_dlmm_add_liquidity_accounts(_e: Any, _get: AccountGetter) -> None:
    pass


def fill_dlmm_remove_liquidity_accounts(_e: Any, _get: AccountGetter) -> None:
    pass
