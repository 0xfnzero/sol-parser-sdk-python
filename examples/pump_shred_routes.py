"""python examples/pump_shred_routes.py — six signed wires; no RPC or bank claims."""
from pathlib import Path
import base64
import json
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import base58
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sol_parser.shredstream_client import parse_shred_transaction,parse_shred_transaction_with_loaded_addresses
from sol_parser.wire_transaction import decode_wire_transaction
from sol_parser import RawInstructionDexType
from sol_parser.grpc_types import EventType,IncludeOnlyFilter,ExcludeFilter,EventMetadata
from sol_parser.pump_routes import AMM,parse_route


def run_replay():
    fixtures=json.loads((Path(__file__).parent/'fixtures/pump_shred_routes.json').read_text())
    baseline=None
    for _ in range(2):
        trace=[]
        for f in fixtures:
            raw=base64.b64decode(f['wire']);tx,_=decode_wire_transaction(raw);m=tx['message']
            count=len(tx['signatures'])
            signed=raw[:-64*count] if tx['version']==1 else raw[1+64*count:]
            for key,signature in zip(m['accountKeys'],tx['signatures']):
                Ed25519PublicKey.from_public_bytes(base58.b58decode(key)).verify(base58.b58decode(signature),signed)
            assert tx['signatures'][0]==f['signature']
            w,r=f['loaded_writable'],f['loaded_readonly']
            def parse(filter=None):
                return parse_shred_transaction_with_loaded_addresses(raw,w,r,slot=f['slot'],tx_index=888,recv_us=999,filter=filter)
            if f['expected'][0]['kind'] in ('RapidBuy', 'BuyPumpDelta'):
                events = parse()
                keys = [*m['accountKeys'], *w, *r]
                assert len(events) == len(f['expected'])
                for event in events:
                    assert event.type == EventType.RAW_INSTRUCTION
                    e = event.data
                    ix = m['instructions'][e.instruction_index]
                    assert e.program_id == keys[ix['programIdIndex']]
                    assert e.accounts == [keys[i] for i in ix['accounts']]
                    assert e.account_indices == ix['accounts']
                    assert e.instruction_data == list(base58.b58decode(ix['data']))
                    assert not hasattr(e, 'is_buy') and not hasattr(e, 'ix_name')
                selected = parse(IncludeOnlyFilter([EventType.PUMP_FUN_TRADE]))
                assert selected
                assert all(e.type == EventType.RAW_INSTRUCTION and any(d.dex_type == RawInstructionDexType.PUMPFUN for d in e.data.dexes) for e in selected)
                assert not parse(ExcludeFilter([EventType.RAW_INSTRUCTION]))
                trace.append((f['signature'], [e.type for e in events]))
                continue
            events=parse(IncludeOnlyFilter([EventType.PUMP_FUN_TRADE,EventType.PUMP_FUN_CREATE]))
            assert len(events)==len(f['expected'])
            assert len(parse_shred_transaction(raw))==(0 if w or r else len(events))
            keys=[*m['accountKeys'],*w,*r]
            for event,want in zip(events,f['expected']):
                e=event.data
                from sol_parser.json_util import dex_event_json_dumps
                from sol_parser.event_types import to_typed_event
                encoded=json.loads(dex_event_json_dumps(event))
                assert encoded['data']['instruction_data']==e.instruction_data
                assert to_typed_event({encoded['type']:encoded['data']})==e
                assert e.is_buy is (True if e.kind in ('RapidBuy','BuyPumpDelta') else None)
                assert e.ix_name == ('buy_exact_quote_in_v2' if e.kind == 'RapidBuy' else None)
                legacy = dict(encoded['data'])
                legacy.pop('is_buy'); legacy.pop('ix_name')
                old = to_typed_event({encoded['type']:legacy})
                assert old.is_buy is None and old.ix_name is None
                assert e.kind==want['kind'] and e.user==want['user']
                assert e.input_account==want['input'] and e.output_account==want['output']
                assert e.amount_in==want['amount_in'] and e.min_amount_out==want['min_amount_out']
                assert e.instruction_index==want['instruction_index']
                assert [list(vars(h).values()) for h in e.hops]==want['hops']
                assert e.metadata.signature==f['signature'] and e.metadata.tx_index==888 and e.metadata.grpc_recv_us==999
                assert e.metadata.recent_blockhash==m['recentBlockhash']
                ix=m['instructions'][e.instruction_index];a=[keys[i] for i in ix['accounts']];data=base58.b58decode(ix['data'])
                for bad in (data[:3],data+bytes([1])):
                    assert parse_route(e.program,bad,a,EventMetadata(),0) is None
                assert parse_route('11111111111111111111111111111111',data,a,EventMetadata(),0) is None
                assert parse_route(e.program,data,a[:-1],EventMetadata(),0) is None
                if e.kind=='BuyPumpDelta':assert e.amount_in is None
            assert len(parse(IncludeOnlyFilter([EventType.PUMP_ROUTE_INTENT])))==len(events)
            assert not parse(ExcludeFilter([EventType.PUMP_ROUTE_INTENT]))
            assert not parse(IncludeOnlyFilter([EventType.PUMP_FUN_BUY]))
            assert not parse(IncludeOnlyFilter([EventType.PUMP_FUN_CREATE]))
            if events[0].data.program==AMM:assert len(parse(IncludeOnlyFilter([EventType.PUMP_SWAP_TRADE])))==len(events)
            try:parse_shred_transaction_with_loaded_addresses(raw,w+['11111111111111111111111111111111'],r)
            except ValueError:pass
            else:raise AssertionError('bad ALT count accepted')
            calls=[]
            def resolve(decoded,slot):calls.append(slot);assert decoded==tx;return w,r
            assert len(parse_shred_transaction(raw,slot=f['slot'],address_lookup_resolver=resolve))==len(events)
            if w or r:
                assert calls==[f['slot']]
                assert not parse_shred_transaction(raw,address_lookup_resolver=lambda *_:None)
            trace.append((f['signature'],[e.data.kind for e in events]))
        assert baseline is None or baseline==trace
        baseline=trace
    check_boundaries(fixtures)
    return len(fixtures)

def check_boundaries(fixtures):
    from solders.pubkey import Pubkey
    from solders.keypair import Keypair
    from solders.instruction import Instruction, AccountMeta
    from solders.message import MessageV0
    from solders.hash import Hash
    from solders.transaction import VersionedTransaction
    f=json.loads((Path(__file__).parent/'fixtures/pump_curve_instruction.json').read_text())
    wallet=Keypair.from_seed(bytes([117])*32)
    a=list(f['accounts']);a[3]=str(wallet.pubkey())
    data=bytes(f['data'])
    for amount in (1,2**64-1):
        wire_data=data[:8]+amount.to_bytes(8,'little')+data[16:]
        ix=Instruction(Pubkey.from_string(f['program']),wire_data,[AccountMeta(Pubkey.from_string(k),i==3,True) for i,k in enumerate(a)])
        tx=VersionedTransaction(MessageV0.try_compile(wallet.pubkey(),[ix],[],Hash.default()),[wallet]);tx.verify_and_hash_message()
        events=parse_shred_transaction(bytes(tx),filter=IncludeOnlyFilter([EventType.PUMP_FUN_TRADE]))
        assert len(events)==1 and events[0].data.kind=='MultiHopCurveSwap' and events[0].data.amount_in==amount
        assert events[0].data.is_buy is None and events[0].data.ix_name is None
    assert parse_route(f['program'],data[:8]+bytes(8)+data[16:],a,EventMetadata(),0) is None
    first=next(f for f in fixtures if f['expected'][0]['kind']=='MultiHopSwap');tx,_=decode_wire_transaction(base64.b64decode(first['wire']));keys=[*tx['message']['accountKeys'],*first['loaded_writable'],*first['loaded_readonly']]
    ix=tx['message']['instructions'][first['expected'][0]['instruction_index']];a=[keys[i] for i in ix['accounts']];data=base58.b58decode(ix['data'])
    assert parse_route(AMM,data[:16]+bytes(8),a,EventMetadata(),0).data.min_amount_out==0
    assert parse_route(AMM,data[:8]+bytes(8)+data[16:],a,EventMetadata(),0) is None
    bad=list(a);bad[7]='11111111111111111111111111111111'
    assert parse_route(AMM,data,bad,EventMetadata(),0) is None

if __name__=='__main__':
    print(f'{run_replay()} signed ShredStream transactions verified twice; offline replay, zero RPC.')
