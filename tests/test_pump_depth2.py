"""Signed depth-2 bank execution replay, including ALT-loaded accounts."""
import json
from pathlib import Path
import pytest
from sol_parser.rpc_parser import parse_rpc_transaction,rpc_get_transaction_result_dict_to_response
CASES=json.loads((Path(__file__).parent/'fixtures/pump_depth2_20261014.json').read_text())['cases']
@pytest.mark.parametrize('c',CASES,ids=lambda c:c['name'])
def test_pump_depth2_signed_bank_replay(c):
    events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(c['raw']),c['raw']['transaction']['signatures'][0],None,0)
    assert error is None
    creates=[e for e in events if e.type.value=='PumpFunCreate']
    assert len(creates)==1
    for k,v in c['expected'].items():assert str(getattr(creates[0].data,k))==str(v)
    rolled_back={**c['raw'],'meta':{**c['raw']['meta'],'err':{'InstructionError':[1,{'Custom':6109}]}}}
    events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(rolled_back),'failed',None,0)
    assert not events
