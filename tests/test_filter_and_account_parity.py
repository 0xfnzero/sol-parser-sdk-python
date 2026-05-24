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
)
from sol_parser.dex_parsers import PUMP_FEES_UPDATE_ADMIN
from sol_parser.grpc_types import (
    EventMetadata,
    EventType,
    ExcludeFilter,
    IncludeOnlyFilter,
    event_type_filter_includes_pump_fees,
)
from sol_parser.parser import parse_log_optimized


def _pump_fees_update_admin_log() -> str:
    buf = struct.pack("<Q", PUMP_FEES_UPDATE_ADMIN) + bytes(8 + 32 + 32)
    return "Program data: " + base64.b64encode(buf).decode("ascii")


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


def test_protocol_helper_exclude_matches_rust_semantics():
    assert not event_type_filter_includes_pump_fees(
        ExcludeFilter([EventType.PUMP_FEES_UPDATE_ADMIN])
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


def test_pumpfun_account_parsers_are_exported() -> None:
    import sol_parser.accounts as accounts

    for name in (
        "parse_pumpfun_bonding_curve",
        "parse_pumpfun_fee_config",
        "parse_pumpfun_sharing_config",
        "parse_pumpfun_global_volume_accumulator",
        "parse_pumpfun_user_volume_accumulator",
        "PUMP_FEES_PROGRAM_ID",
    ):
        assert name in accounts.__all__


def _u64(value: int) -> bytes:
    return value.to_bytes(8, "little")


def _pk(seed: int) -> bytes:
    return bytes([seed]) * 32


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
