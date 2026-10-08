"""Nonzero and repeat fee claims, delegate owner identity, large integers and rollback."""
import json
from pathlib import Path
import pytest
from sol_parser.rpc_parser import parse_rpc_transaction,rpc_get_transaction_result_dict_to_response
CASES=json.loads((Path(__file__).parent/'fixtures/damm_v2_fees_20261008.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_damm_v2_fees_bank(case):
 events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(case['raw']),'simulation',None,0)
 assert error is None
 if case['raw']['meta']['err'] is not None:
  assert not events
  if case['name']=='owner_claim_then_failed_delegate':assert case['bank_validation']['rolled_back_claim_events']>0
  return
 lp=[e for e in events if e.type.value in ('MeteoraDammV2ClaimPositionFee',)]
 assert len(lp)==len(case['expected'])
 for event,want in zip(lp,case['expected']):
  assert event.type.value==want['type']
  for key,value in want.items():
   if key!='type':assert str(getattr(event.data,key))==value

def test_fee_claim_truncation_and_u64_precision():
 import base58
 from sol_parser.dex_parsers import parse_meteora_damm_from_buf
 from sol_parser.event_types import legacy_dict_to_dex_event
 c=CASES[0]
 ix=next(i for g in c['raw']['meta']['innerInstructions'] for i in g['instructions'] if base58.b58decode(i['data'])[8:16]==bytes([198,182,183,52,97,12,49,56]))
 body=base58.b58decode(ix['data'])[8:]
 for length in range(len(body)):
  assert parse_meteora_damm_from_buf(body[:length],{}) is None
 event=parse_meteora_damm_from_buf(body,{})
 assert event.data.fee_a_claimed==209095310084412990
 decoded=legacy_dict_to_dex_event({'MeteoraDammV2ClaimPositionFee':{'pool':event.data.pool,'position':event.data.position,'owner':event.data.owner,'fee_a_claimed':str(event.data.fee_a_claimed),'fee_b_claimed':'31995','metadata':{}}})
 assert decoded.data==event.data
