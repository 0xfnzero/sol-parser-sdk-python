"""Actual TCP gRPC validation, including full u64 and latest filters after reconnect."""
import asyncio
import grpc
from sol_parser import YellowstoneGrpc
from sol_parser import geyser_pb2 as pb, geyser_pb2_grpc as service
from sol_parser.grpc_types import EventType, TransactionFilter, event_type_filter_include_only

def test_tcp_lifecycle_and_latest_configuration():
    async def run():
        requests=[]
        class Server(service.GeyserServicer):
            starts=0
            async def Subscribe(self, iterator, context):
                self.starts+=1
                attempt=self.starts
                async for request in iterator:
                    requests.append(request)
                    if attempt==1 and request.transactions:
                        await context.abort(grpc.StatusCode.UNAVAILABLE,"test reconnect")
                    yield pb.SubscribeUpdate(block_meta=pb.SubscribeUpdateBlockMeta(slot=2**64-1,blockhash="observed",parent_slot=2**64-2))
        server=grpc.aio.server()
        impl=Server();service.add_GeyserServicer_to_server(impl,server)
        port=server.add_insecure_port("127.0.0.1:0");await server.start()
        client=YellowstoneGrpc.new(f"http://127.0.0.1:{port}")
        client.config.retry_delay_ms=1
        try:
            q=await client.subscribe_dex_events([],[],event_type_filter_include_only([EventType.BLOCK_META]))
            event=await asyncio.wait_for(q.get(),3)
            assert event.data.metadata.slot==2**64-1
            await client.update_subscription([TransactionFilter(account_include=["latest"])],[])
            error=await asyncio.wait_for(q.errors.get(),3)
            assert isinstance(error,grpc.RpcError)
            event=await asyncio.wait_for(q.get(),3)
            assert impl.starts==2
            assert next(iter(requests[-1].transactions.values())).account_include==["latest"]
            assert q.status().continuity_broken and q.status().reconnects==1
            old_task=client._dex_task
            replacement=await client.subscribe_dex_events([],[],event_type_filter_include_only([EventType.BLOCK_META]))
            assert old_task.done() and q.status().state=="stopped"
            await asyncio.wait_for(replacement.get(),3)
            await client.stop()
            assert replacement.status().state=="stopped"
        finally:
            await client.disconnect();await server.stop(0)
    asyncio.run(run())
