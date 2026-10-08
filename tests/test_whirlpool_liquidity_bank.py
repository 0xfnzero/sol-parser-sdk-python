"""Whirlpool legacy/v2 liquidity quantities and NFT lifecycle, with failed prefix rollback."""
import json
from pathlib import Path
import pytest
from sol_parser.rpc_parser import parse_rpc_transaction,rpc_get_transaction_result_dict_to_response
CASES=json.loads((Path(__file__).parent/'fixtures/whirlpool_liquidity_20261008.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_whirlpool_liquidity_bank(case):
 events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(case['raw']),'simulation',None,0)
 assert error is None
 if case['raw']['meta']['err'] is not None:
  assert not events
  if case['name']=='close_nonempty':assert case['bank_validation']['rolled_back_liquidity_events']>0
  return
 lp=[e for e in events if e.type.value in ('OrcaWhirlpoolLiquidityIncreased','OrcaWhirlpoolLiquidityDecreased')]
 assert len(lp)==len(case['expected'])
 for event,want in zip(lp,case['expected']):
  assert event.type.value==want['type']
  for key,value in want.items():
   if key!='type':assert str(getattr(event.data,key))==value

def test_repeated_liquidity_and_missing_logs_are_not_collapsed():
 from copy import deepcopy
 from sol_parser.log_instr_dedup import dedupe_log_instruction_events
 case=next(c for c in CASES if c['name']=='increase')
 events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(case['raw']),'simulation',None,0)
 assert error is None
 log=next(e for e in events if e.type.value=='OrcaWhirlpoolLiquidityIncreased')
 instruction=deepcopy(log)
 instruction.data.token_a_amount=(1<<64)-1
 instruction.data.token_b_amount=(1<<64)-1
 instruction.data.tick_lower_index=instruction.data.tick_upper_index=0
 merged=dedupe_log_instruction_events([deepcopy(log),deepcopy(log)],[deepcopy(instruction),deepcopy(instruction)])
 assert len(merged)==2 and all(e.data==log.data for e in merged)
 assert len(dedupe_log_instruction_events([deepcopy(log)],[deepcopy(instruction),deepcopy(instruction)]))==3
 instruction.data.position='11111111111111111111111111111111'
 assert len(dedupe_log_instruction_events([deepcopy(log)],[instruction]))==2
