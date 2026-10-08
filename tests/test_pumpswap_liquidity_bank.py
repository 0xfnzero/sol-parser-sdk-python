"""LP intent identities and full-transaction rollback from current-bank simulations."""
import json
import base64
from pathlib import Path
import pytest
from sol_parser.rpc_parser import parse_rpc_transaction,rpc_get_transaction_result_dict_to_response
CASES=json.loads((Path(__file__).parent/'fixtures/pumpswap_liquidity_20261008.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_pumpswap_liquidity_bank(case):
 events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(case['raw']),'simulation',None,0)
 assert error is None
 if case['raw']['meta']['err'] is not None:
  assert not events, 'rolled-back prefix trade/deposit retained'
  return
 lp=[e for e in events if e.type.value in ('PumpSwapLiquidityAdded','PumpSwapLiquidityRemoved')]
 assert len(lp)==len(case['expected'])
 for event,want in zip(lp,case['expected']):
  assert event.type.value==want['type']
  for key,value in want.items():
   if key!='type': assert getattr(event.data,key)==(value if key in ('pool','user','user_base_token_account','user_quote_token_account','user_pool_token_account') else int(value))

def test_pumpswap_lp_event_rejects_every_truncated_body():
 from sol_parser.dex_parsers import parse_ps_add_liq_from_data,parse_ps_remove_liq_from_data
 # Official event body: 11 eight-byte fields and five public keys.
 for parser in (parse_ps_add_liq_from_data,parse_ps_remove_liq_from_data):
  for size in range(248):assert parser(bytes(size),{}) is None
