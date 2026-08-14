from __future__ import annotations

import struct

from sol_parser.event_types import (
    EventType,
    OrcaWhirlpoolLiquidityDecreasedEvent,
    OrcaWhirlpoolLiquidityIncreasedEvent,
    OrcaWhirlpoolPoolInitializedEvent,
    OrcaWhirlpoolSwapEvent,
)
from sol_parser.instructions import (
    ORCA_WHIRLPOOL_PROGRAM_ID,
    parse_instruction_unified,
    parse_orca_whirlpool_instruction,
)
from sol_parser.grpc_types import ExcludeFilter, IncludeOnlyFilter


SWAP_DISC = bytes([248, 198, 158, 145, 225, 117, 135, 200])
SWAP_V2_DISC = bytes([43, 4, 237, 11, 26, 201, 30, 98])
INC_LIQ_DISC = bytes([46, 156, 243, 118, 13, 205, 251, 178])
DEC_LIQ_DISC = bytes([160, 38, 208, 111, 104, 91, 44, 1])
INIT_POOL_DISC = bytes([17, 43, 80, 74, 168, 202, 6, 113])


def _accounts(n: int) -> list[str]:
    return [f"account_{i}" for i in range(n)]


def _swap_instruction(
    disc: bytes,
    amount: int,
    threshold: int,
    sqrt_price_limit: int,
    input_specified: bool,
    a_to_b: bool,
) -> bytes:
    return (
        disc
        + struct.pack("<QQ", amount, threshold)
        + sqrt_price_limit.to_bytes(16, "little")
        + bytes([1 if input_specified else 0, 1 if a_to_b else 0])
    )


def _liquidity_instruction(disc: bytes, liquidity: int, amount_a: int, amount_b: int) -> bytes:
    return disc + liquidity.to_bytes(16, "little") + struct.pack("<QQ", amount_a, amount_b)


def _init_pool_instruction(tick_spacing: int, initial_sqrt_price: int) -> bytes:
    return INIT_POOL_DISC + struct.pack("<H", tick_spacing) + initial_sqrt_price.to_bytes(16, "little")


def test_parse_orca_swap_and_swap_v2_instruction_fields() -> None:
    sqrt_price_limit = (1 << 80) + 123
    ev = parse_orca_whirlpool_instruction(
        _swap_instruction(SWAP_DISC, 111, 222, sqrt_price_limit, True, False),
        _accounts(4),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert ev is not None
    assert ev.type == EventType.ORCA_WHIRLPOOL_SWAP
    assert isinstance(ev.data, OrcaWhirlpoolSwapEvent)
    assert ev.data.whirlpool == "account_2"
    assert ev.data.a_to_b is False
    assert ev.data.pre_sqrt_price == str(sqrt_price_limit)
    assert ev.data.post_sqrt_price == "0"
    assert ev.data.input_amount == 111
    assert ev.data.output_amount == 222

    swap_v2 = parse_instruction_unified(
        _swap_instruction(SWAP_V2_DISC, 333, 444, sqrt_price_limit + 1, False, True),
        _accounts(5),
        "sig",
        1,
        0,
        None,
        10,
        IncludeOnlyFilter([EventType.ORCA_WHIRLPOOL_SWAP]),
        ORCA_WHIRLPOOL_PROGRAM_ID,
    )
    assert swap_v2 is not None
    assert swap_v2.type == EventType.ORCA_WHIRLPOOL_SWAP
    assert isinstance(swap_v2.data, OrcaWhirlpoolSwapEvent)
    assert swap_v2.data.whirlpool == "account_4"
    assert swap_v2.data.a_to_b is True
    assert swap_v2.data.pre_sqrt_price == str(sqrt_price_limit + 1)
    assert swap_v2.data.input_amount == 0
    assert swap_v2.data.output_amount == 333


def test_parse_orca_liquidity_instruction_payload_values() -> None:
    inc = parse_orca_whirlpool_instruction(
        _liquidity_instruction(INC_LIQ_DISC, (1 << 80) + 1, 222, 333),
        _accounts(5),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert inc is not None
    assert inc.type == EventType.ORCA_WHIRLPOOL_LIQUIDITY_INCREASED
    assert isinstance(inc.data, OrcaWhirlpoolLiquidityIncreasedEvent)
    assert inc.data.whirlpool == "account_1"
    assert inc.data.position == "account_3"
    assert inc.data.liquidity == str((1 << 80) + 1)
    assert inc.data.token_a_amount == 222
    assert inc.data.token_b_amount == 333

    dec = parse_orca_whirlpool_instruction(
        _liquidity_instruction(DEC_LIQ_DISC, (1 << 80) + 2, 444, 555),
        _accounts(5),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert dec is not None
    assert dec.type == EventType.ORCA_WHIRLPOOL_LIQUIDITY_DECREASED
    assert isinstance(dec.data, OrcaWhirlpoolLiquidityDecreasedEvent)
    assert dec.data.whirlpool == "account_1"
    assert dec.data.position == "account_3"
    assert dec.data.liquidity == str((1 << 80) + 2)
    assert dec.data.token_a_amount == 444
    assert dec.data.token_b_amount == 555


def test_parse_orca_initialize_pool_and_filters() -> None:
    initial_sqrt_price = (1 << 96) + 99
    ev = parse_instruction_unified(
        _init_pool_instruction(128, initial_sqrt_price),
        _accounts(10),
        "sig",
        1,
        0,
        None,
        10,
        IncludeOnlyFilter([EventType.ORCA_WHIRLPOOL_POOL_INITIALIZED]),
        ORCA_WHIRLPOOL_PROGRAM_ID,
    )
    assert ev is not None
    assert ev.type == EventType.ORCA_WHIRLPOOL_POOL_INITIALIZED
    assert isinstance(ev.data, OrcaWhirlpoolPoolInitializedEvent)
    assert ev.data.whirlpool == "account_1"
    assert ev.data.whirlpools_config == "account_2"
    assert ev.data.token_mint_a == "account_3"
    assert ev.data.token_mint_b == "account_4"
    assert ev.data.tick_spacing == 128
    assert ev.data.token_program_a == "account_8"
    assert ev.data.token_program_b == "account_9"
    assert ev.data.decimals_a == 0
    assert ev.data.decimals_b == 0
    assert ev.data.initial_sqrt_price == str(initial_sqrt_price)

    excluded = parse_instruction_unified(
        _init_pool_instruction(128, initial_sqrt_price),
        _accounts(10),
        "sig",
        1,
        0,
        None,
        10,
        ExcludeFilter([EventType.ORCA_WHIRLPOOL_POOL_INITIALIZED]),
        ORCA_WHIRLPOOL_PROGRAM_ID,
    )
    assert excluded is None
