"""Whirlpool legacy/v2 liquidity quantities and NFT lifecycle, with failed prefix rollback."""
import json
from pathlib import Path
import pytest
from sol_parser.rpc_parser import parse_rpc_transaction,rpc_get_transaction_result_dict_to_response
CASES=json.loads((Path(__file__).parent/'fixtures/clmm_liquidity_20261008.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_clmm_liquidity_bank(case):
 events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(case['raw']),'simulation',None,0)
 assert error is None
 if case['raw']['meta']['err'] is not None:
  assert not events
  if case['name'].endswith('close_nonempty'):assert case['bank_validation']['rolled_back_liquidity_events']>0
  return
 lp=[e for e in events if e.type.value in ('RaydiumClmmIncreaseLiquidity','RaydiumClmmDecreaseLiquidity')]
 assert len(lp)==len(case['expected'])
 for event,want in zip(lp,case['expected']):
  assert event.type.value==want['type']
  for key,value in want.items():
   if key!='type':assert str(getattr(event.data,key))==value


def test_clmm_occurrences_and_unresolved_instruction_mint():
 from copy import deepcopy
 from sol_parser.log_instr_dedup import dedupe_log_instruction_events
 case=next(c for c in CASES if c['name']=='increase_base0')
 events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(case['raw']),'simulation',None,0)
 assert error is None
 log=next(e for e in events if e.type.value=='RaydiumClmmIncreaseLiquidity')
 ix=deepcopy(log);ix.data.position_nft_mint='';ix.data.liquidity='0';ix.data.amount_0=ix.data.amount_1=0
 out=dedupe_log_instruction_events([deepcopy(log),deepcopy(log)],[deepcopy(ix),deepcopy(ix)])
 assert len(out)==2 and all(e.data.liquidity==log.data.liquidity and e.data.position_nft_mint==log.data.position_nft_mint for e in out)
 assert len(dedupe_log_instruction_events([deepcopy(log)],[deepcopy(ix),deepcopy(ix)]))==3
 ix.data.personal_position='11111111111111111111111111111111'
 assert len(dedupe_log_instruction_events([deepcopy(log)],[ix]))==2
 raw=deepcopy(case['raw']);raw['meta']['logMessages']=[]
 events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(raw),'simulation',None,0)
 assert error is None
 ix=next(e for e in events if e.type.value=='RaydiumClmmIncreaseLiquidity')
 assert ix.data.position_nft_mint=='' and ix.data.personal_position==log.data.personal_position and ix.data.liquidity=='0'
