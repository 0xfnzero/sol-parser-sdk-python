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
    assert len(out)==2  # Two ordinary calls remain distinct even with identical identities.
    if mismatch!='none': assert out[0]==before

@pytest.mark.parametrize('heights', [(1,2,2,3), (None,None,None,None)])
def test_repeated_trades_pair_with_their_own_cpi(heights):
    def trade(amount, executed=False):
        return DexEvent(EventType.PUMP_FUN_TRADE, PumpFunTradeEvent(mint='mintA', user='userA', is_buy=True, ix_name='buy_v3', amount=amount if not executed else 0, token_amount=amount if executed else 0))
    h0,h1,h2,h3=heights
    out=merge_instruction_events([(0,None,h0,False,trade(100)),(0,0,h1,True,trade(90,True)),(0,1,h2,False,trade(200)),(0,2,h3,True,trade(180,True))])
    assert [(e.data.amount,e.data.token_amount) for e in out]==[(100,90),(200,180)]

def test_second_execution_event_cannot_overwrite_first():
    def trade(amount=0):
        return DexEvent(EventType.PUMP_FUN_TRADE, PumpFunTradeEvent(mint='mintA',user='userA',is_buy=True,ix_name='buy_v3',token_amount=amount))
    out=merge_instruction_events([(0,None,1,False,trade()),(0,0,2,True,trade(90)),(0,1,2,True,trade(180))])
    assert [e.data.token_amount for e in out]==[90,180]

@pytest.mark.parametrize('kind', ['buy','sell'])
def test_repeated_swap_occurrences_survive_log_instruction_dedup(kind):
    from sol_parser.log_instr_dedup import dedupe_log_instruction_events
    cls=PumpSwapBuyEvent if kind=='buy' else PumpSwapSellEvent
    et=EventType.PUMP_SWAP_BUY if kind=='buy' else EventType.PUMP_SWAP_SELL
    executed='quote_amount_in' if kind=='buy' else 'quote_amount_out'
    limit='max_quote_amount_in' if kind=='buy' else 'min_quote_amount_out'
    logs=[DexEvent(et,cls(pool='pool',user='user',**{executed:n})) for n in (90,180)]
    instructions=[DexEvent(et,cls(pool='pool',user='user',user_base_token_account=str(n),**{limit:n})) for n in (100,200)]
    assert len(dedupe_log_instruction_events([],copy.deepcopy(instructions)))==2
    out=dedupe_log_instruction_events(logs,instructions)
    assert [(e.data.user_base_token_account,getattr(e.data,executed)) for e in out]==[('100',90),('200',180)]

@pytest.mark.parametrize('kind', ['buy','sell'])
@pytest.mark.parametrize('known', [True,False])
def test_repeated_swap_calls_pair_with_their_own_cpi(kind,known):
    cls=PumpSwapBuyEvent if kind=='buy' else PumpSwapSellEvent
    et=EventType.PUMP_SWAP_BUY if kind=='buy' else EventType.PUMP_SWAP_SELL
    executed='quote_amount_in' if kind=='buy' else 'quote_amount_out'
    def event(amount,execution=False):
        return DexEvent(et,cls(pool='pool',user='user',**({executed:amount} if execution else {'user_base_token_account':str(amount)})))
    def h(n): return n if known else None
    out=merge_instruction_events([(0,None,h(1),False,event(100)),(0,0,h(2),True,event(90,True)),(0,1,h(2),False,event(200)),(0,2,h(3),True,event(180,True))])
    assert [(e.data.user_base_token_account,getattr(e.data,executed)) for e in out]==[('100',90),('200',180)]

@pytest.mark.parametrize('kind', ['pump', 'buy', 'sell'])
@pytest.mark.parametrize('counts', [(1,2), (2,1)])
def test_incomplete_trade_sources_are_not_paired(kind, counts):
    from sol_parser.log_instr_dedup import dedupe_log_instruction_events
    cls = PumpFunTradeEvent if kind == 'pump' else (PumpSwapBuyEvent if kind == 'buy' else PumpSwapSellEvent)
    et = EventType.PUMP_FUN_TRADE if kind == 'pump' else (EventType.PUMP_SWAP_BUY if kind == 'buy' else EventType.PUMP_SWAP_SELL)
    base = {'mint':'mint', 'is_buy':True, 'ix_name':'buy_v3'} if kind == 'pump' else {'pool':'pool'}
    field = 'bonding_curve' if kind == 'pump' else 'user_base_token_account'
    logs = [DexEvent(et, cls(user='user', **base)) for _ in range(counts[0])]
    before = copy.deepcopy(logs)
    instructions = [DexEvent(et, cls(user='user', **base, **{field:f'account{i}'})) for i in range(counts[1])]
    out = dedupe_log_instruction_events(logs, instructions)
    assert len(out) == sum(counts)
    assert out[:counts[0]] == before

def test_incomplete_source_guard_is_scoped_to_pump_lane():
    from sol_parser.log_instr_dedup import dedupe_log_instruction_events
    def event(lane, account=''):
        return DexEvent(EventType.PUMP_FUN_TRADE, PumpFunTradeEvent(mint='mint',user='user',is_buy=True,ix_name=lane,bonding_curve=account))
    out = dedupe_log_instruction_events(
        [event('buy_v3'),event('buy_exact_quote_in_v3')],
        [event('buy_v3','first'),event('buy_v3','second'),event('buy_exact_quote_in_v3','exact')])
    assert len(out) == 4
    assert out[0].data.bonding_curve == ''
    assert out[1].data.bonding_curve == 'exact'
