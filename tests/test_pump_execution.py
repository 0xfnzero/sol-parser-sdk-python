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
             ['pump_execution_20261019.json', 'pump_routes_20261009.json', 'wrapped_pumpfun_reported.json', 'pump_create_alt_20261026.json', 'pump_multi_hop_20261025.json']), [])
FIELDS = ('mint', 'user', 'pool', 'is_buy', 'is_created_buy', 'ix_name', 'token_amount', 'sol_amount', 'quote_amount',
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

from base64 import b64decode
from sol_parser.shredstream_client import parse_shred_transaction, parse_shred_transaction_with_loaded_addresses
from sol_parser.grpc_types import EventType, IncludeOnlyFilter
from sol_parser.trade_source import TradeParseStatus

@pytest.mark.parametrize('i,case', list(enumerate(json.loads((ROOT/'pump_create_alt_20261026.json').read_text())['cases'])))
def test_signed_alt_create_and_trade(i, case):
    rpc = case['wire_rpc']
    wire = b64decode(rpc['transaction'][0])
    filter = IncludeOnlyFilter([EventType.PUMP_FUN_CREATE, EventType.PUMP_FUN_TRADE])
    events = parse_shred_transaction(wire, slot=rpc['slot'], tx_index=888, recv_us=123456, filter=filter)
    loaded = rpc['meta']['loadedAddresses']
    full = parse_shred_transaction_with_loaded_addresses(wire, loaded['writable'], loaded['readonly'], filter=filter)
    assert [e.type for e in events] == [EventType.PUMP_FUN_CREATE_V2, EventType.PUMP_FUN_TRADE]
    assert [e.type for e in full] == [e.type for e in events]
    create, trade = (e.data for e in events)
    assert create.ix_name == 'create_v2'
    assert trade.ix_name == ['buy_exact_sol_in','buy_v2','buy_v3'][i]
    assert trade.is_created_buy and trade.mint == create.mint
    for event in events:
        assert event.data.metadata.signature == case['signature']
        assert (event.data.metadata.tx_index,event.data.metadata.grpc_recv_us) == (888,123456)
        assert event.data.metadata.recent_blockhash == case['raw']['transaction']['message']['recentBlockhash']
    for field in ('mint','name','symbol','uri','creator','user'):
        assert getattr(create,field) == getattr(full[0].data,field)
    only = parse_shred_transaction(wire, filter=IncludeOnlyFilter([EventType.PUMP_FUN_TRADE]))
    assert len(only) == 1 and only[0].data.is_created_buy
    if i > 0:
        assert trade.quote_mint == '11111111111111111111111111111111'


def test_official_multi_hop_curve_provenance_and_execution_amounts():
    case = json.loads((ROOT/'pump_multi_hop_20261025.json').read_text())['cases'][0]
    wire = b64decode(case['wire_rpc']['transaction'][0])
    events = parse_shred_transaction(wire, filter=IncludeOnlyFilter([EventType.PUMP_FUN_CREATE,EventType.PUMP_FUN_TRADE]))
    trades = [e.data for e in events if isinstance(e.data,PumpFunTradeEvent)]
    assert len(trades) == 1
    t = trades[0]
    assert t.ix_name == 'multi_hop_swap' and t.is_buy and t.is_created_buy
    assert t.mint == 'Aijxkeq5L9iaDYZxfaXUhnHQj4cYeo8um6a3t5vzpump'
    assert t.quote_mint == '6Vk3fAQWYEot6JbQb8Nx8j5wZeDnMhzk8FajjHhZpump'
    assert (t.sol_amount,t.token_amount,t.quote_amount) == (0,0,0)
    assert t.parse_status == TradeParseStatus.INSTRUCTION_DECODED
    source = t.third_program
    assert source and source.instruction_data == list(base58.b58decode(case['raw']['transaction']['message']['instructions'][source.instruction_index]['data']))
    assert parse_shred_transaction(wire, filter=IncludeOnlyFilter([EventType.PUMP_FUN_BUY])) == []
    executed = [e.data for e in parse(case['raw']) if isinstance(e.data,PumpFunTradeEvent)]
    assert len(executed) == 1 and executed[0].ix_name == 'multi_hop_swap'
    assert (executed[0].sol_amount,executed[0].token_amount,executed[0].quote_amount) == (0,255705136795915,11728308720756)


def test_multi_hop_pda_fallback_matches_native(monkeypatch):
    import sol_parser.shredstream_pump_multi_hop as multi
    from solders.pubkey import Pubkey
    mints = [str(Pubkey.from_bytes(bytes([i])*32)) for i in range(16)]
    expected = [multi._curve_address(mint) for mint in mints]
    monkeypatch.setattr(multi,'Pubkey',None)
    assert [multi._curve_address(mint) for mint in mints] == expected


def test_multi_hop_rejects_non_curve_venues_and_bad_layouts():
    from sol_parser.shredstream_client import _decode_shred
    from sol_parser.shredstream_pump_multi_hop import parse_curve_hops, MULTI_HOP_SWAP
    from sol_parser.grpc_types import EventMetadata
    case = json.loads((ROOT/'pump_multi_hop_20261025.json').read_text())['cases'][0]
    tx = _decode_shred(b64decode(case['wire_rpc']['transaction'][0]))
    msg = tx['message']
    ix = next(ix for ix in msg['instructions'] if ix['data'].startswith(MULTI_HOP_SWAP))
    data, indices, keys = ix['data'], list(ix['accounts']), msg['accountKeys']
    parse_hops = lambda accounts, payload=data: parse_curve_hops(payload, accounts, keys, 0, EventMetadata())
    assert len(parse_hops(indices)) == 1
    assert parse_hops(indices[:-1]) == []
    assert parse_hops(indices, data[:-1]) == []
    all_amm = list(indices)
    all_amm[23] = indices[0]
    assert parse_hops(all_amm) == []
    missing_vault = list(indices)
    missing_vault[24] = 255
    event = parse_hops(missing_vault)[0].data
    assert event.third_program.accounts[24] is None
