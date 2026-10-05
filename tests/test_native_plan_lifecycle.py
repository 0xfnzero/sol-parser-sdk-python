import asyncio
from types import SimpleNamespace
from sol_parser import (
    YellowstoneGrpc, DexEventQueue, GrpcStreamStatus,
    LaunchLabPoolCreateEvent, StonkFunPoolCreateEvent,
    LaunchLabTradeEvent, StonkFunTradeEvent,
    RaydiumLaunchlabPoolCreateEvent, RaydiumLaunchlabTradeEvent,
)

def test_public_aliases_preserve_event_identity():
    assert LaunchLabPoolCreateEvent is StonkFunPoolCreateEvent is RaydiumLaunchlabPoolCreateEvent
    assert LaunchLabTradeEvent is StonkFunTradeEvent is RaydiumLaunchlabTradeEvent

def test_queue_overflow_is_observable_continuity_failure():
    q = DexEventQueue(1)
    YellowstoneGrpc._queue_event_nowait(q, "first")
    YellowstoneGrpc._queue_event_nowait(q, "lost")
    assert q.get_nowait() == "first"
    assert q.status().dropped == 1
    assert q.status().continuity_broken

def test_grpc_failures_report_errors_and_stop_joins_old_tasks():
    async def run():
        started = asyncio.Event()
        exited = asyncio.Event()
        class Client:
            async def Subscribe(self, requests, metadata=None):
                started.set()
                try:
                    raise RuntimeError("simulated connection failure")
                    yield None
                finally:
                    exited.set()
        client = YellowstoneGrpc.new("http://127.0.0.1:1")
        client._connected = True
        client._client = Client()
        q = await client.subscribe_dex_events([], [])
        error = await asyncio.wait_for(q.errors.get(), 1)
        assert str(error) == "simulated connection failure"
        assert q.status().state == "reconnecting"
        assert q.status().continuity_broken
        task = client._dex_task
        replacement = await client.subscribe_dex_events([], [])
        assert task.done()
        assert q.status().state == "stopped"
        assert replacement is not q
        await client.stop()
        assert client._dex_task is None
        assert exited.is_set()
    asyncio.run(run())

def test_blockmeta_overflow_does_not_stall_stream_or_ping():
    from sol_parser.grpc_types import EventType, event_type_filter_include_only
    from sol_parser.grpc_client import geyser_pb2
    async def run():
        reached_ping = asyncio.Event()
        release = asyncio.Event()
        class Client:
            async def Subscribe(self, requests, metadata=None):
                await anext(requests)
                for slot in (1, 2):
                    yield geyser_pb2.SubscribeUpdate(block_meta=geyser_pb2.SubscribeUpdateBlockMeta(slot=slot,blockhash="observed"))
                # This must be reached without draining the full public queue.
                yield geyser_pb2.SubscribeUpdate(ping=geyser_pb2.SubscribeUpdatePing())
                request = await asyncio.wait_for(anext(requests), 1)
                assert request.HasField("ping")
                reached_ping.set()
                await release.wait()
        client = YellowstoneGrpc.new("http://127.0.0.1:1")
        client.config.buffer_size = 1
        client._connected = True
        client._client = Client()
        q = await client.subscribe_dex_events([], [], event_type_filter_include_only([EventType.BLOCK_META]))
        try:
            await asyncio.wait_for(reached_ping.wait(), 1)
            assert q.qsize() == 1 and q.status().dropped == 1
            assert q.status().continuity_broken
            assert q.get_nowait().data.metadata.slot == 1
        finally:
            await client.stop()
    asyncio.run(run())
