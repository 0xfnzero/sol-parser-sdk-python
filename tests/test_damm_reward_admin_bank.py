"""Reward renewal net funding, carry-forward rates and failed transaction rollback."""
import json
from pathlib import Path
import pytest
from sol_parser.rpc_parser import parse_rpc_transaction,rpc_get_transaction_result_dict_to_response
CASES=json.loads((Path(__file__).parent/'fixtures/damm_reward_admin_20261009.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_damm_reward_admin_bank(case):
 events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(case['raw']),'simulation',None,0)
 assert error is None
 if case['raw']['meta']['err'] is not None:
  assert not events
  return
 lp=[e for e in events if e.type.value in ('MeteoraDammV2WithdrawIneligibleReward','MeteoraDammV2WithdrawDeadLiquidityReward','MeteoraDammV2FundReward','MeteoraDammV2InitializeReward','MeteoraDammV2UpdateRewardDuration','MeteoraDammV2UpdateRewardFunder')]
 assert len(lp)==len(case['expected'])
 for event,want in zip(lp,case['expected']):
  assert event.type.value==want['type']
  for key,value in want.items():
   if key!='type':assert str(getattr(event.data,key))==value

@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_administration_logs_and_truncated_payloads(case):
 from sol_parser.dex_parsers import parse_meteora_damm_from_buf
 for item in case['logs']:
  wire=bytes(item['bytes'])
  event=parse_meteora_damm_from_buf(wire,{'signature':'simulation','slot':1})
  assert event is not None
  assert event.type.value==item['expected']['type']
  for key,value in item['expected'].items():
   if key!='type':assert str(getattr(event.data,key))==value
  for end in range(len(wire)):
   assert parse_meteora_damm_from_buf(wire[:end],{}) is None
