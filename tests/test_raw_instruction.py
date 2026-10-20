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
        events = parse_shred_transaction_with_loaded_addresses(wire,f['loaded_writable'],f['loaded_readonly'],tx_index=71,recv_us=123456,filter=IncludeOnlyFilter([EventType.RAW_INSTRUCTION]))
        assert len(events) == len(msg['instructions'])
        for event, ix in zip(events, msg['instructions']):
            e=event.data
            assert e.metadata.tx_index == 71
            assert e.metadata.grpc_recv_us == 123456
            assert e.program_id == keys[ix['programIdIndex']]
            assert e.accounts == [keys[i] for i in ix['accounts']]
            assert e.account_indices == ix['accounts']
            assert e.instruction_data == list(base58.b58decode(ix['data']))
            encoded=json.loads(dex_event_json_dumps(event))
            assert to_typed_event({encoded['type']:encoded['data']}) == e
            assert not hasattr(e,'ix_name') and not hasattr(e,'is_buy')
        defaults = parse_shred_transaction_with_loaded_addresses(wire, f['loaded_writable'], f['loaded_readonly'])
        assert all(e.type != EventType.RAW_INSTRUCTION for e in defaults)
        for event in defaults:
            if event.type == EventType.PUMP_FUN_TRADE and event.data.third_program:
                assert event.data.parse_status == "Unresolved"
                assert event.data.sol_amount == 0
                raw = event.data.third_program
                assert raw.instruction_data == list(base58.b58decode(msg['instructions'][raw.instruction_index]['data']))

def test_unknown_program_changed_data_and_missing_alt_stay_raw():
    tx,_=decode_wire_transaction(base64.b64decode(FIXTURES[0]['wire']))
    msg=tx['message']; ix=msg['instructions'][1]
    indices=[ix['accounts'][2],ix['accounts'][1],ix['accounts'][2],250]
    msg['instructions']=[dict(programIdIndex=0,accounts=indices,data=bytes([255,0,1]))]
    events=_parse_decoded_shred(tx,msg['accountKeys'],None,0,0,0,IncludeOnlyFilter([EventType.RAW_INSTRUCTION]))
    assert len(events)==1
    assert events[0].data.accounts == [msg['accountKeys'][i] if i<250 else None for i in indices]
    assert events[0].data.instruction_data==[255,0,1]

def test_raw_subscriptions_use_instruction_local_program_references():
    tx, _ = decode_wire_transaction(base64.b64decode(FIXTURES[0]['wire']))
    msg = tx['message']
    msg['accountKeys'] = [msg['accountKeys'][0], '6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P', 'CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C']
    msg['instructions'] = [dict(programIdIndex=0, accounts=accounts, data=b'\xff')
                           for accounts in ([1, 1], [2], [], [1, 2, 250], [250])]
    for kind, expected in [('PumpFunTrade', [0, 3]), ('RaydiumCpmmSwap', []), ('PumpFunBuy', []), ('RawInstruction', [0, 1, 2, 3, 4])]:
        events = _parse_decoded_shred(tx, msg['accountKeys'], None, 0, 0, 0, IncludeOnlyFilter([EventType(kind)]))
        assert [(e.data.third_program if e.type == EventType.PUMP_FUN_TRADE else e.data).instruction_index for e in events] == expected
    events = _parse_decoded_shred(tx, msg['accountKeys'], None, 0, 0, 0, None)
    assert len(events) == 2
    assert events[1].data.third_program.accounts[-1] is None
    filter = IncludeOnlyFilter([EventType.PUMP_FUN_TRADE])
    filter.exclude_types = [EventType.RAW_INSTRUCTION]
    assert len(_parse_decoded_shred(tx, msg['accountKeys'], None, 0, 0, 0, filter)) == 2

def test_dex_enum_exports_and_json_round_trip():
    import pytest
    from sol_parser import RawInstructionDexType, RawInstructionDex
    expected = ["pumpfun","pumpswap","raydium_launchlab","raydium_cpmm","raydium_clmm","raydium_amm_v4","orca_whirlpool","meteora_pools","meteora_damm_v2","meteora_dlmm","meteora_dbc"]
    assert [kind.value for kind in RawInstructionDexType] == expected
    for kind in RawInstructionDexType:
        assert json.dumps(kind) == json.dumps(kind.value)
        restored = RawInstructionDex(**json.loads(json.dumps(dict(dex_type=kind, program_id="program"))))
        assert restored.dex_type is kind
    with pytest.raises(ValueError):
        RawInstructionDex(dex_type="typo", program_id="program")
    tx, _ = decode_wire_transaction(base64.b64decode(FIXTURES[0]['wire']))
    events = _parse_decoded_shred(tx, tx['message']['accountKeys'], None, 0, 0, 0, IncludeOnlyFilter([EventType.RAW_INSTRUCTION]))
    assert any(e.data.dexes for e in events)
    assert all(isinstance(d.dex_type, RawInstructionDexType) for e in events for d in e.data.dexes)
