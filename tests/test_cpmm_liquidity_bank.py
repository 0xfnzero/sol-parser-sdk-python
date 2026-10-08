"""LP intent identities and full-transaction rollback from current-bank simulations."""
import json
import base64
from pathlib import Path
import pytest
from sol_parser.rpc_parser import parse_rpc_transaction,rpc_get_transaction_result_dict_to_response
CASES=json.loads((Path(__file__).parent/'fixtures/cpmm_liquidity_20261008.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_cpmm_liquidity_bank(case):
 events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(case['raw']),'simulation',None,0)
 assert error is None
 if case['raw']['meta']['err'] is not None:
  assert not events, 'rolled-back prefix trade/deposit retained'
  if case['name']=='withdraw_impossible_minimum':
   payloads=[base64.b64decode(line[14:]) for line in case['raw']['meta']['logMessages'] if line.startswith('Program data: ')]
   lp_payloads=[p for p in payloads if p[:8]==bytes([121,163,205,201,57,218,117,60])]
   assert len(lp_payloads)==2 and [p[96] for p in lp_payloads]==[0,1]
  return
 lp=[e for e in events if e.type.value in ('RaydiumCpmmDeposit','RaydiumCpmmWithdraw')]
 assert len(lp)==len(case['expected'])
 for event,want in zip(lp,case['expected']):
  assert event.type.value==want['type']
  for key,value in want.items():
   if key!='type': assert getattr(event.data,key)==(value if key in ('pool','user') else int(value))
