"""Nonzero and repeat fee claims, delegate owner identity, large integers and rollback."""
import json
from pathlib import Path
import pytest
from sol_parser.rpc_parser import parse_rpc_transaction,rpc_get_transaction_result_dict_to_response
CASES=json.loads((Path(__file__).parent/'fixtures/dbc_v1_migration_20261008.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_dbc_v1_migration_bank(case):
 events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(case['raw']),'simulation',None,0)
 assert error is None
 if case['raw']['meta']['err'] is not None:
  assert not events
  return
 lp=[e for e in events if e.type.value in ('MeteoraPoolsPoolCreated',)]
 assert len(lp)==len(case['expected'])
 for event,want in zip(lp,case['expected']):
  assert event.type.value==want['type']
  for key,value in want.items():
   if key!='type':assert str(getattr(event.data,key))==value


def test_actual_config2_instruction_without_logs_and_malformed_option():
 import base58
 from sol_parser.instructions import parse_meteora_pools_instruction
 f=json.loads((Path(__file__).parent/'fixtures/damm_v1_config2_instruction_20261008.json').read_text())
 data=base58.b58decode(f['data'])
 invoke=lambda d:parse_meteora_pools_instruction(d,f['accounts'],'simulation',0,0,None,0)
 e=invoke(data)
 assert e is not None
 for key,value in f['expected'].items():
  if key!='type':assert str(getattr(e.data,key))==value
 assert invoke(data[:24])is None
 bad=bytearray(data);bad[24]=2;assert invoke(bytes(bad))is None
 bad[24]=1;assert invoke(bytes(bad[:32]))is None
 obsolete=bytes([95,180,10,172,84,174,232,40])+bytes(49);assert invoke(obsolete)is None
