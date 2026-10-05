import json, base64
from pathlib import Path
import pytest
from sol_parser import decode_wire_transaction, analyze_rpc_transaction_routes, analyze_simulation_routes
import copy
from sol_parser.accounts import AccountData
from sol_parser.grpc_types import EventMetadata
from sol_parser.liquidity_snapshot import parse_liquidity_account

def test_closed_liquidity_candidates():
    data=bytes.fromhex('11d8f68ee1c7da38')+bytes(140)
    account=AccountData('11111111111111111111111111111111',False,1,'whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc',0,data)
    assert parse_liquidity_account(account,EventMetadata()) is not None
    account.lamports=0
    assert parse_liquidity_account(account,EventMetadata()) is None
    account.lamports=1;account.executable=True
    assert parse_liquidity_account(account,EventMetadata()) is None

PREFUNDED=json.loads((Path(__file__).parent/'fixtures/review10_prefunded_ata.json').read_text())
def test_prefunded_ata():
    r=analyze_simulation_routes(base64.b64decode(PREFUNDED['wire']),PREFUNDED['response'])
    assert r.succeeded and not r.legs and not r.transfers
def test_invalid_allocation_space():
    response=copy.deepcopy(PREFUNDED['response'])
    response['result']['value']['innerInstructions'][0]['instructions'][2]['parsed']['info']['space']=-1
    with pytest.raises(ValueError):analyze_simulation_routes(base64.b64decode(PREFUNDED['wire']),response)

COMPILED=json.loads((Path(__file__).parent/'fixtures/review10_compiled_bounds.json').read_text())
@pytest.mark.parametrize('case',COMPILED,ids=lambda c:c['name'])
def test_compiled_bounds(case):
    if case['valid']:analyze_rpc_transaction_routes(case['transaction'])
    else:
        with pytest.raises(ValueError):analyze_rpc_transaction_routes(case['transaction'])

WIRES=json.loads((Path(__file__).parent/'fixtures/review10_wire_bounds.json').read_text())
@pytest.mark.parametrize('case',WIRES,ids=lambda c:c['name'])
def test_wire_bounds(case):
    if case['valid']:decode_wire_transaction(base64.b64decode(case['wire']))
    else:
        with pytest.raises(ValueError):decode_wire_transaction(base64.b64decode(case['wire']))
