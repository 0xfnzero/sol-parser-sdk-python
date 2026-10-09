"""Offline regression for the actual DEX stream's configured reconnect backoff."""
import asyncio
from sol_parser.grpc_client import DexEventQueue, YellowstoneGrpc
from sol_parser.grpc_types import ClientConfig
from sol_parser import geyser_pb2 as pb


def test_retry_delay_uses_config_backoff_and_resets_on_success(monkeypatch):
    async def run():
        config = ClientConfig.low_latency()
        client = YellowstoneGrpc("http://localhost:1", config)
        cancel = asyncio.Event()
        delays = []

        class Transport:
            attempts = 0

            async def Subscribe(self, *args, **kwargs):
                self.attempts += 1
                if self.attempts == 3:
                    yield pb.SubscribeUpdate(ping=pb.SubscribeUpdatePing())
                raise ConnectionError("offline transport failure")

        async def record_sleep(delay):
            delays.append(delay)
            if len(delays) == 3:
                cancel.set()

        client._client = Transport()
        monkeypatch.setattr(asyncio, "sleep", record_sleep)
        await client._handle_dex_stream(object(), DexEventQueue(8), cancel, None, asyncio.Queue())
        assert delays == [0.1, 0.2, 0.1]

    asyncio.run(run())
