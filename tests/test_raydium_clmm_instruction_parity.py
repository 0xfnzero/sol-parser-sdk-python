from __future__ import annotations

import struct
import base64

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
    IncludeOnlyFilter,
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
    parse_raydium_cpmm_instruction,
)
from sol_parser.parser import parse_log_optimized


DEC_LIQ_V2_DISC = bytes([58, 127, 188, 62, 79, 82, 196, 96])
DEC_LIQ_LOG_DISC = bytes([160, 38, 208, 111, 104, 91, 44, 1])
CREATE_CUSTOMIZABLE_POOL_DISC = bytes([43, 68, 212, 167, 89, 47, 164, 1])
OPEN_POSITION_DISC = bytes([135, 128, 47, 77, 15, 152, 240, 49])
OPEN_POSITION_V2_DISC = bytes([77, 184, 74, 214, 112, 86, 241, 199])
OPEN_POSITION_WITH_TOKEN_22_NFT_DISC = bytes([77, 255, 174, 82, 125, 29, 201, 46])
CLOSE_POSITION_DISC = bytes([123, 134, 81, 0, 49, 68, 98, 98])
CPMM_DEPOSIT_DISC = bytes([242, 35, 198, 137, 82, 225, 242, 182])
CPMM_WITHDRAW_DISC = bytes([183, 18, 70, 156, 148, 109, 161, 34])
CPMM_SWAP_IN_DISC = bytes([143, 190, 90, 218, 196, 30, 51, 222])
RAYDIUM_LAUNCHLAB_TRADE_DISC = bytes([189, 219, 127, 211, 78, 230, 97, 238])
DLMM_SWAP_DISC = bytes([143, 190, 90, 218, 196, 30, 51, 222])
RAYDIUM_LAUNCHLAB_BUY_EXACT_IN_DISC = bytes([250, 234, 13, 123, 213, 156, 19, 236])
METEORA_POOLS_SWAP_DISC = bytes([248, 198, 158, 145, 225, 117, 135, 200])
METEORA_DLMM_SWAP_DISC = bytes([248, 198, 158, 145, 225, 117, 135, 200])


def _accounts(n: int) -> list[str]:
    return [f"account_{i}" for i in range(n)]


def _u64_instruction(disc: bytes, *values: int) -> bytes:
    return disc + struct.pack("<" + "Q" * len(values), *values)


def _pk(seed: int) -> bytes:
    return bytes((seed + i) & 0xFF for i in range(32))


def _log(buf: bytes) -> str:
    return "Program data: " + base64.b64encode(buf).decode("ascii")


def _liquidity_instruction(disc: bytes, liquidity: int, amount0: int, amount1: int) -> bytes:
    return disc + liquidity.to_bytes(16, "little") + struct.pack("<QQ", amount0, amount1)


def _open_position_instruction(disc: bytes, lower: int, upper: int, liquidity: int) -> bytes:
    data = bytearray(8 + 4 + 4 + 4 + 4 + 16 + 8 + 8)
    data[:8] = disc
    struct.pack_into("<ii", data, 8, lower, upper)
    data[24:40] = liquidity.to_bytes(16, "little")
    return bytes(data)


def _create_customizable_pool_instruction(sqrt_price_x64: int) -> bytes:
    data = bytearray(8 + 16)
    data[:8] = CREATE_CUSTOMIZABLE_POOL_DISC
    data[8:24] = sqrt_price_x64.to_bytes(16, "little")
    return bytes(data)


def test_parse_raydium_clmm_decrease_uses_rust_v2_instruction_discriminator() -> None:
    ev = parse_raydium_clmm_instruction(
        _liquidity_instruction(DEC_LIQ_V2_DISC, (1 << 80) + 111, 222, 333),
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
    assert ev.data.pool == "account_3"
    assert ev.data.position_nft_mint == "account_1"
    assert ev.data.user == "account_0"
    assert ev.data.liquidity == str((1 << 80) + 111)
    assert ev.data.amount0_min == 222
    assert ev.data.amount1_min == 333

    assert parse_raydium_clmm_instruction(
        _liquidity_instruction(DEC_LIQ_LOG_DISC, 111, 222, 333),
        _accounts(4),
        "sig",
        1,
        0,
        None,
        10,
    ) is None


def test_parse_raydium_clmm_open_and_close_position() -> None:
    liquidity = (1 << 80) + 123
    open_event = parse_raydium_clmm_instruction(
        _open_position_instruction(OPEN_POSITION_V2_DISC, -10, 20, liquidity),
        _accounts(7),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert open_event is not None
    assert open_event.type == EventType.RAYDIUM_CLMM_OPEN_POSITION
    assert isinstance(open_event.data, RaydiumClmmOpenPositionEvent)
    assert open_event.data.pool == "account_5"
    assert open_event.data.user == "account_1"
    assert open_event.data.position_nft_mint == "account_2"
    assert open_event.data.tick_lower_index == -10
    assert open_event.data.tick_upper_index == 20
    assert open_event.data.liquidity == str(liquidity)
    assert event_type_filter_allows_instruction_parsing([EventType.RAYDIUM_CLMM_OPEN_POSITION])
    routed = parse_instruction_unified(
        _open_position_instruction(OPEN_POSITION_V2_DISC, -10, 20, 123),
        _accounts(7),
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

    legacy_open = parse_raydium_clmm_instruction(
        _open_position_instruction(OPEN_POSITION_DISC, -11, 21, 456),
        _accounts(7),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert legacy_open is not None
    assert isinstance(legacy_open.data, RaydiumClmmOpenPositionEvent)
    assert legacy_open.data.pool == "account_5"

    token22_open = parse_raydium_clmm_instruction(
        _open_position_instruction(OPEN_POSITION_WITH_TOKEN_22_NFT_DISC, -12, 22, 789),
        _accounts(7),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert token22_open is not None
    assert isinstance(token22_open.data, RaydiumClmmOpenPositionEvent)
    assert token22_open.data.pool == "account_4"

    close_event = parse_raydium_clmm_instruction(CLOSE_POSITION_DISC, _accounts(4), "sig", 1, 0, None, 10)
    assert close_event is not None
    assert close_event.type == EventType.RAYDIUM_CLMM_CLOSE_POSITION
    assert isinstance(close_event.data, RaydiumClmmClosePositionEvent)
    assert close_event.data.pool == "11111111111111111111111111111111"
    assert close_event.data.user == "account_0"
    assert close_event.data.position_nft_mint == "account_1"


def test_parse_raydium_clmm_create_customizable_pool_instruction() -> None:
    sqrt_price_x64 = (1 << 80) + 999
    ev = parse_raydium_clmm_instruction(
        _create_customizable_pool_instruction(sqrt_price_x64),
        _accounts(7),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert ev is not None
    assert ev.type == EventType.RAYDIUM_CLMM_CREATE_POOL
    assert ev.data.pool == "account_2"
    assert ev.data.creator == "account_0"
    assert ev.data.token_0_mint == "account_3"
    assert ev.data.token_1_mint == "account_4"
    assert ev.data.sqrt_price_x64 == str(sqrt_price_x64)
    assert ev.data.token_vault_0 == "account_5"
    assert ev.data.token_vault_1 == "account_6"
    assert ev.data.open_time == 0


def test_parse_raydium_cpmm_normal_instruction_uses_rust_accounts_and_defaults() -> None:
    deposit = parse_raydium_cpmm_instruction(
        _u64_instruction(CPMM_DEPOSIT_DISC, 111, 222, 333),
        _accounts(4),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert deposit is not None
    assert deposit.type == EventType.RAYDIUM_CPMM_DEPOSIT
    assert deposit.data.pool == "account_0"
    assert deposit.data.user == "account_1"
    assert deposit.data.lp_token_amount == 111
    assert deposit.data.token0_amount == 222
    assert deposit.data.token1_amount == 333

    withdraw = parse_raydium_cpmm_instruction(
        _u64_instruction(CPMM_WITHDRAW_DISC, 444, 555, 666),
        _accounts(4),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert withdraw is not None
    assert withdraw.type == EventType.RAYDIUM_CPMM_WITHDRAW
    assert withdraw.data.pool == "account_0"
    assert withdraw.data.user == "account_1"
    assert withdraw.data.lp_token_amount == 444
    assert withdraw.data.token0_amount == 555
    assert withdraw.data.token1_amount == 666

    swap = parse_raydium_cpmm_instruction(
        _u64_instruction(CPMM_SWAP_IN_DISC, 777, 888),
        _accounts(4),
        "sig",
        1,
        0,
        None,
        10,
    )
    assert swap is not None
    assert swap.type == EventType.RAYDIUM_CPMM_SWAP
    assert swap.data.pool_id == "account_3"
    assert swap.data.input_amount == 0
    assert swap.data.output_amount == 0
    assert swap.data.base_input is True


def test_log_shared_discriminators_respect_filter_and_program_scope() -> None:
    launchlab = bytearray(RAYDIUM_LAUNCHLAB_TRADE_DISC)
    payload = bytearray(139)
    payload[0:32] = _pk(10)
    struct.pack_into("<QQ", payload, 88, 111, 222)
    payload[136] = 0
    payload[138] = 1
    launchlab += payload
    ev = parse_log_optimized(
        _log(bytes(launchlab)),
        "sig",
        1,
        0,
        None,
        10,
        IncludeOnlyFilter([EventType.RAYDIUM_LAUNCHLAB_TRADE]),
        False,
    )
    assert ev is not None
    assert ev.type == EventType.RAYDIUM_LAUNCHLAB_TRADE
    assert ev.data.amount_in == 111
    assert ev.data.amount_out == 222
    assert ev.data.is_buy is True
    assert ev.data.exact_in is True

    dlmm = bytearray(DLMM_SWAP_DISC)
    payload = bytearray(32 + 32 + 4 + 4 + 8 + 8 + 1 + 8 + 8 + 16 + 8)
    payload[0:32] = _pk(11)
    payload[32:64] = _pk(12)
    struct.pack_into("<QQ", payload, 72, 333, 444)
    payload[88] = 1
    struct.pack_into("<QQ", payload, 89, 5, 6)
    struct.pack_into("<Q", payload, 121, 7)
    dlmm += payload
    ev = parse_log_optimized(
        _log(bytes(dlmm)),
        "sig",
        1,
        0,
        None,
        10,
        IncludeOnlyFilter([EventType.METEORA_DLMM_SWAP]),
        False,
        "",
        METEORA_DLMM_PROGRAM_ID,
    )
    assert ev is not None
    assert ev.type == EventType.METEORA_DLMM_SWAP
    assert ev.data.amount_in == 333
    assert ev.data.amount_out == 444


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
        _u64_instruction(METEORA_DLMM_SWAP_DISC, 333, 444),
        _accounts(11),
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
    assert dlmm.data.from_addr == "account_10"
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
