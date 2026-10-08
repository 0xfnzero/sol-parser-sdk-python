"""Executed partial-fill remainder differs from gross unused wallet funding."""
import json
from pathlib import Path
import pytest
from sol_parser.rpc_parser import parse_rpc_transaction,rpc_get_transaction_result_dict_to_response

CASES=json.loads((Path(__file__).parent/'fixtures/dbc_boundary_20261008.json').read_text())['cases']
@pytest.mark.parametrize('case',CASES,ids=lambda c:c['name'])
def test_dbc_boundary_bank_events_and_rollback(case):
    events,error=parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(case['raw']),'simulation',None,0)
    assert error is None
    if case['raw']['meta']['err'] is not None:
        assert not events
        if 'after_curve_completed' in case['name']:
            assert case['rolled_back_curve_complete_payloads']>0
        return
    swaps=[e.data for e in events if e.type.value=='MeteoraDbcSwap']
    complete=[e.data for e in events if e.type.value=='MeteoraDbcCurveComplete']
    assert len(swaps)==len(complete)==1
    e=swaps[0];v=case['validation']
    for key,want in case['expected_swap'].items():
        assert getattr(e,key)==(want if isinstance(want,bool) else int(want))
    assert e.included_fee_input_amount==v['bank_consumed_quote']
    assert e.output_amount==v['bank_base_credit'] and e.referral_fee==v['bank_referral_credit']
    assert e.amount_left!=v['bank_unconsumed_quote']
    assert e.amount_left+v['initial_requested_input_fee']-v['recalculated_fill_fee']==v['bank_unconsumed_quote']
    assert complete[0].quote_reserve==e.quote_reserve_amount>=e.migration_threshold
