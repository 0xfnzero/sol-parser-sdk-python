from __future__ import annotations

import struct

from sol_parser.account_fillers.raydium_launchlab import (
    fill_pool_create_accounts as fill_raydium_launchlab_pool_create_accounts,
    fill_trade_accounts as fill_raydium_launchlab_trade_accounts,
)
from sol_parser.event_types import (
    MeteoraDlmmSwapEvent,
    MeteoraPoolsSwapEvent,
    RaydiumClmmClosePositionEvent,
    RaydiumClmmDecreaseLiquidityEvent,
    RaydiumClmmOpenPositionEvent,
    RaydiumLaunchlabPoolCreateEvent,
    RaydiumLaunchlabTradeEvent,
)
from sol_parser.grpc_types import (
    EventType,
    all_event_types,
    event_type_filter_allows_instruction_parsing,
)
from sol_parser.instructions import (
    METEORA_DLMM_PROGRAM_ID,
    METEORA_POOLS_PROGRAM_ID,
    RAYDIUM_CLMM_PROGRAM_ID,
    RAYDIUM_LAUNCHLAB_PROGRAM_ID,
    parse_instruction_unified,
    parse_raydium_launchlab_instruction,
    parse_raydium_clmm_instruction,
)


DEC_LIQ_V2_DISC = bytes([58, 127, 188, 62, 79, 82, 196, 96])
DEC_LIQ_LOG_DISC = bytes([160, 38, 208, 111, 104, 91, 44, 1])
OPEN_POSITION_V2_DISC = bytes([77, 184, 74, 214, 112, 86, 241, 199])
CLOSE_POSITION_DISC = bytes([123, 134, 81, 0, 49, 68, 98, 98])
RAYDIUM_LAUNCHLAB_BUY_EXACT_IN_DISC = bytes([250, 234, 13, 123, 213, 156, 19, 236])
METEORA_POOLS_SWAP_DISC = bytes([248, 198, 158, 145, 225, 117, 135, 200])


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


def test_meteora_dbc_log_events_do_not_enable_instruction_prefilter() -> None:
    assert not event_type_filter_allows_instruction_parsing([EventType.METEORA_DBC_SWAP])


def test_parse_meteora_pools_and_dlmm_outer_instructions_are_routed() -> None:
    assert event_type_filter_allows_instruction_parsing([EventType.METEORA_POOLS_SWAP])
    pools = parse_instruction_unified(
        _u64_instruction(METEORA_POOLS_SWAP_DISC, 111, 222),
        _accounts(2),
        "sig",
        1,
        0,
        None,
        10,
        None,
        METEORA_POOLS_PROGRAM_ID,
    )
    assert pools is not None
    assert pools.type == EventType.METEORA_POOLS_SWAP
    assert isinstance(pools.data, MeteoraPoolsSwapEvent)
    assert pools.data.in_amount == 111
    assert pools.data.out_amount == 222

    assert event_type_filter_allows_instruction_parsing([EventType.METEORA_DLMM_SWAP])
    dlmm = parse_instruction_unified(
        bytes([11]) + struct.pack("<QQ", 333, 444),
        _accounts(3),
        "sig",
        1,
        0,
        None,
        10,
        None,
        METEORA_DLMM_PROGRAM_ID,
    )
    assert dlmm is not None
    assert dlmm.type == EventType.METEORA_DLMM_SWAP
    assert isinstance(dlmm.data, MeteoraDlmmSwapEvent)
    assert dlmm.data.pool == "account_0"
    assert dlmm.data.from_addr == "account_1"
    assert dlmm.data.amount_in == 333


def test_parse_raydium_launchlab_buy_exact_in_uses_rust_layout() -> None:
    ev = parse_raydium_launchlab_instruction(
        _u64_instruction(RAYDIUM_LAUNCHLAB_BUY_EXACT_IN_DISC, 111, 222),
        _accounts(6),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert ev is not None
    assert ev.type == EventType.RAYDIUM_LAUNCHLAB_TRADE
    assert ev.data.pool_state == "account_4"
    assert ev.data.user == "account_0"
    assert ev.data.amount_in == 111
    assert ev.data.amount_out == 222
    assert ev.data.is_buy is True
    assert ev.data.exact_in is True

    routed = parse_instruction_unified(
        _u64_instruction(RAYDIUM_LAUNCHLAB_BUY_EXACT_IN_DISC, 111, 222),
        _accounts(6),
        "sig",
        1,
        0,
        None,
        10,
        None,
        RAYDIUM_LAUNCHLAB_PROGRAM_ID,
    )
    assert routed is not None
    assert routed.type == EventType.RAYDIUM_LAUNCHLAB_TRADE


def test_raydium_launchlab_account_fillers_use_rust_indexes() -> None:
    trade = RaydiumLaunchlabTradeEvent(pool_state="11111111111111111111111111111111", user="")
    fill_raydium_launchlab_trade_accounts(trade, lambda i: f"account_{i}")
    assert trade.user == "account_0"
    assert trade.pool_state == "account_4"

    pool_create = RaydiumLaunchlabPoolCreateEvent(
        pool_state="11111111111111111111111111111111",
        creator="",
    )
    fill_raydium_launchlab_pool_create_accounts(pool_create, lambda i: f"account_{i}")
    assert pool_create.creator == "account_1"
    assert pool_create.pool_state == "account_5"


def test_non_pump_account_event_names_are_exposed_but_not_instruction_prefilter() -> None:
    events = all_event_types()
    assert EventType.ACCOUNT_RAYDIUM_CLMM_POOL_STATE in events
    assert EventType.ACCOUNT_RAYDIUM_CPMM_POOL_STATE in events
    assert EventType.ACCOUNT_ORCA_WHIRLPOOL in events
    assert not event_type_filter_allows_instruction_parsing(
        [
            EventType.ACCOUNT_RAYDIUM_CLMM_POOL_STATE,
            EventType.ACCOUNT_RAYDIUM_CPMM_POOL_STATE,
            EventType.ACCOUNT_ORCA_WHIRLPOOL,
        ]
    )
