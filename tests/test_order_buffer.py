from sol_parser.event_types import DexEvent, PumpFunTradeEvent
from sol_parser.grpc_types import ClientConfig, EventMetadata, EventType, OrderMode
from sol_parser.order_buffer import OrderDispatcher


def _event(signature: str, slot: int, tx_index: int) -> DexEvent:
    return DexEvent(
        type=EventType.PUMP_FUN_TRADE,
        data=PumpFunTradeEvent(
            metadata=EventMetadata(signature=signature, slot=slot, tx_index=tx_index)
        ),
    )


def test_order_dispatcher_orders_buffered_transactions():
    dispatcher = OrderDispatcher(ClientConfig(order_mode=OrderMode.ORDERED))
    out = []

    dispatcher.push_transaction_events([_event("tx2", 1, 2)], 1, 2, out.append)
    dispatcher.push_transaction_events([_event("tx1", 1, 1)], 1, 1, out.append)
    assert out == []

    dispatcher.push_transaction_events([_event("tx0", 2, 0)], 2, 0, out.append)
    assert [ev.data.metadata.signature for ev in out] == ["tx1", "tx2"]


def test_order_dispatcher_streams_whole_transaction_batch():
    dispatcher = OrderDispatcher(ClientConfig(order_mode=OrderMode.STREAMING_ORDERED))
    out = []

    dispatcher.push_transaction_events(
        [_event("tx0-a", 1, 0), _event("tx0-b", 1, 0)],
        1,
        0,
        out.append,
    )

    assert [ev.data.metadata.signature for ev in out] == ["tx0-a", "tx0-b"]
