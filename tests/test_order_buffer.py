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


def test_streaming_timeout_retains_progress_and_bounds_pending_state():
    dispatcher = OrderDispatcher(ClientConfig(order_mode=OrderMode.STREAMING_ORDERED))
    out = []
    for index in (0, 2, 2):
        dispatcher.push_transaction_events([_event(f"tx{index}", 42, index)], 42, index, out.append)
    dispatcher.last_flush -= 2 * dispatcher.timeout_s
    dispatcher.flush_due(out.append)
    for index in (0, 1, 2, 3):
        dispatcher.push_transaction_events([_event(f"tx{index}", 42, index)], 42, index, out.append)
    assert [ev.data.metadata.tx_index for ev in out] == [0, 2, 3]
    assert dispatcher.watermarks == {42: 4}
    assert not dispatcher.pending_indexes and not dispatcher.slots
    dispatcher.push_transaction_events([_event("next", 43, 0)], 43, 0, out.append)
    dispatcher.push_transaction_events([_event("old", 42, 0)], 42, 0, out.append)
    assert [ev.data.metadata.signature for ev in out] == ["tx0", "tx2", "tx3", "next"]
    assert dispatcher.watermarks == {43: 1}
    # Buffered whole batches release once and preserve transaction-internal order.
    dispatcher.push_transaction_events([_event("a", 43, 2), _event("b", 43, 2)], 43, 2, out.append)
    dispatcher.push_transaction_events([_event("duplicate", 43, 2)], 43, 2, out.append)
    dispatcher.push_transaction_events([_event("gap", 43, 1)], 43, 1, out.append)
    assert [ev.data.metadata.signature for ev in out][-3:] == ["gap", "a", "b"]
    assert not dispatcher.pending_indexes and not dispatcher.slots
    dispatcher.flush_all(out.append)
    dispatcher.push_transaction_events([_event("replay", 43, 0)], 43, 0, out.append)
    assert out[-1].data.metadata.signature == "b"


def test_repeated_pending_and_old_indexes_remain_bounded():
    dispatcher = OrderDispatcher(ClientConfig(order_mode=OrderMode.STREAMING_ORDERED))
    out = []
    for _ in range(10000):
        dispatcher.push_transaction_events([_event("pending", 42, 2)], 42, 2, out.append)
    assert len(dispatcher.slots[42]) == 1 and len(dispatcher.pending_indexes) == 1
    dispatcher.flush_all(out.append)
    assert len(out) == 1 and not dispatcher.slots and not dispatcher.pending_indexes
    dispatcher.push_transaction_events([_event("next", 43, 0)], 43, 0, out.append)
    for _ in range(10000):
        dispatcher.push_transaction_events([_event("old", 42, 2)], 42, 2, out.append)
    assert len(out) == 2 and not dispatcher.slots and len(dispatcher.watermarks) == 1
