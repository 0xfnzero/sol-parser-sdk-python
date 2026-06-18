import base64
import struct

import base58

from sol_parser.accounts import (
    AccountData,
    PUMPFUN_BONDING_CURVE_BODY,
    PUMPFUN_GLOBAL_BODY,
    PUMPFUN_PROGRAM_ID,
    PUMP_FEES_PROGRAM_ID,
    _DISC_PUMPFUN_BONDING_CURVE,
    _DISC_PUMPFUN_FEE_CONFIG,
    _DISC_PUMPFUN_GLOBAL,
    parse_account_unified,
    parse_token_account,
)
from sol_parser.dex_parsers import PUMP_FEES_UPDATE_ADMIN, PUMP_FEES_UPDATE_FEE_SHARES
from sol_parser.grpc_types import (
    EventMetadata,
    EventType,
    ExcludeFilter,
    IncludeOnlyFilter,
    event_type_filter_allows_instruction_parsing,
    event_type_filter_includes_pumpfun,
    event_type_filter_includes_pump_fees,
    event_type_filter_includes_pumpswap,
    event_type_filter_includes_meteora_dlmm,
    event_type_filter_includes_meteora_pools,
    event_type_filter_includes_raydium_cpmm,
    event_type_filter_includes_raydium_launchlab,
    all_event_types,
)
from sol_parser.event_type_parity import RUST_EVENT_TYPES
from sol_parser.parser import parse_log_optimized, parse_log_optimized_with_program_id
from sol_parser.instructions import (
    METEORA_DAMM_V2_PROGRAM_ID,
    METEORA_DBC_PROGRAM_ID,
    RAYDIUM_CLMM_PROGRAM_ID,
    parse_instruction_unified,
)
from sol_parser.grpc_instruction_parser import should_parse_instructions
from sol_parser.accounts.raydium_orca import ORCA_WHIRLPOOL_PROGRAM_ID, RAYDIUM_CPMM_PROGRAM_ID
import sol_parser.rpc_parser as rpc_parser


def _pump_fees_update_admin_log() -> str:
    buf = struct.pack("<Q", PUMP_FEES_UPDATE_ADMIN) + bytes(8 + 32 + 32)
    return "Program data: " + base64.b64encode(buf).decode("ascii")


def _push_string(buf: bytearray, value: str) -> None:
    raw = value.encode("utf-8")
    buf.extend(struct.pack("<I", len(raw)))
    buf.extend(raw)


def _pumpfun_buy_exact_sol_in_trade_log() -> str:
    buf = bytearray()
    buf += bytes([189, 219, 127, 211, 78, 230, 97, 238])
    buf += _pk(1)
    for value in (10, 20):
        buf += struct.pack("<Q", value)
    buf += bytes([1])
    buf += _pk(2)
    buf += struct.pack("<q", 30)
    for value in (40, 50, 60, 70):
        buf += struct.pack("<Q", value)
    buf += _pk(3)
    for value in (80, 90):
        buf += struct.pack("<Q", value)
    buf += _pk(4)
    for value in (100, 110):
        buf += struct.pack("<Q", value)
    buf += bytes([0])
    for value in (120, 130, 140):
        buf += struct.pack("<Q", value)
    buf += struct.pack("<q", 150)
    _push_string(buf, "buy_exact_sol_in")
    return "Program data: " + base64.b64encode(bytes(buf)).decode("ascii")


def _pump_fees_large_update_fee_shares_log() -> str:
    buf = bytearray()
    buf += struct.pack("<Q", PUMP_FEES_UPDATE_FEE_SHARES)
    buf += struct.pack("<q", 1_777_920_719)
    buf += _pk(1)
    buf += _pk(2)
    buf += _pk(3)
    buf += struct.pack("<I", 64)
    for i in range(64):
        buf += _pk(40 + i)
        buf += struct.pack("<H", 1000 + i)
    assert len(buf) > 2048
    return "Program data: " + base64.b64encode(bytes(buf)).decode("ascii")


def _dbc_swap_log() -> str:
    buf = bytearray()
    buf += struct.pack("<Q", 0x93BBAA8AD5153C1B)
    buf += bytes([1]) * 32
    buf += bytes([2]) * 32
    buf += bytes([1, 1])
    for value in (10, 9, 10, 8):
        buf += struct.pack("<Q", value)
    buf += (1 << 64).to_bytes(16, "little")
    for value in (1, 2, 3, 10, 123):
        buf += struct.pack("<Q", value)
    return "Program data: " + base64.b64encode(bytes(buf)).decode("ascii")


def _cpmm_create_pool_log() -> str:
    buf = bytearray()
    buf += bytes([233, 146, 209, 142, 207, 104, 64, 188])
    buf += _pk(10)
    buf += _pk(11)
    buf += _pk(12)
    buf += _pk(13)
    buf += struct.pack("<Q", 1000)
    buf += struct.pack("<Q", 2000)
    return "Program data: " + base64.b64encode(bytes(buf)).decode("ascii")


def _damm_add_liquidity_log() -> str:
    buf = bytearray()
    buf += bytes([175, 242, 8, 157, 30, 247, 185, 169])
    buf += _pk(20)
    buf += _pk(21)
    buf += _pk(22)
    buf += (123).to_bytes(16, "little")
    for value in (1, 2, 3, 4, 5, 6):
        buf += struct.pack("<Q", value)
    return "Program data: " + base64.b64encode(bytes(buf)).decode("ascii")


def _clmm_open_limit_order_log() -> str:
    buf = bytearray()
    buf += bytes([106, 24, 71, 85, 57, 169, 158, 216])
    buf += bytes([1]) * 32
    buf += bytes([2]) * 32
    buf += bytes([1])
    buf += struct.pack("<i", -123)
    buf += struct.pack("<Q", 456)
    buf += struct.pack("<Q", 7)
    return "Program data: " + base64.b64encode(bytes(buf)).decode("ascii")


def _pk(seed: int) -> bytes:
    return bytes(((seed + i) & 0xFF) for i in range(32))


def _pk_str(seed: int) -> str:
    return base58.b58encode(_pk(seed)).decode()


PUMPFUN_TRADE_DISC = bytes([189, 219, 127, 211, 78, 230, 97, 238])
EVENT_CPI_SUFFIX = bytes([155, 167, 108, 32, 122, 76, 173, 64])


def _pumpfun_trade_payload(ix_name: str) -> bytes:
    buf = bytearray()
    buf += _pk(70)
    for value in (10, 20):
        buf += struct.pack("<Q", value)
    buf += bytes([1])
    buf += _pk(71)
    buf += struct.pack("<q", 30)
    for value in (40, 50, 60, 70):
        buf += struct.pack("<Q", value)
    buf += _pk(72)
    for value in (80, 90):
        buf += struct.pack("<Q", value)
    buf += _pk(73)
    for value in (100, 110):
        buf += struct.pack("<Q", value)
    buf += bytes([0])
    for value in (120, 130, 140):
        buf += struct.pack("<Q", value)
    buf += struct.pack("<q", 150)
    _push_string(buf, ix_name)
    return bytes(buf)


def _pumpfun_trade_log(ix_name: str) -> str:
    return "Program data: " + base64.b64encode(PUMPFUN_TRADE_DISC + _pumpfun_trade_payload(ix_name)).decode("ascii")


def _u128(value: int) -> bytes:
    return value.to_bytes(16, "little")


def test_event_type_inventory_matches_rust():
    assert [event_type.value for event_type in all_event_types()] == RUST_EVENT_TYPES


def test_parse_log_optimized_applies_event_type_filter():
    log = _pump_fees_update_admin_log()

    ev = parse_log_optimized(log, "sig", 1, grpc_recv_us=1)
    assert ev is not None
    assert ev.type == EventType.PUMP_FEES_UPDATE_ADMIN

    ev = parse_log_optimized(
        log,
        "sig",
        1,
        grpc_recv_us=1,
        event_type_filter=IncludeOnlyFilter([EventType.PUMP_FEES_UPDATE_ADMIN]),
    )
    assert ev is not None
    assert ev.type == EventType.PUMP_FEES_UPDATE_ADMIN

    assert (
        parse_log_optimized(
            log,
            "sig",
            1,
            grpc_recv_us=1,
            event_type_filter=IncludeOnlyFilter([EventType.PUMP_FUN_CREATE]),
        )
        is None
    )
    assert (
        parse_log_optimized(
            log,
            "sig",
            1,
            grpc_recv_us=1,
            event_type_filter=ExcludeFilter([EventType.PUMP_FEES_UPDATE_ADMIN]),
        )
        is None
    )


def test_parse_log_optimized_accepts_large_program_data_payloads():
    ev = parse_log_optimized(
        _pump_fees_large_update_fee_shares_log(),
        "sig",
        1,
        grpc_recv_us=1,
        event_type_filter=IncludeOnlyFilter([EventType.PUMP_FEES_UPDATE_FEE_SHARES]),
    )
    assert ev is not None
    assert ev.type == EventType.PUMP_FEES_UPDATE_FEE_SHARES
    assert len(ev.data.new_shareholders) == 64
    assert ev.data.new_shareholders[-1].share_bps == 1063


def test_scoped_pumpfun_trade_prefilter_accepts_buy_family_filters():
    ev = parse_log_optimized_with_program_id(
        _pumpfun_buy_exact_sol_in_trade_log(),
        "sig",
        1,
        grpc_recv_us=1,
        event_type_filter=IncludeOnlyFilter([EventType.PUMP_FUN_BUY]),
        program_id=PUMPFUN_PROGRAM_ID,
    )
    assert ev is not None
    assert ev.type == EventType.PUMP_FUN_BUY_EXACT_SOL_IN


def test_parse_log_optimized_uses_program_context_for_meteora_dbc():
    log = _dbc_swap_log()
    filter = IncludeOnlyFilter([EventType.METEORA_DBC_SWAP])

    assert parse_log_optimized(log, "sig", 1, grpc_recv_us=1, event_type_filter=filter) is None

    ev = parse_log_optimized_with_program_id(
        log,
        "sig",
        1,
        grpc_recv_us=1,
        event_type_filter=filter,
        program_id=METEORA_DBC_PROGRAM_ID,
    )
    assert ev is not None
    assert ev.type == EventType.METEORA_DBC_SWAP
    assert ev.data.output_amount == 8
    assert ev.data.current_timestamp == 123


def test_parse_log_optimized_routes_scoped_cpmm_create_pool_without_clmm_leak():
    log = _cpmm_create_pool_log()

    assert (
        parse_log_optimized(
            log,
            "sig",
            1,
            grpc_recv_us=1,
            event_type_filter=IncludeOnlyFilter([EventType.RAYDIUM_CPMM_INITIALIZE]),
        )
        is None
    )

    cpmm = parse_log_optimized_with_program_id(
        log,
        "sig",
        1,
        grpc_recv_us=1,
        event_type_filter=IncludeOnlyFilter([EventType.RAYDIUM_CPMM_INITIALIZE]),
        program_id=RAYDIUM_CPMM_PROGRAM_ID,
    )
    assert cpmm is not None
    assert cpmm.type == EventType.RAYDIUM_CPMM_INITIALIZE
    assert cpmm.data.init_amount0 == 1000

    assert (
        parse_log_optimized_with_program_id(
            log,
            "sig",
            1,
            grpc_recv_us=1,
            event_type_filter=IncludeOnlyFilter([EventType.RAYDIUM_CLMM_CREATE_POOL]),
            program_id=RAYDIUM_CLMM_PROGRAM_ID,
        )
        is None
    )


def test_parse_log_optimized_parses_scoped_damm_non_swap_program_data():
    ev = parse_log_optimized_with_program_id(
        _damm_add_liquidity_log(),
        "sig",
        1,
        grpc_recv_us=1,
        event_type_filter=IncludeOnlyFilter([EventType.METEORA_DAMM_V2_ADD_LIQUIDITY]),
        program_id=METEORA_DAMM_V2_PROGRAM_ID,
    )

    assert ev is not None
    assert ev.type == EventType.METEORA_DAMM_V2_ADD_LIQUIDITY
    assert ev.data.liquidity_delta == "123"
    assert ev.data.token_b_amount == 4


def test_protocol_helper_exclude_matches_rust_semantics():
    assert event_type_filter_includes_pump_fees(
        ExcludeFilter([EventType.PUMP_FEES_UPDATE_ADMIN])
    )
    assert event_type_filter_includes_raydium_cpmm(
        ExcludeFilter([EventType.RAYDIUM_CPMM_SWAP])
    )
    assert not event_type_filter_includes_raydium_cpmm(
        ExcludeFilter(
            [
                EventType.RAYDIUM_CPMM_SWAP,
                EventType.RAYDIUM_CPMM_DEPOSIT,
                EventType.RAYDIUM_CPMM_WITHDRAW,
                EventType.RAYDIUM_CPMM_INITIALIZE,
            ]
        )
    )
    assert not event_type_filter_includes_raydium_launchlab(
        ExcludeFilter(
            [
                EventType.RAYDIUM_LAUNCHLAB_TRADE,
                EventType.RAYDIUM_LAUNCHLAB_POOL_CREATE,
                EventType.RAYDIUM_LAUNCHLAB_MIGRATE_AMM,
            ]
        )
    )
    assert event_type_filter_includes_pumpswap(
        IncludeOnlyFilter([EventType.PUMP_SWAP_TRADE])
    )
    assert event_type_filter_allows_instruction_parsing([EventType.PUMP_SWAP_TRADE])
    assert not event_type_filter_includes_pumpfun(
        IncludeOnlyFilter([EventType.ACCOUNT_PUMP_FUN_GLOBAL])
    )
    assert not event_type_filter_allows_instruction_parsing(
        [EventType.ACCOUNT_PUMP_FUN_GLOBAL]
    )
    assert not event_type_filter_includes_pumpfun(
        IncludeOnlyFilter([EventType.PUMP_FEES_UPDATE_ADMIN])
    )
    assert event_type_filter_allows_instruction_parsing(
        [EventType.PUMP_FEES_UPDATE_ADMIN]
    )
    assert event_type_filter_allows_instruction_parsing(
        [EventType.METEORA_DAMM_V2_INITIALIZE_POOL]
    )
    assert event_type_filter_includes_meteora_pools(
        IncludeOnlyFilter([EventType.METEORA_POOLS_SWAP])
    )
    assert not event_type_filter_includes_meteora_pools(
        IncludeOnlyFilter([EventType.PUMP_FUN_TRADE])
    )
    assert event_type_filter_includes_meteora_dlmm(
        IncludeOnlyFilter([EventType.METEORA_DLMM_SWAP])
    )
    assert not event_type_filter_includes_meteora_dlmm(
        IncludeOnlyFilter([EventType.PUMP_FUN_TRADE])
    )
    assert event_type_filter_allows_instruction_parsing([EventType.RAYDIUM_AMM_V4_DEPOSIT])
    assert event_type_filter_allows_instruction_parsing([EventType.RAYDIUM_CLMM_OPEN_LIMIT_ORDER])
    assert IncludeOnlyFilter([EventType.RAYDIUM_CLMM_OPEN_LIMIT_ORDER]).should_include(
        EventType.RAYDIUM_CLMM_OPEN_LIMIT_ORDER
    )
    assert not IncludeOnlyFilter([EventType.PUMP_SWAP_TRADE]).should_include(
        EventType.PUMP_FUN_BUY
    )
    assert IncludeOnlyFilter([EventType.PUMP_SWAP_TRADE]).should_include(
        EventType.PUMP_SWAP_BUY
    )
    assert not ExcludeFilter([EventType.PUMP_SWAP_TRADE]).should_include(
        EventType.PUMP_SWAP_SELL
    )


def test_parse_raydium_clmm_advanced_log_event_and_filter():
    log = _clmm_open_limit_order_log()
    ev = parse_log_optimized(
        log,
        "sig",
        1,
        grpc_recv_us=1,
        event_type_filter=IncludeOnlyFilter([EventType.RAYDIUM_CLMM_OPEN_LIMIT_ORDER]),
    )
    assert ev is not None
    assert ev.type == EventType.RAYDIUM_CLMM_OPEN_LIMIT_ORDER
    assert ev.data.pool_id == base58.b58encode(bytes([1]) * 32).decode()
    assert ev.data.limit_order == base58.b58encode(bytes([2]) * 32).decode()
    assert ev.data.zero_for_one is True
    assert ev.data.tick_index == -123
    assert ev.data.total_amount == 456
    assert ev.data.transfer_fee == 7
    assert (
        parse_log_optimized(
            log,
            "sig",
            1,
            grpc_recv_us=1,
            event_type_filter=ExcludeFilter([EventType.RAYDIUM_CLMM_OPEN_LIMIT_ORDER]),
        )
        is None
    )


def test_parse_raydium_clmm_base_program_data_layouts():
    swap = bytearray()
    swap += bytes([64, 198, 205, 232, 38, 8, 113, 226])
    swap += _pk(1)
    swap += _pk(2)
    swap += _pk(3)
    swap += _pk(4)
    swap += struct.pack("<QQQQ", 10, 1, 20, 2)
    swap += bytes([1])
    swap += _u128((1 << 80) + 30)
    swap += _u128((1 << 96) + 40)
    swap += struct.pack("<i", -77)

    ev = parse_log_optimized("Program data: " + base64.b64encode(bytes(swap)).decode(), "sig", 1, grpc_recv_us=1)
    assert ev is not None
    assert ev.type == EventType.RAYDIUM_CLMM_SWAP
    assert ev.data.pool_state == _pk_str(1)
    assert ev.data.sender == _pk_str(2)
    assert ev.data.token_account_0 == _pk_str(3)
    assert ev.data.token_account_1 == _pk_str(4)
    assert ev.data.amount_0 == 10
    assert ev.data.transfer_fee_0 == 1
    assert ev.data.amount_1 == 20
    assert ev.data.transfer_fee_1 == 2
    assert ev.data.zero_for_one is True
    assert ev.data.sqrt_price_x64 == str((1 << 80) + 30)
    assert ev.data.liquidity == str((1 << 96) + 40)
    assert ev.data.tick == -77

    create = bytearray()
    create += bytes([25, 94, 75, 47, 112, 99, 53, 63])
    create += _pk(5)
    create += _pk(6)
    create += struct.pack("<H", 64)
    create += _pk(7)
    create += _u128((1 << 72) + 55)
    create += struct.pack("<i", 88)
    create += _pk(8)
    create += _pk(9)

    ev = parse_log_optimized("Program data: " + base64.b64encode(bytes(create)).decode(), "sig", 1, grpc_recv_us=1)
    assert ev is not None
    assert ev.type == EventType.RAYDIUM_CLMM_CREATE_POOL
    assert ev.data.token_0_mint == _pk_str(5)
    assert ev.data.token_1_mint == _pk_str(6)
    assert ev.data.tick_spacing == 64
    assert ev.data.pool == _pk_str(7)
    assert ev.data.sqrt_price_x64 == str((1 << 72) + 55)
    assert ev.data.tick == 88
    assert ev.data.token_vault_0 == _pk_str(8)
    assert ev.data.token_vault_1 == _pk_str(9)

    old_instruction_disc = bytes([248, 198, 158, 145, 225, 117, 135, 200]) + _pk(1)
    assert (
        parse_log_optimized(
            "Program data: " + base64.b64encode(old_instruction_disc).decode(),
            "sig",
            1,
            grpc_recv_us=1,
        )
        is None
    )


def test_parse_raydium_clmm_collect_fee_logs():
    personal = bytearray()
    personal += bytes([166, 174, 105, 192, 81, 161, 83, 105])
    personal += _pk(10)
    personal += _pk(11)
    personal += _pk(12)
    personal += struct.pack("<QQ", 70, 80)

    ev = parse_log_optimized(
        "Program data: " + base64.b64encode(bytes(personal)).decode(),
        "sig",
        1,
        grpc_recv_us=1,
        event_type_filter=IncludeOnlyFilter([EventType.RAYDIUM_CLMM_COLLECT_FEE]),
    )
    assert ev is not None
    assert ev.type == EventType.RAYDIUM_CLMM_COLLECT_FEE
    assert ev.data.position_nft_mint == _pk_str(10)
    assert ev.data.recipient_token_account_0 == _pk_str(11)
    assert ev.data.recipient_token_account_1 == _pk_str(12)
    assert ev.data.amount_0 == 70
    assert ev.data.amount_1 == 80

    protocol = bytearray()
    protocol += bytes([206, 87, 17, 79, 45, 41, 213, 61])
    protocol += _pk(13)
    protocol += _pk(14)
    protocol += _pk(15)
    protocol += struct.pack("<QQ", 90, 100)

    ev = parse_log_optimized(
        "Program data: " + base64.b64encode(bytes(protocol)).decode(),
        "sig",
        1,
        grpc_recv_us=1,
        event_type_filter=IncludeOnlyFilter([EventType.RAYDIUM_CLMM_COLLECT_FEE]),
    )
    assert ev is not None
    assert ev.type == EventType.RAYDIUM_CLMM_COLLECT_FEE
    assert ev.data.pool_state == _pk_str(13)
    assert ev.data.recipient_token_account_0 == _pk_str(14)
    assert ev.data.recipient_token_account_1 == _pk_str(15)
    assert ev.data.amount_0 == 90
    assert ev.data.amount_1 == 100


def test_rpc_instruction_parser_uses_loaded_address_table_keys(monkeypatch):
    calls = []

    def fake_parse_instruction_unified(
        data,
        accounts,
        signature,
        slot,
        tx_index,
        block_time_us,
        grpc_recv_us,
        filter,
        program_id,
    ):
        calls.append((program_id, list(accounts), tx_index))
        return None

    monkeypatch.setattr(rpc_parser, "parse_instruction_unified", fake_parse_instruction_unified)
    monkeypatch.setattr(rpc_parser, "rpc_response_to_solana_storage", lambda tx: (None, None))

    static_key = "11111111111111111111111111111111"
    readonly_key = "So11111111111111111111111111111111111111112"
    tx = rpc_parser.RpcTransactionResponse(
        slot=7,
        block_time=None,
        meta=rpc_parser.RpcTransactionMeta(
            fee=0,
            pre_balances=[],
            post_balances=[],
            log_messages=[],
            inner_instructions=[],
            pre_token_balances=[],
            post_token_balances=[],
            loaded_addresses=rpc_parser.RpcLoadedAddresses(
                writable=[RAYDIUM_CLMM_PROGRAM_ID],
                readonly=[readonly_key],
            ),
            compute_units_consumed=None,
        ),
        transaction=rpc_parser.RpcTransaction(
            signatures=["sig"],
            message=rpc_parser.RpcMessage(
                account_keys=[static_key],
                header=None,
                recent_blockhash="",
                instructions=[
                    rpc_parser.RpcCompiledInstruction(
                        program_id_index=1,
                        accounts=bytes([0, 2]),
                        data=b"\x01",
                    )
                ],
                address_table_lookups=[],
            ),
        ),
        transaction_index=42,
    )

    events, err = rpc_parser.parse_rpc_transaction(tx, "sig", None, 99)

    assert err is None
    assert events == []
    assert calls == [(RAYDIUM_CLMM_PROGRAM_ID, [static_key, readonly_key], 42)]


def test_rpc_instruction_parser_none_filter_parses_instructions(monkeypatch):
    monkeypatch.setattr(rpc_parser, "rpc_response_to_solana_storage", lambda tx: (None, None))

    data = bytearray(8 + 4 + 4 + 4 + 4 + 16 + 8 + 8)
    data[:8] = bytes([77, 184, 74, 214, 112, 86, 241, 199])
    struct.pack_into("<ii", data, 8, -10, 20)
    data[24:40] = (123).to_bytes(16, "little")

    tx = rpc_parser.RpcTransactionResponse(
        slot=7,
        block_time=None,
        meta=rpc_parser.RpcTransactionMeta(
            fee=0,
            pre_balances=[],
            post_balances=[],
            log_messages=[],
            inner_instructions=[],
            pre_token_balances=[],
            post_token_balances=[],
            loaded_addresses=None,
            compute_units_consumed=None,
        ),
        transaction=rpc_parser.RpcTransaction(
            signatures=["sig"],
            message=rpc_parser.RpcMessage(
                    account_keys=[
                        RAYDIUM_CLMM_PROGRAM_ID,
                        "account_0",
                        "user",
                        "position_nft_mint",
                        "position",
                        "account_4",
                        "pool",
                    ],
                header=None,
                recent_blockhash="",
                instructions=[
                    rpc_parser.RpcCompiledInstruction(
                            program_id_index=0,
                            accounts=bytes([1, 2, 3, 4, 5, 6]),
                            data=bytes(data),
                        )
                ],
                address_table_lookups=[],
            ),
        ),
        transaction_index=42,
    )

    events, err = rpc_parser.parse_rpc_transaction(tx, "sig", None, 99)

    assert err is None
    assert len(events) == 1
    assert events[0].type == EventType.RAYDIUM_CLMM_OPEN_POSITION
    assert events[0].data.metadata.tx_index == 42
    assert events[0].data.pool == "pool"
    assert events[0].data.user == "user"
    assert events[0].data.position_nft_mint == "position_nft_mint"


def test_empty_include_only_filter_skips_instruction_prefilter():
    assert not should_parse_instructions(IncludeOnlyFilter([]))
    assert (
        parse_instruction_unified(
            b"\x01\x02\x03\x04\x05\x06\x07\x08",
            [],
            "sig",
            1,
            0,
            None,
            1,
            IncludeOnlyFilter([]),
            RAYDIUM_CLMM_PROGRAM_ID,
        )
        is None
    )
    assert (
        parse_instruction_unified(
            b"\x01\x02\x03\x04\x05\x06\x07\x08",
            [],
            "sig",
            1,
            0,
            None,
            1,
            IncludeOnlyFilter([EventType.ACCOUNT_RAYDIUM_CLMM_POOL_STATE]),
            RAYDIUM_CLMM_PROGRAM_ID,
        )
        is None
    )


def test_pumpfun_global_account_returns_dex_event_wrapper():
    data = _DISC_PUMPFUN_GLOBAL + bytes(PUMPFUN_GLOBAL_BODY)
    account = AccountData(
        pubkey="pubkey",
        executable=False,
        lamports=1,
        owner=PUMPFUN_PROGRAM_ID,
        rent_epoch=0,
        data=data,
    )
    ev = parse_account_unified(
        account,
        EventMetadata(signature="sig", slot=1, tx_index=0, block_time_us=0, grpc_recv_us=1),
        IncludeOnlyFilter([EventType.ACCOUNT_PUMP_FUN_GLOBAL]),
    )
    assert ev is not None
    assert ev.type == EventType.ACCOUNT_PUMP_FUN_GLOBAL
    assert ev.data["pubkey"] == "pubkey"


def test_account_filter_uses_actual_parsed_event_type():
    account = AccountData(
        pubkey="bonding_curve",
        executable=False,
        lamports=1,
        owner=PUMPFUN_PROGRAM_ID,
        rent_epoch=0,
        data=_DISC_PUMPFUN_BONDING_CURVE + bytes(PUMPFUN_BONDING_CURVE_BODY),
    )
    ev = parse_account_unified(
        account,
        EventMetadata(signature="sig", slot=1, tx_index=0, block_time_us=0, grpc_recv_us=1),
        IncludeOnlyFilter([EventType.ACCOUNT_PUMP_FUN_GLOBAL]),
    )
    assert ev is None


def test_token_info_include_only_does_not_emit_token_account():
    data = bytearray(82)
    data[36:44] = struct.pack("<Q", 1_000_000)
    data[44] = 6
    account = AccountData(
        pubkey="mint",
        executable=False,
        lamports=1,
        owner="TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA",
        rent_epoch=0,
        data=bytes(data),
    )
    metadata = EventMetadata(signature="sig", slot=1, tx_index=0, block_time_us=0, grpc_recv_us=1)

    ev = parse_account_unified(account, metadata, IncludeOnlyFilter([EventType.TOKEN_INFO]))
    assert ev is not None
    assert ev.type == EventType.TOKEN_INFO

    assert parse_account_unified(
        account,
        metadata,
        IncludeOnlyFilter([EventType.TOKEN_ACCOUNT]),
    ) is None


def test_known_dex_owner_does_not_fall_through_to_token_parser():
    data = bytearray(82)
    data[36:44] = struct.pack("<Q", 1_000_000)
    data[44] = 6
    account = AccountData(
        pubkey="not_a_pumpfun_account",
        executable=False,
        lamports=1,
        owner=PUMPFUN_PROGRAM_ID,
        rent_epoch=0,
        data=bytes(data),
    )
    metadata = EventMetadata(signature="sig", slot=1, tx_index=0, block_time_us=0, grpc_recv_us=1)

    assert parse_account_unified(account, metadata) is None


def test_token_parser_rejects_non_token_program_owner():
    data = bytearray(82)
    data[36:44] = struct.pack("<Q", 1_000_000)
    data[44] = 6
    account = AccountData(
        pubkey="not_a_token_mint",
        executable=False,
        lamports=1,
        owner=RAYDIUM_CLMM_PROGRAM_ID,
        rent_epoch=0,
        data=bytes(data),
    )
    metadata = EventMetadata(signature="sig", slot=1, tx_index=0, block_time_us=0, grpc_recv_us=1)

    assert parse_token_account(account, metadata) is None


def test_pumpfun_account_parsers_are_exported() -> None:
    import sol_parser.accounts as accounts

    for name in (
        "parse_pumpfun_bonding_curve",
        "parse_pumpfun_fee_config",
        "parse_pumpfun_sharing_config",
        "parse_pumpfun_global_volume_accumulator",
        "parse_pumpfun_user_volume_accumulator",
        "parse_raydium_clmm_account",
        "parse_raydium_cpmm_account",
        "parse_orca_whirlpool_account",
        "PUMP_FEES_PROGRAM_ID",
    ):
        assert name in accounts.__all__


def _u64(value: int) -> bytes:
    return value.to_bytes(8, "little")


def _u32(value: int) -> bytes:
    return value.to_bytes(4, "little")


def _u16(value: int) -> bytes:
    return value.to_bytes(2, "little")


def _pk(seed: int) -> bytes:
    return bytes([seed]) * 32


def _pk58(seed: int) -> str:
    return base58.b58encode(_pk(seed)).decode("ascii")


def test_pumpfun_bonding_curve_account_reads_quote_fields():
    creator = _pk(7)
    quote_mint = _pk(8)
    data = b"".join(
        [
            _DISC_PUMPFUN_BONDING_CURVE,
            _u64(100),
            _u64(4_292_000_000),
            _u64(200),
            _u64(3_000_000_000),
            _u64(1_000),
            b"\x01",
            creator,
            b"\x01",
            b"\x00",
            quote_mint,
        ]
    )
    assert len(data) == 8 + PUMPFUN_BONDING_CURVE_BODY
    account = AccountData(
        pubkey="bonding_curve",
        executable=False,
        lamports=1,
        owner=PUMPFUN_PROGRAM_ID,
        rent_epoch=0,
        data=data,
    )

    ev = parse_account_unified(
        account,
        EventMetadata(signature="sig", slot=1, tx_index=0, block_time_us=0, grpc_recv_us=1),
        IncludeOnlyFilter([EventType.ACCOUNT_PUMP_FUN_BONDING_CURVE]),
    )

    assert ev is not None
    assert ev.type == EventType.ACCOUNT_PUMP_FUN_BONDING_CURVE
    curve = ev.data["bonding_curve"]
    assert curve["virtual_quote_reserves"] == 4_292_000_000
    assert curve["real_quote_reserves"] == 3_000_000_000
    assert curve["creator"] == base58.b58encode(creator).decode("ascii")
    assert curve["quote_mint"] == base58.b58encode(quote_mint).decode("ascii")
    assert curve["complete"] is True
    assert curve["is_mayhem_mode"] is True
    assert curve["is_cashback_coin"] is False


def test_pumpfun_fee_config_rejects_truncated_vector():
    data = b"".join(
        [
            _DISC_PUMPFUN_FEE_CONFIG,
            b"\x01",
            _pk(1),
            _u64(1),
            _u64(2),
            _u64(3),
            (1).to_bytes(4, "little"),
        ]
    )
    account = AccountData(
        pubkey="fee_config",
        executable=False,
        lamports=1,
        owner=PUMP_FEES_PROGRAM_ID,
        rent_epoch=0,
        data=data,
    )

    ev = parse_account_unified(
        account,
        EventMetadata(signature="sig", slot=1, tx_index=0, block_time_us=0, grpc_recv_us=1),
        IncludeOnlyFilter([EventType.ACCOUNT_PUMP_FUN_FEE_CONFIG]),
    )

    assert ev is None


def test_raydium_clmm_account_parser_reads_amm_config():
    disc = bytes([218, 244, 33, 104, 203, 203, 43, 111])
    data = b"".join(
        [
            disc,
            b"\x09",
            _u16(7),
            _pk(1),
            _u32(111),
            _u32(222),
            _u16(64),
            _u32(333),
            _u32(444),
            _pk(2),
            _u64(1),
            _u64(2),
            _u64(3),
        ]
    )
    account = AccountData(
        pubkey="clmm_amm_config",
        executable=False,
        lamports=1,
        owner=RAYDIUM_CLMM_PROGRAM_ID,
        rent_epoch=0,
        data=data,
    )

    ev = parse_account_unified(
        account,
        EventMetadata(signature="sig", slot=1, tx_index=0, block_time_us=0, grpc_recv_us=1),
        IncludeOnlyFilter([EventType.ACCOUNT_RAYDIUM_CLMM_AMM_CONFIG]),
    )

    assert ev is not None
    assert ev.type == EventType.ACCOUNT_RAYDIUM_CLMM_AMM_CONFIG
    assert ev.data["amm_config"]["owner"] == _pk58(1)
    assert ev.data["amm_config"]["tick_spacing"] == 64
    assert ev.data["amm_config"]["padding"] == [1, 2, 3]


def test_raydium_cpmm_account_parser_scopes_shared_discriminators():
    disc = bytes([247, 237, 227, 245, 215, 195, 222, 70])
    data = bytearray(disc)
    for seed in range(1, 11):
        data += _pk(seed)
    data += bytes([11, 1, 9, 6, 6])
    for value in (100, 1, 2, 3, 4, 123456, 99):
        data += _u64(value)
    data += bytes([2, 1])
    data += bytes(6)
    data += _u64(5)
    data += _u64(6)
    for value in range(28):
        data += _u64(value)
    account = AccountData(
        pubkey="cpmm_pool",
        executable=False,
        lamports=1,
        owner=RAYDIUM_CPMM_PROGRAM_ID,
        rent_epoch=0,
        data=bytes(data),
    )

    ev = parse_account_unified(
        account,
        EventMetadata(signature="sig", slot=1, tx_index=0, block_time_us=0, grpc_recv_us=1),
        IncludeOnlyFilter([EventType.ACCOUNT_RAYDIUM_CPMM_POOL_STATE]),
    )

    assert ev is not None
    assert ev.type == EventType.ACCOUNT_RAYDIUM_CPMM_POOL_STATE
    assert ev.data["pool_state"]["auth_bump"] == 11
    assert ev.data["pool_state"]["lp_supply"] == 100
    assert ev.data["pool_state"]["enable_creator_fee"] is True
    assert (
        parse_account_unified(
            account,
            EventMetadata(signature="sig", slot=1, tx_index=0, block_time_us=0, grpc_recv_us=1),
            IncludeOnlyFilter([EventType.ACCOUNT_RAYDIUM_CLMM_POOL_STATE]),
        )
        is None
    )


def test_orca_whirlpool_account_parser_reads_fee_tier():
    disc = bytes([56, 75, 159, 76, 142, 68, 190, 105])
    data = b"".join([disc, _pk(9), _u16(128), _u16(500)])
    account = AccountData(
        pubkey="orca_fee_tier",
        executable=False,
        lamports=1,
        owner=ORCA_WHIRLPOOL_PROGRAM_ID,
        rent_epoch=0,
        data=data,
    )

    ev = parse_account_unified(
        account,
        EventMetadata(signature="sig", slot=1, tx_index=0, block_time_us=0, grpc_recv_us=1),
        IncludeOnlyFilter([EventType.ACCOUNT_ORCA_FEE_TIER]),
    )

    assert ev is not None
    assert ev.type == EventType.ACCOUNT_ORCA_FEE_TIER
    assert ev.data["fee_tier"]["whirlpools_config"] == _pk58(9)
    assert ev.data["fee_tier"]["tick_spacing"] == 128
    assert ev.data["fee_tier"]["default_fee_rate"] == 500


def test_rpc_parser_merges_outer_and_inner_pumpfun_instructions():
    tx = rpc_parser.RpcTransactionResponse(
        slot=7,
        block_time=None,
        meta=rpc_parser.RpcTransactionMeta(
            fee=0,
            pre_balances=[],
            post_balances=[],
            log_messages=[],
            inner_instructions=[
                rpc_parser.RpcInnerInstructionGroup(
                    index=0,
                    instructions=[
                        rpc_parser.RpcCompiledInstruction(
                            program_id_index=0,
                            accounts=bytes(range(18)),
                            data=(
                                PUMPFUN_TRADE_DISC
                                + EVENT_CPI_SUFFIX
                                + _pumpfun_trade_payload("buy")
                            ),
                        )
                    ],
                )
            ],
            pre_token_balances=[],
            post_token_balances=[],
            loaded_addresses=None,
            compute_units_consumed=None,
        ),
        transaction=rpc_parser.RpcTransaction(
            signatures=["sig"],
            message=rpc_parser.RpcMessage(
                account_keys=[PUMPFUN_PROGRAM_ID] + [_pk_str(i) for i in range(1, 19)],
                header=None,
                recent_blockhash="11111111111111111111111111111111",
                instructions=[
                    rpc_parser.RpcCompiledInstruction(
                        program_id_index=0,
                        accounts=bytes(range(18)),
                        data=bytes([102, 6, 61, 18, 1, 218, 235, 234])
                        + struct.pack("<QQB", 123, 456, 0),
                    )
                ],
                address_table_lookups=[],
            ),
        ),
        transaction_index=42,
    )

    events, err = rpc_parser.parse_rpc_transaction(tx, "sig", None, 99)

    assert err is None
    assert len(events) == 1
    assert events[0].type == EventType.PUMP_FUN_BUY
    trade = events[0].data
    assert trade.sol_amount == 10
    assert trade.token_amount == 20
    assert trade.amount == 123
    assert trade.max_sol_cost == 456
    assert trade.bonding_curve == _pk_str(3)
    assert trade.metadata.tx_index == 42
    assert trade.metadata.recent_blockhash == "11111111111111111111111111111111"


def test_rpc_parser_marks_pumpfun_log_trade_created_buy_from_whole_transaction():
    tx = rpc_parser.RpcTransactionResponse(
        slot=7,
        block_time=None,
        meta=rpc_parser.RpcTransactionMeta(
            fee=0,
            pre_balances=[],
            post_balances=[],
            log_messages=[
                f"Program {PUMPFUN_PROGRAM_ID} invoke [1]",
                _pumpfun_trade_log("buy"),
                "Program data: G3KpTd7rY3Y",
                f"Program {PUMPFUN_PROGRAM_ID} success",
            ],
            inner_instructions=[],
            pre_token_balances=[],
            post_token_balances=[],
            loaded_addresses=None,
            compute_units_consumed=None,
        ),
        transaction=rpc_parser.RpcTransaction(
            signatures=["sig"],
            message=rpc_parser.RpcMessage(
                account_keys=[],
                header=None,
                recent_blockhash="",
                instructions=[],
                address_table_lookups=[],
            ),
        ),
        transaction_index=7,
    )

    events, err = rpc_parser.parse_rpc_transaction(tx, "sig", None, 99)

    assert err is None
    assert len(events) == 1
    assert events[0].type == EventType.PUMP_FUN_BUY
    assert events[0].data.is_created_buy is True


def test_meteora_damm_initialize_pool_account_filler_matches_rust_indexes():
    from sol_parser.account_fillers.meteora import fill_damm_v2_initialize_pool_accounts
    from sol_parser.event_types import MeteoraDammV2InitializePoolEvent

    ev = MeteoraDammV2InitializePoolEvent()
    fill_damm_v2_initialize_pool_accounts(ev, lambda i: f"account_{i}")

    assert ev.creator == "account_0"
    assert ev.position_nft_mint == "account_1"
    assert ev.pool == "account_6"
    assert ev.position == "account_7"
    assert ev.token_a_mint == "account_8"
    assert ev.token_b_mint == "account_9"
