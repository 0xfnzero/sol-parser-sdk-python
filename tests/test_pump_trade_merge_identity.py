"""Distinct trades nested under one outer instruction must survive merging."""
import copy
import pytest
from sol_parser.event_types import DexEvent, PumpFunTradeEvent, PumpSwapBuyEvent, PumpSwapSellEvent
from sol_parser.grpc_types import EventType
from sol_parser.grpc_instruction_parser import merge_instruction_events

@pytest.mark.parametrize('kind', ['pump', 'swap_buy', 'swap_sell'])
@pytest.mark.parametrize('mismatch', ['venue', 'user', 'direction', 'none'])
def test_nested_trade_identity(kind, mismatch):
    cls = PumpFunTradeEvent if kind == 'pump' else (PumpSwapBuyEvent if kind == 'swap_buy' else PumpSwapSellEvent)
    et = EventType.PUMP_FUN_TRADE if kind == 'pump' else (EventType.PUMP_SWAP_BUY if kind == 'swap_buy' else EventType.PUMP_SWAP_SELL)
    body = cls(user='userA', **({'mint':'mintA', 'is_buy':True, 'ix_name':'buy_v3'} if kind=='pump' else {'pool':'poolA'}))
    other = copy.deepcopy(body)
    other_type = et
    if mismatch=='venue': setattr(other,'mint' if kind=='pump' else 'pool','venueB')
    if mismatch=='user': other.user='userB'
    if mismatch=='direction':
        if kind=='pump': other.is_buy=False;other.ix_name='sell_v3'
        else:
            other= (PumpSwapSellEvent if kind=='swap_buy' else PumpSwapBuyEvent)(pool='poolA',user='userA')
            other_type=EventType.PUMP_SWAP_SELL if kind=='swap_buy' else EventType.PUMP_SWAP_BUY
    base=DexEvent(et,body);inner=DexEvent(other_type,other)
    before=copy.deepcopy(base)
    out=merge_instruction_events([(0,None,base),(0,0,inner)])
    assert len(out)==(1 if mismatch=='none' else 2)
    if mismatch!='none': assert out[0]==before
