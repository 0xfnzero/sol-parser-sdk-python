import json
from pathlib import Path
import pytest
from sol_parser.parser import parse_log_unified
from sol_parser.grpc_types import EventType

CASES=json.loads((Path(__file__).parent/'fixtures/damm_v1_live_simulations_20261008.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_real_damm_v1_execution(case):
    assert len(case['logs']) == len(case['expected'])
    for log,want in zip(case['logs'],case['expected']):
        e=parse_log_unified(log,'simulation',1)
        assert e.type==EventType.METEORA_POOLS_SWAP
        for key,value in want.items():assert getattr(e.data,key)==value
        assert e.data.amount_in==e.data.minimum_out_amount==0
    if case['error'] is None:
        assert case['expected']
        if len(case['expected'])==1:assert case['expected'][0]['out_amount']==case['bank_output_balances'][0]
        else:
            buy,sell=case['expected']
            assert buy['out_amount']-sum(case['sell_source_debits'])==case['bank_output_balances'][0]
            assert 9900000+sell['out_amount']==case['bank_output_balances'][1]
