import base64
import struct

from sol_parser.accounts import (
    AccountData,
    PUMPFUN_GLOBAL_BODY,
    PUMPFUN_PROGRAM_ID,
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
