"""Whirlpool legacy/v2 liquidity quantities and NFT lifecycle, with failed prefix rollback."""
import json
from pathlib import Path
import pytest
from sol_parser.rpc_parser import parse_rpc_transaction,rpc_get_transaction_result_dict_to_response
CASES=json.loads((Path(__file__).parent/'fixtures/whirlpool_fees_20261008.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_whirlpool_fees_bank(case):
 events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(case['raw']),'simulation',None,0)
 assert error is None
 if case['raw']['meta']['err'] is not None:
  assert not events
  if case['name'].endswith('close_nonempty'):assert case['bank_validation']['rolled_back_liquidity_events']>0
  return
 lp=[e for e in events if e.type.value in ('OrcaWhirlpoolLiquidityIncreased','OrcaWhirlpoolLiquidityDecreased')]
 assert len(lp)==len(case['expected'])
 for event,want in zip(lp,case['expected']):
  assert event.type.value==want['type']
  for key,value in want.items():
   if key!='type':assert str(getattr(event.data,key))==value
