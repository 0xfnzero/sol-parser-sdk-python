from __future__ import annotations

import struct

from sol_parser.event_types import (
    RaydiumClmmClosePositionEvent,
    RaydiumClmmDecreaseLiquidityEvent,
    RaydiumClmmOpenPositionEvent,
)
from sol_parser.grpc_types import EventType, event_type_filter_allows_instruction_parsing
from sol_parser.instructions import RAYDIUM_CLMM_PROGRAM_ID, parse_instruction_unified, parse_raydium_clmm_instruction


DEC_LIQ_V2_DISC = bytes([58, 127, 188, 62, 79, 82, 196, 96])
DEC_LIQ_LOG_DISC = bytes([160, 38, 208, 111, 104, 91, 44, 1])
OPEN_POSITION_V2_DISC = bytes([77, 184, 74, 214, 112, 86, 241, 199])
CLOSE_POSITION_DISC = bytes([123, 134, 81, 0, 49, 68, 98, 98])


def _accounts(n: int) -> list[str]:
    return [f"account_{i}" for i in range(n)]


def _u64_instruction(disc: bytes, *values: int) -> bytes:
    return disc + struct.pack("<" + "Q" * len(values), *values)


def _open_position_instruction(disc: bytes, lower: int, upper: int, liquidity: int) -> bytes:
    data = bytearray(8 + 4 + 4 + 4 + 4 + 8 + 8 + 8)
    data[:8] = disc
    struct.pack_into("<ii", data, 8, lower, upper)
    struct.pack_into("<Q", data, 24, liquidity)
    return bytes(data)


def test_parse_raydium_clmm_decrease_uses_rust_v2_instruction_discriminator() -> None:
    ev = parse_raydium_clmm_instruction(
        _u64_instruction(DEC_LIQ_V2_DISC, 111, 222, 333),
        _accounts(4),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert ev is not None
    assert ev.type == EventType.RAYDIUM_CLMM_DECREASE_LIQUIDITY
    assert isinstance(ev.data, RaydiumClmmDecreaseLiquidityEvent)
    assert ev.data.pool == "account_0"
    assert ev.data.position_nft_mint == "account_1"
    assert ev.data.user == "account_2"
    assert ev.data.liquidity == "111"
    assert ev.data.amount0_min == 222
    assert ev.data.amount1_min == 333

    assert parse_raydium_clmm_instruction(
        _u64_instruction(DEC_LIQ_LOG_DISC, 111, 222, 333),
        _accounts(4),
        "sig",
        1,
        0,
        None,
        10,
    ) is None


def test_parse_raydium_clmm_open_and_close_position() -> None:
    open_event = parse_raydium_clmm_instruction(
        _open_position_instruction(OPEN_POSITION_V2_DISC, -10, 20, 123),
        _accounts(4),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert open_event is not None
    assert open_event.type == EventType.RAYDIUM_CLMM_OPEN_POSITION
    assert isinstance(open_event.data, RaydiumClmmOpenPositionEvent)
    assert open_event.data.pool == "account_0"
    assert open_event.data.user == "account_1"
    assert open_event.data.position_nft_mint == "account_2"
    assert open_event.data.tick_lower_index == -10
    assert open_event.data.tick_upper_index == 20
    assert open_event.data.liquidity == "123"
    assert event_type_filter_allows_instruction_parsing([EventType.RAYDIUM_CLMM_OPEN_POSITION])
    routed = parse_instruction_unified(
        _open_position_instruction(OPEN_POSITION_V2_DISC, -10, 20, 123),
        _accounts(4),
        "sig",
        1,
        0,
        None,
        10,
        None,
        RAYDIUM_CLMM_PROGRAM_ID,
    )
    assert routed is not None
    assert routed.type == EventType.RAYDIUM_CLMM_OPEN_POSITION

    close_event = parse_raydium_clmm_instruction(CLOSE_POSITION_DISC, _accounts(4), "sig", 1, 0, None, 10)
    assert close_event is not None
    assert close_event.type == EventType.RAYDIUM_CLMM_CLOSE_POSITION
    assert isinstance(close_event.data, RaydiumClmmClosePositionEvent)
    assert close_event.data.pool == "account_0"
    assert close_event.data.user == "account_1"
    assert close_event.data.position_nft_mint == "account_2"
