import base64
import json
from pathlib import Path
import base58
from sol_parser.shredstream_client import parse_shred_transaction, parse_shred_transaction_with_loaded_addresses, _parse_decoded_shred
from sol_parser.wire_transaction import decode_wire_transaction
from sol_parser.grpc_types import EventType, IncludeOnlyFilter
from sol_parser.json_util import dex_event_json_dumps
from sol_parser.event_types import to_typed_event

FIXTURES = json.loads((Path(__file__).parents[1]/'examples/fixtures/raw_instructions.json').read_text())

def test_signed_raw_payloads_and_json():
    for f in FIXTURES:
        wire = base64.b64decode(f['wire'])
        tx, _ = decode_wire_transaction(wire)
        msg = tx['message']
        keys = msg['accountKeys'] + f['loaded_writable'] + f['loaded_readonly']
        events = parse_shred_transaction_with_loaded_addresses(wire,f['loaded_writable'],f['loaded_readonly'],filter=IncludeOnlyFilter([EventType.RAW_INSTRUCTION]))
        assert len(events) == len(msg['instructions'])
        for event, ix in zip(events, msg['instructions']):
            e=event.data
            assert e.program_id == keys[ix['programIdIndex']]
            assert e.accounts == [keys[i] for i in ix['accounts']]
            assert e.account_indices == ix['accounts']
            assert e.instruction_data == list(base58.b58decode(ix['data']))
            encoded=json.loads(dex_event_json_dumps(event))
            assert to_typed_event({encoded['type']:encoded['data']}) == e
            assert not hasattr(e,'ix_name') and not hasattr(e,'is_buy')
        if 'raw_instruction_count' in f:
            events = parse_shred_transaction_with_loaded_addresses(wire, f['loaded_writable'], f['loaded_readonly'])
            assert sum(e.type == EventType.RAW_INSTRUCTION for e in events) == f['raw_instruction_count']
            assert not any(e.type.value in ('PumpFunTrade','PumpFunBuy','PumpFunSell','PumpFunBuyExactSolIn') for e in events)
        if f['signature'].startswith(('3nMX','2r4u')):
            events=parse_shred_transaction(wire)
            assert len(events)==(2 if f['signature'].startswith('3nMX') else 3)
            assert all(e.type==EventType.RAW_INSTRUCTION for e in events)

def test_unknown_program_changed_data_and_missing_alt_stay_raw():
    tx,_=decode_wire_transaction(base64.b64decode(FIXTURES[0]['wire']))
    msg=tx['message']; ix=msg['instructions'][1]
    indices=[ix['accounts'][2],ix['accounts'][1],ix['accounts'][2],250]
    msg['instructions']=[dict(programIdIndex=0,accounts=indices,data=bytes([255,0,1]))]
    events=_parse_decoded_shred(tx,msg['accountKeys'],None,0,0,0,None)
    assert len(events)==1
    assert events[0].data.accounts == [msg['accountKeys'][i] if i<250 else None for i in indices]
    assert events[0].data.instruction_data==[255,0,1]
