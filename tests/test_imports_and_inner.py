"""基础导入与 inner 路由烟测。"""

from __future__ import annotations

import struct

from sol_parser.dex_parsers import parse_ps_buy_from_data
from sol_parser.inner_instruction_parser import parse_inner_instruction
from sol_parser.grpc_types import EventType, IncludeOnlyFilter
from sol_parser.instructions import (
    METEORA_POOLS_PROGRAM_ID,
    PUMPFUN_PROGRAM_ID,
    PUMPSWAP_PROGRAM_ID,
    RAYDIUM_LAUNCHLAB_PROGRAM_ID,
)


def test_parse_inner_pumpfun_short_data() -> None:
    assert parse_inner_instruction(b"", PUMPFUN_PROGRAM_ID, {}, IncludeOnlyFilter([]), False) is None


PUMPSWAP_INNER_BUY = bytes([228, 69, 165, 46, 81, 203, 154, 29, 103, 244, 82, 31, 44, 245, 119, 119])
PUMPSWAP_BUY_PAYLOAD_LEN = 16 * 8 + 7 * 32 + 1 + 5 * 8 + 4
RAYDIUM_LAUNCHLAB_INNER_POOL_CREATE = bytes(
    [151, 215, 226, 9, 118, 161, 115, 174, 155, 167, 108, 32, 122, 76, 173, 64]
)
RAYDIUM_LAUNCHLAB_OLD_INNER_TRADE = bytes(
    [80, 120, 100, 200, 150, 75, 60, 40, 155, 167, 108, 32, 122, 76, 173, 64]
)
METEORA_POOLS_INNER_SWAP = bytes(
    [81, 108, 227, 190, 205, 208, 10, 196, 155, 167, 108, 32, 122, 76, 173, 64]
)


def test_parse_inner_none_filter_allows_pumpswap_buy() -> None:
    ev = parse_inner_instruction(
        PUMPSWAP_INNER_BUY + bytes(PUMPSWAP_BUY_PAYLOAD_LEN),
        PUMPSWAP_PROGRAM_ID,
        {},
        None,
        False,
    )

    assert ev is not None
    assert ev.type == EventType.PUMP_SWAP_BUY


def test_parse_inner_applies_actual_event_type_filter() -> None:
    data = PUMPSWAP_INNER_BUY + bytes(PUMPSWAP_BUY_PAYLOAD_LEN)

    assert (
        parse_inner_instruction(
            data,
            PUMPSWAP_PROGRAM_ID,
            {},
            IncludeOnlyFilter([EventType.PUMP_SWAP_CREATE_POOL]),
            False,
        )
        is None
    )
    ev = parse_inner_instruction(
        data,
        PUMPSWAP_PROGRAM_ID,
        {},
        IncludeOnlyFilter([EventType.PUMP_SWAP_TRADE]),
        False,
    )
    assert ev is not None
    assert ev.type == EventType.PUMP_SWAP_BUY


def test_pumpswap_buy_rejects_truncated_min_base_payload() -> None:
    assert parse_ps_buy_from_data(bytes(396), {}) is None
    ev = parse_ps_buy_from_data(bytes(397), {})
    assert ev is not None
    assert ev.type == EventType.PUMP_SWAP_BUY


def test_parse_inner_meteora_pools_uses_protocol_prefilter() -> None:
    data = METEORA_POOLS_INNER_SWAP + struct.pack("<QQ", 1, 2)

    assert (
        parse_inner_instruction(
            data,
            METEORA_POOLS_PROGRAM_ID,
            {},
            IncludeOnlyFilter([EventType.PUMP_FUN_TRADE]),
            False,
        )
        is None
    )
    ev = parse_inner_instruction(
        data,
        METEORA_POOLS_PROGRAM_ID,
        {},
        IncludeOnlyFilter([EventType.METEORA_POOLS_SWAP]),
        False,
    )
    assert ev is not None
    assert ev.type == EventType.METEORA_POOLS_SWAP


def test_parse_inner_raydium_launchlab_uses_real_cpi_discriminators() -> None:
    pool_create_payload = bytes(96) + bytes([6]) + struct.pack("<III", 0, 0, 0)
    ev = parse_inner_instruction(
        RAYDIUM_LAUNCHLAB_INNER_POOL_CREATE + pool_create_payload,
        RAYDIUM_LAUNCHLAB_PROGRAM_ID,
        {},
        None,
        False,
    )

    assert ev is not None
    assert ev.type == EventType.RAYDIUM_LAUNCHLAB_POOL_CREATE
    assert (
        parse_inner_instruction(
            RAYDIUM_LAUNCHLAB_OLD_INNER_TRADE + bytes(139),
            RAYDIUM_LAUNCHLAB_PROGRAM_ID,
            {},
            None,
            False,
        )
        is None
    )


def test_import_grpc_subscribe_builder() -> None:
    from sol_parser.grpc.subscribe_builder import build_subscribe_request_with_commitment

    from sol_parser.grpc_types import AccountFilter, CommitmentLevel, TransactionFilter

    tx = TransactionFilter(account_include=["6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"])
    req = build_subscribe_request_with_commitment(
        [tx], [AccountFilter.new()], CommitmentLevel.PROCESSED
    )
    assert req is not None


def test_import_accounts_utils() -> None:
    from sol_parser.accounts.utils import user_wallet_pubkey_for_onchain_account

    assert (
        user_wallet_pubkey_for_onchain_account(
            "SoLAddRess1111111111111111111111111111111111",
            "11111111111111111111111111111111",
            b"",
            False,
        )
        == "SoLAddRess1111111111111111111111111111111111"
    )
