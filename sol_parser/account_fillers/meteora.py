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
