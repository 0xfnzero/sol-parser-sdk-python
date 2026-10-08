"""Nonzero and repeat fee claims, delegate owner identity, large integers and rollback."""
import json
from pathlib import Path
import pytest
from sol_parser.rpc_parser import parse_rpc_transaction,rpc_get_transaction_result_dict_to_response
CASES=json.loads((Path(__file__).parent/'fixtures/dlmm_rewards_20261008.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_dlmm_rewards_bank(case):
 events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(case['raw']),'simulation',None,0)
 assert error is None
 if case['raw']['meta']['err'] is not None:
  assert not events
  return
 lp=[e for e in events if e.type.value in ('MeteoraDlmmClaimReward',)]
 assert len(lp)==len(case['expected'])
 for event,want in zip(lp,case['expected']):
  assert event.type.value==want['type']
  for key,value in want.items():
   if key!='type':assert str(getattr(event.data,key))==value



def test_reward2_truncation_integer_precision_and_legacy_factory():
 from sol_parser.dex_parsers import parse_dlmm_from_program_data
 from sol_parser.event_types import legacy_dict_to_dex_event
 body=bytes([27,143,244,33,80,43,110,146])+bytes(range(96))+(2**64-1).to_bytes(8,'little')+(2**64-1).to_bytes(8,'little')+(-123).to_bytes(4,'little',signed=True)
 for size in range(len(body)):
  assert parse_dlmm_from_program_data(body[:size],{}) is None
 event=parse_dlmm_from_program_data(body,{})
 assert event.data.total_reward==event.data.reward_index==2**64-1 and event.data.active_bin_id==-123
 converted=legacy_dict_to_dex_event({'MeteoraDlmmClaimReward':{'pool':event.data.pool,'position':event.data.position,'owner':event.data.owner,'reward_index':str(2**64-1),'total_reward':str(2**64-1),'active_bin_id':-123,'metadata':{}}})
 assert converted.data==event.data
