"""Nonzero and repeat fee claims, delegate owner identity, large integers and rollback."""
import json
from pathlib import Path
import pytest
from sol_parser.rpc_parser import parse_rpc_transaction,rpc_get_transaction_result_dict_to_response
CASES=json.loads((Path(__file__).parent/'fixtures/damm_v2_rewards_20261008.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_damm_v2_rewards_bank(case):
 events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(case['raw']),'simulation',None,0)
 assert error is None
 if case['raw']['meta']['err'] is not None:
  assert not events
  return
 lp=[e for e in events if e.type.value in ('MeteoraDammV2ClaimReward',)]
 assert len(lp)==len(case['expected'])
 for event,want in zip(lp,case['expected']):
  assert event.type.value==want['type']
  for key,value in want.items():
   if key!='type':assert str(getattr(event.data,key))==value


def test_reward_claim_precision_boundaries_and_legacy():
 from sol_parser.dex_parsers import parse_meteora_damm_from_buf
 from sol_parser.event_types import legacy_dict_to_dex_event
 body=bytes([218,86,147,200,235,188,215,231])+bytes(range(128))+bytes([1])+(2**64-1).to_bytes(8,'little')
 for length in range(len(body)):
  assert parse_meteora_damm_from_buf(body[:length],{}) is None
 event=parse_meteora_damm_from_buf(body,{})
 assert event.data.total_reward==2**64-1 and event.data.reward_index==1
 decoded=legacy_dict_to_dex_event({'MeteoraDammV2ClaimReward':{'pool':event.data.pool,'position':event.data.position,'owner':event.data.owner,'mint_reward':event.data.mint_reward,'reward_index':1,'total_reward':str(2**64-1),'metadata':{}}})
 assert decoded.data==event.data
