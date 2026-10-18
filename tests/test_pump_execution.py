"""Captured 2026-10-19 executions and five multi-hop regression combinations."""
import copy
import json
from pathlib import Path
import base58
import pytest
from sol_parser.rpc_parser import parse_rpc_transaction, rpc_get_transaction_result_dict_to_response
from sol_parser.event_types import PumpFunTradeEvent

ROOT = Path(__file__).parent / 'fixtures'
CASES = sum((json.loads((ROOT / name).read_text())['cases'] for name in
             ['pump_execution_20261019.json', 'pump_routes_20261009.json']), [])
FIELDS = ('mint', 'user', 'pool', 'is_buy', 'token_amount', 'sol_amount', 'quote_amount',
          'base_amount_in', 'base_amount_out', 'quote_amount_in', 'quote_amount_out')

def parse(raw):
    events, error = parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(raw), 'replay', None, 0)
    assert error is None
    return events

def trades(events):
    return [tuple(getattr(e.data, key, None) for key in FIELDS) for e in events
            if isinstance(e.data, PumpFunTradeEvent) or e.type.value in ('PumpSwapBuy', 'PumpSwapSell')]

@pytest.mark.parametrize('case', CASES, ids=lambda c: c['name'])
def test_execution_without_logs(case):
    raw = copy.deepcopy(case['raw'])
    expected = trades(parse(raw))
    assert expected
    for logs in (raw['meta']['logMessages'][:len(raw['meta']['logMessages'])//2], []):
        raw['meta']['logMessages'] = logs
        assert trades(parse(raw)) == expected
        from sol_parser.rpc_parser import rpc_response_to_solana_storage
        from sol_parser.grpc_instruction_parser import parse_instructions_enhanced_from_parsed
        response = rpc_get_transaction_result_dict_to_response(raw)
        tx, meta = rpc_response_to_solana_storage(response)
        grpc_events = parse_instructions_enhanced_from_parsed(tx.message, meta, 'replay', raw['slot'], 0, None, 0, None, tx)
        assert trades(grpc_events) == expected
    for group in raw['meta']['innerInstructions']:
        group['instructions'] = [ix for ix in group['instructions'] if not
            base58.b58decode(ix['data']).startswith(bytes([228,69,165,46,81,203,154,29]))]
    for event in parse(raw):
        if isinstance(event.data, PumpFunTradeEvent):
            assert (event.data.sol_amount, event.data.token_amount, event.data.quote_amount) == (0,0,0)
    raw['meta']['err'] = {'InstructionError': [0, 'InvalidArgument']}
    assert parse(raw) == []
