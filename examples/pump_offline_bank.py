"""Native solders LiteSVM execution; python examples/pump_offline_bank.py [config.json]."""
from pathlib import Path
import base64
import gzip
import hashlib
import json
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import base58
from solders.pubkey import Pubkey
from solders.keypair import Keypair
from solders.account import Account
from solders.clock import Clock
from solders.litesvm import LiteSVM
from solders.instruction import Instruction, AccountMeta
from solders.message import MessageV0
from solders.transaction import VersionedTransaction
from solders.address_lookup_table_account import AddressLookupTableAccount
from solders.compute_budget import set_compute_unit_limit
from solders.transaction_metadata import SimulatedTransactionInfo
from sol_parser.shredstream_client import parse_shred_transaction, parse_shred_transaction_with_loaded_addresses
from sol_parser.parser import parse_log
from sol_parser.wire_transaction import decode_wire_transaction
from sol_parser.rpc_parser import rpc_get_transaction_result_dict_to_response, parse_rpc_transaction

ROOT = Path(__file__).parent / 'offline_bank'
P = Pubkey.from_string
AMM = P('pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA')
PUMP = P('6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P')
ATA = P('ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL')
TOKENS = {P('TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA'), P('TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb')}
WALLET = Keypair.from_seed(bytes([117])*32)

def ata(user, owner, mint):
    return Pubkey.find_program_address([bytes(user),bytes(owner),bytes(mint)],ATA)[0]

def initialize(bundle, case, alt):
    msg=case['raw']['transaction']['message'];keys=list(map(P,msg['accountKeys']))
    original=next(i for i in msg['instructions'] if keys[i['programIdIndex']]==AMM)
    old=keys[original['accounts'][0]];mapping={old:WALLET.pubkey()}
    for program in (AMM,PUMP):
        mapping[Pubkey.find_program_address([b'user_volume_accumulator',bytes(old)],program)[0]]=Pubkey.find_program_address([b'user_volume_accumulator',bytes(WALLET.pubkey())],program)[0]
    for address,a in case['accounts'].items():
        data=base64.b64decode(a['data'][0]);owner=P(a['owner'])
        if owner in TOKENS and len(data)>=165 and data[32:64]==bytes(old):
            mint=Pubkey.from_bytes(data[:32])
            if ata(old,owner,mint)==P(address):mapping[P(address)]=ata(WALLET.pubkey(),owner,mint)
    bank=LiteSVM().with_sigverify(True).with_blockhash_check(True).with_log_bytes_limit(None)
    bank.set_clock(Clock(*bundle['clock']))
    for program,code in bundle['programs'].items():bank.add_program(P(program),base64.b64decode(code))
    tracked=set()
    for address,a in case['accounts'].items():
        source=base64.b64decode(a['data'][0]);data=bytearray(source)
        for before,after in mapping.items():
            for offset in range(max(0,len(source)-31)):
                if source[offset:offset+32]==bytes(before):data[offset:offset+32]=bytes(after)
        key=mapping.get(P(address),P(address));tracked.add(key)
        bank.set_account(key,Account(a['lamports'],bytes(data),P(a['owner']),a['executable'],a['rentEpoch']))
    bank.airdrop(WALLET.pubkey(),500_000_000_000)
    h=msg['header'];ns=h['numRequiredSignatures'];rs=h['numReadonlySignedAccounts'];ru=h['numReadonlyUnsignedAccounts']
    metas=[AccountMeta(mapping.get(k,k),i<ns,i<ns-rs if i<ns else i<len(keys)-ru) for i,k in enumerate(keys)]
    ix=Instruction(AMM,base58.b58decode(original['data']),[metas[i] for i in original['accounts']])
    tracked.update(a.pubkey for a in ix.accounts);tracked.add(WALLET.pubkey())
    tables=[]
    if alt:
        addresses=list(dict.fromkeys(a.pubkey for a in ix.accounts if not a.is_signer));key=Pubkey.from_bytes(bytes([118])*32)
        data=bytes([1,0,0,0])+bytes([255])*8+bytes(44)+b''.join(bytes(a) for a in addresses)
        bank.set_account(key,Account(bank.minimum_balance_for_rent_exemption(len(data)),data,P('AddressLookupTab1e1111111111111111111111111')))
        tables=[AddressLookupTableAccount(key,addresses)];tracked.add(key)
    return bank,ix,tables,tracked

def execute(bundle,case,alt,reject,oracle):
    bank,ix,tables,tracked=initialize(bundle,case,alt)
    if reject:ix=Instruction(ix.program_id,ix.data[:16]+bytes([255])*8,ix.accounts)
    msg=MessageV0.try_compile(WALLET.pubkey(),[set_compute_unit_limit(1_400_000),ix],tables,bank.latest_blockhash())
    tx=VersionedTransaction(msg,[WALLET]);tx.verify_and_hash_message();tracked.update(msg.account_keys)
    state=lambda:{k:bank.get_account(k) for k in tracked}
    before=state();sim=bank.simulate_transaction(tx)
    assert isinstance(sim,SimulatedTransactionInfo)==(not reject), (case['name'],sim)
    assert state()==before,'simulation changed bank'
    meta=sim.meta();committed=bank.send_transaction(tx);after=state()
    assert hasattr(committed,'err')==reject
    if reject:
        assert json.loads(sim.to_json())['err']=={'InstructionError':[1,{'Custom':6004}]}
        assert all(after[k]==v for k,v in before.items() if k!=WALLET.pubkey()),'parent rollback leaked writes'
        assert before[WALLET.pubkey()].lamports-after[WALLET.pubkey()].lamports==5000
    else:
        assert any(after[k]!=v for k,v in before.items() if k!=WALLET.pubkey())
        assert all(after[k]==a for k,a in sim.post_accounts() if k in tracked)
    loaded=lambda side:[str(tables[0].addresses[i]) for lookup in msg.address_table_lookups for i in getattr(lookup,side)]
    w,r=loaded('writable_indexes'),loaded('readonly_indexes')
    events=parse_shred_transaction_with_loaded_addresses(bytes(tx),w,r,slot=bundle['clock'][0])
    assert len(events)==1;intent=events[0].data
    assert intent.kind=='MultiHopSwap' and len(intent.hops)==2 and intent.instruction_index==1
    assert intent.user==str(WALLET.pubkey()) and intent.input_account==str(ix.accounts[1].pubkey) and intent.output_account==str(ix.accounts[2].pubkey)
    assert intent.amount_in==int.from_bytes(ix.data[8:16],'little') and intent.min_amount_out==int.from_bytes(ix.data[16:24],'little')
    assert len(parse_shred_transaction(bytes(tx)))==(0 if alt else 1)
    fills=[]
    for line in meta.logs():
        e=parse_log(line,str(tx.signatures[0]),0,0,None,0,False)
        if e is not None and e.type.value in ('PumpFunTrade','PumpSwapBuy','PumpSwapSell'):fills.append(e)
    assert len(fills)==len(oracle)
    for event,want in zip(fills,oracle):
        assert event.type.value==want['type']
        body=event.data if isinstance(event.data,dict) else vars(event.data)
        for field,value in want.items():
            if field!='type':assert str(body[field])==(str(WALLET.pubkey()) if field=='user' else value),(case['name'],field,body[field],value)
    # Feed execution status and logs to the offline status-aware decoder; no RPC call.
    decoded,_=decode_wire_transaction(bytes(tx))
    response=rpc_get_transaction_result_dict_to_response({
        'slot':bundle['clock'][0], 'transaction':decoded,
        'meta':{'err':{'InstructionError':[1,{'Custom':6004}]} if reject else None,
                'logMessages':meta.logs(),'loadedAddresses':{'writable':w,'readonly':r},
                'fee':5000,'preBalances':[],'postBalances':[],'innerInstructions':[],
                'preTokenBalances':[],'postTokenBalances':[]}})
    settled,error=parse_rpc_transaction(response,str(tx.signatures[0]),None,0)
    assert error is None
    assert sum(e.type.value in ('PumpFunTrade','PumpSwapBuy','PumpSwapSell') for e in settled)==(0 if reject else 2)
    # Corrupting only the signature must be rejected before program execution.
    bad=bytearray(bytes(tx));bad[1]^=1
    failed=bank.simulate_transaction(VersionedTransaction.from_bytes(bytes(bad)))
    assert json.loads(failed.to_json())['err']=='SignatureFailure' and not failed.meta().logs()
    if alt:
        from solders.message import MessageAddressTableLookup
        for side in ('writable_indexes','readonly_indexes'):
            lookup=msg.address_table_lookups[0];w0=bytes(lookup.writable_indexes);r0=bytes(lookup.readonly_indexes)
            if side=='writable_indexes':w0=bytes([255])+w0[1:]
            else:r0=bytes([255])+r0[1:]
            invalid=MessageV0(msg.header,msg.account_keys,msg.recent_blockhash,msg.instructions,[MessageAddressTableLookup(lookup.account_key,w0,r0)])
            failed=bank.simulate_transaction(VersionedTransaction(invalid,[WALLET]))
            assert json.loads(failed.to_json())['err']=='InvalidAddressLookupTableIndex' and not failed.meta().logs()
    assert state()==after
    return (case['name'],alt,reject,bytes(tx),meta.logs(),[(str(k),None if a is None else a.to_json()) for k,a in sorted(after.items(),key=lambda x:str(x[0]))])

def run_bank(config_path=None):
    config=json.loads(Path(config_path or ROOT/'config.json').read_text());payload=(ROOT/config['snapshot']).read_bytes()
    assert hashlib.sha256(payload).hexdigest()==config['sha256']
    bundle=json.loads(gzip.decompress(payload));assert bundle['schema']==1
    oracle=json.loads((ROOT/'expected.json').read_text());assert config['repetitions']>=2
    baseline=None
    for repetition in range(config['repetitions']):
        trace=[execute(bundle,c,alt,reject,oracle[c['name']]) for c in bundle['cases'] for alt in (False,True) for reject in (False,True)]
        assert len(trace)==20 and (baseline is None or baseline==trace)
        baseline=trace
        print(f'Offline bank pass {repetition+1}: 20 freshly signed routes + native SDK parsing passed')
    return len(trace)

if __name__=='__main__':run_bank(sys.argv[1] if len(sys.argv)>1 else None)
