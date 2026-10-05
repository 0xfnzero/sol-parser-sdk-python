"""Read one gRPC BlockMeta event using GRPC_URL/GRPC_TOKEN; no RPC."""

import asyncio, os, json
from sol_parser import YellowstoneGrpc, EventType, event_type_filter_include_only


async def main():
    client = YellowstoneGrpc.new(os.environ["GRPC_URL"], os.environ.get("GRPC_TOKEN"))
    try:
        queue = await client.subscribe_dex_events(
            [], [], event_type_filter_include_only([EventType.BLOCK_META])
        )
        event = await asyncio.wait_for(queue.get(), 30)
        print(json.dumps(vars(event.data.metadata)))
    finally:
        await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
