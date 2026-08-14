import base64
import struct

from sol_parser.dex_parsers import RAYDIUM_AMM_V4_PROGRAM_ID, RAYDIUM_CPMM_PROGRAM_ID
from sol_parser.grpc_types import EventType
from sol_parser.parser import parse_log_optimized_with_program_id


def _program_data(discriminator: bytes, payload: bytes) -> str:
    return "Program data: " + base64.b64encode(discriminator + payload).decode()


def test_current_cpmm_swap_event_layout() -> None:
    pool = bytes(range(32))
    payload = pool + struct.pack("<QQQQQQ?", 10, 20, 30, 40, 1, 2, True)
    event = parse_log_optimized_with_program_id(
        _program_data(bytes([64, 198, 205, 232, 38, 8, 113, 226]), payload),
        "sig", 1, program_id=RAYDIUM_CPMM_PROGRAM_ID,
    )
    assert event is not None
    assert event.type == EventType.RAYDIUM_CPMM_SWAP
    assert event.data.input_vault_before == 10
    assert event.data.output_vault_before == 20
    assert event.data.input_amount == 30
    assert event.data.output_amount == 40
    assert event.data.input_transfer_fee == 1
    assert event.data.output_transfer_fee == 2
    assert event.data.base_input is True


def test_amm_v4_ray_log_swap_base_in() -> None:
    ray_log = bytes([3]) + struct.pack("<QQQQQQQ", 100, 5, 2, 90, 1000, 2000, 88)
    event = parse_log_optimized_with_program_id(
        "Program log: ray_log: " + base64.b64encode(ray_log).decode(),
        "sig", 1, program_id=RAYDIUM_AMM_V4_PROGRAM_ID,
    )
    assert event is not None
    assert event.type == EventType.RAYDIUM_AMM_V4_SWAP
    assert event.data.amount_in == 100
    assert event.data.minimum_amount_out == 5
    assert event.data.amount_out == 88
