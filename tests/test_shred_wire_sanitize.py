import pytest
from solders.message import Message, MessageV0, MessageHeader, MessageAddressTableLookup
from solders.instruction import CompiledInstruction
from solders.pubkey import Pubkey
from solders.hash import Hash
from solders.signature import Signature
from solders.transaction import VersionedTransaction
from sol_parser.shredstream_client import _events_from_versioned_tx_wire, PUMPFUN_PROGRAM_ID

DATA=bytes([184,23,238,97,103,197,211,61])+(111).to_bytes(8,'little')+(222).to_bytes(8,'little')
KEYS=[Pubkey.from_bytes(bytes([i])*32) for i in range(1,4)]+[Pubkey.from_string(PUMPFUN_PROGRAM_ID)]

def wire(version,pid=3,accounts=bytes([0,1,2,3]),required=1,lookups=()):
    ix=CompiledInstruction(pid,DATA,accounts)
    if version=='legacy':
        msg=Message.new_with_compiled_instructions(required,0,0,KEYS,Hash.default(),[ix])
    else:
        msg=MessageV0(MessageHeader(required,0,0),KEYS,Hash.default(),[ix],list(lookups))
    return VersionedTransaction.populate(msg,[Signature.default()])

def parse(transaction):
    return _events_from_versioned_tx_wire(bytes(transaction),'offline',1,0,10,None)

@pytest.mark.parametrize('version',['legacy','v0'])
@pytest.mark.parametrize('options',[{'pid':99},{'accounts':bytes([0,1,2,99])},{'required':2}])
def test_structurally_invalid_wire_is_rejected_without_guessing(version,options):
    transaction=wire(version,**options)
    with pytest.raises(Exception): transaction.sanitize()
    assert parse(transaction)==[]

@pytest.mark.parametrize('version',['legacy','v0'])
def test_valid_wire_preserves_pump_instruction_parsing(version):
    transaction=wire(version);transaction.sanitize()
    events=parse(transaction)
    assert events and events[0].type.value=='PumpFunBuy'

def test_valid_v0_with_missing_alt_preserves_documented_placeholder_mapping():
    lookup=MessageAddressTableLookup(Pubkey.from_bytes(bytes([9])*32),bytes([0]),bytes())
    transaction=wire('v0',accounts=bytes([0,1,2,4]),lookups=[lookup]);transaction.sanitize()
    assert parse(transaction)
