"""Current compact layouts from successful mainnet bank execution."""
import base64,json
from pathlib import Path
import pytest
from sol_parser import analyze_simulation_routes
CORPUS=json.loads((Path(__file__).parent/'fixtures/pump_compact_simulations_20261008.json').read_text())
@pytest.mark.parametrize('case',CORPUS['cases'],ids=lambda c:c['name'])
def test_current_compact_bank_execution_routes(case):
    route=analyze_simulation_routes(base64.b64decode(case['wire']),case['response'])
    name=case['name']; expected=2 if name in ('pump_sell_v3','pump_amm_sell_v2') else 1
    assert len(route.legs)==expected
    assert route.succeeded == (case['response']['result']['value']['err'] is None)
    assert all(leg.protocol==('PumpSwap' if 'amm' in name else 'PumpFun') for leg in route.legs)
    leg=route.legs[-1]
    assert leg.input_mint and leg.output_mint and leg.input_mint!=leg.output_mint
    assert leg.specified_amount>0 and leg.other_amount_threshold>0
    if not route.succeeded:
        assert leg.actual_input_amount is None and leg.actual_output_amount is None
