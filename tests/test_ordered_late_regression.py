from sol_parser.event_types import DexEvent, PumpFunTradeEvent
from sol_parser.grpc_types import ClientConfig, EventMetadata, EventType, OrderMode
from sol_parser.order_buffer import OrderDispatcher

def event(slot,index,id='tx'):
    return DexEvent(type=EventType.PUMP_FUN_TRADE,data=PumpFunTradeEvent(metadata=EventMetadata(signature=id,slot=slot,tx_index=index)))

def test_ordered_rejects_closed_slot_late_batches(caplog):
    d=OrderDispatcher(ClientConfig(order_mode=OrderMode.ORDERED));out=[]
    for slot,index in [(10,2),(11,0),(10,1),(10,9),(12,0)]:
        d.push_transaction_events([event(slot,index)],slot,index,out.append)
    d.flush_all(out.append)
    assert [(e.data.metadata.slot,e.data.metadata.tx_index) for e in out]==[(10,2),(11,0),(12,0)]
    assert d.ordered_late_transactions==2
    assert len([r for r in caplog.records if 'Ordered continuity break' in r.message])==2

def test_ordered_timeout_retains_watermark_and_complete_batch_order(caplog):
    d=OrderDispatcher(ClientConfig(order_mode=OrderMode.ORDERED));out=[]
    d.push_transaction_events([event(42,2,'a'),event(42,2,'b')],42,2,out.append)
    d.last_flush-=d.timeout_s*2
    d.flush_due(out.append)
    for index in (0,1,2,3):
        d.push_transaction_events([event(42,index,str(index))],42,index,out.append)
    d.flush_all(out.append)
    assert [e.data.metadata.signature for e in out]==['a','b','3']
    assert d.ordered_late_transactions==3


def test_ordered_late_replay_bounds_diagnostics(caplog):
    d = OrderDispatcher(ClientConfig(order_mode=OrderMode.ORDERED)); out = []
    d.push_transaction_events([event(10, 2)], 10, 2, out.append)
    d.flush_all(out.append)
    for _ in range(10000):
        d.push_transaction_events([event(10, 1)], 10, 1, out.append)
    assert d.ordered_late_transactions == 10000
    assert len([r for r in caplog.records if 'Ordered continuity break' in r.message]) == 20
    assert len(out) == 1
    d.push_transaction_events([event(10, 3)], 10, 3, out.append)
    d.flush_all(out.append)
    assert len(out) == 2
