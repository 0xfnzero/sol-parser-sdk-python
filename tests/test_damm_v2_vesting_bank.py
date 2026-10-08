"""Actual liquidity quantities and NFT lifecycle, with failed prefix rollback."""
import json
from pathlib import Path
import pytest
from sol_parser.rpc_parser import parse_rpc_transaction,rpc_get_transaction_result_dict_to_response
CASES=json.loads((Path(__file__).parent/'fixtures/damm_v2_vesting_20261008.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_damm_v2_vesting_bank(case):
 events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(case['raw']),'simulation',None,0)
 assert error is None
 if case['raw']['meta']['err'] is not None:
  assert not events
  if 'rolled_back_position_events' in case['bank_validation']:assert case['bank_validation']['rolled_back_position_events']>0
  return
 lp=[e for e in events if e.type.value in ('MeteoraDammV2CreatePosition','MeteoraDammV2ClosePosition','MeteoraDammV2AddLiquidity','MeteoraDammV2RemoveLiquidity')]
 assert len(lp)==len(case['expected'])
 for event,want in zip(lp,case['expected']):
  assert event.type.value==want['type']
  for key,value in want.items():
   if key!='type':assert str(getattr(event.data,key))==value
