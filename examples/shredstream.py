"""SHREDSTREAM_URL=... SHREDSTREAM_X_TOKEN=... python examples/shredstream.py

Optional SHRED_ALT_CACHE_FILE: JSON {"ALT public key": ["address", ...]} loaded
before subscribing. Refresh snapshots outside the callback, never by hot-path RPC.
"""
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sol_parser import ShredStreamClient, ShredStreamConfig, format_dex_event_json
from sol_parser.grpc_types import EventType, IncludeOnlyFilter


def main():
    client = ShredStreamClient(os.environ['SHREDSTREAM_URL'], ShredStreamConfig(
        auth_token=os.getenv('SHREDSTREAM_X_TOKEN')))
    cache_file = os.getenv('SHRED_ALT_CACHE_FILE')
    if cache_file:
        tables = json.loads(Path(cache_file).read_text())
        def resolve(transaction, slot, recv_us, tx_index, event_type_filter):
            writable, readonly = [], []
            for lookup in transaction['message']['addressTableLookups']:
                table = tables.get(lookup['accountKey'])
                if table is None:
                    print(f"ALT miss slot={slot} tx_index={tx_index} recv_us={recv_us} key={lookup['accountKey']}", file=sys.stderr)
                    return None
                writable.extend(table[i] for i in lookup['writableIndexes'])
                readonly.extend(table[i] for i in lookup['readonlyIndexes'])
            return writable, readonly
        client.with_address_lookup_resolver(resolve)
    filter = IncludeOnlyFilter([EventType.PUMP_FUN_CREATE, EventType.PUMP_FUN_TRADE])
    for event in client.iter_dex_events(filter, on_error=lambda error: print(error, file=sys.stderr)):
        print(format_dex_event_json(event))


if __name__ == '__main__':
    main()
