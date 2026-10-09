import base64
import struct
from unittest.mock import patch
import pytest
from sol_parser import parser
from sol_parser.dex_parsers import PUMP_FEES_UPDATE_ADMIN
from sol_parser.accounts import PUMP_FEES_PROGRAM_ID
from sol_parser.grpc_types import IncludeOnlyFilter, EventType

ENCODED = base64.b64encode(struct.pack('<Q', PUMP_FEES_UPDATE_ADMIN) + bytes(72)).decode()
INCLUDED = IncludeOnlyFilter([EventType.PUMP_FEES_UPDATE_ADMIN])
EXCLUDED = IncludeOnlyFilter([EventType.RAYDIUM_CPMM_SWAP])

def parse(encoded, filt=INCLUDED):
    return parser.parse_log_optimized('Program data: ' + encoded, 'offline', 1, 0, 0, 0, filt, False, '', PUMP_FEES_PROGRAM_ID)

def test_excluded_events_do_not_decode_whole_payload():
    with patch.object(parser, 'decode_program_data_line', side_effect=AssertionError('full decode')):
        for size in (512, 4096):
            encoded = base64.b64encode(struct.pack('<Q', PUMP_FEES_UPDATE_ADMIN) + bytes(size - 8)).decode()
            assert parse(encoded, EXCLUDED) is None

@pytest.mark.parametrize('encoded', [ENCODED, ' ' + ENCODED + ' ', ENCODED[:4]+'\n'+ENCODED[4:], ENCODED[:4]+'!'+ENCODED[4:], ENCODED[:-1], ENCODED+'!', 'AA=='])
def test_included_encoding_semantics(encoded):
    decoded = parser.decode_program_data_line('Program data: '+encoded)
    expected = parse(base64.b64encode(decoded).decode()) if decoded else None
    assert parse(encoded) == expected
