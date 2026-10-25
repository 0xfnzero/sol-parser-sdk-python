"""Offline execution replay; optional signature fetch uses SOLANA_RPC_URL.

Inspect third_program and parse_status. Execution metadata is unavailable to Shred;
one outer wrapper may produce several fills, so callback counts may differ.
"""
import json
import base64
import requests
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sol_parser import format_dex_event_json
from sol_parser.shredstream_client import parse_shred_transaction, parse_shred_transaction_with_loaded_addresses
from sol_parser.grpc_types import EventType, IncludeOnlyFilter
from sol_parser.rpc_parser import parse_rpc_transaction, rpc_get_transaction_result_dict_to_response
from parse_tx_by_signature import fetch_transaction

if len(sys.argv) > 1:
    raw = fetch_transaction(sys.argv[1], os.environ.get('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com'))
    if raw is None:
        raise RuntimeError('Transaction not found; use a recent signature or an archive RPC')
    response = requests.post(os.environ.get('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com'),
        json=dict(jsonrpc='2.0',id=2,method='getTransaction',params=[sys.argv[1],dict(encoding='base64',maxSupportedTransactionVersion=1)]),timeout=30)
    response.raise_for_status()
    wire_rpc = response.json().get('result')
    if not wire_rpc:raise RuntimeError('Wire transaction unavailable')
    cases = [{'raw': raw, 'wire_rpc': wire_rpc}]
else:
    cases = sum((json.loads((Path(__file__).resolve().parents[1] / 'tests/fixtures' / name).read_text())['cases']
                 for name in ['pump_create_alt_20261026.json', 'pump_multi_hop_20261025.json', 'wrapped_pumpfun_reported.json']), [])
for case in cases:
    raw = case['raw']
    if 'wire_rpc' in case:
        wire_rpc=case['wire_rpc']
        wire=base64.b64decode(wire_rpc['transaction'][0])
        loaded=wire_rpc['meta']['loadedAddresses']
        filter=IncludeOnlyFilter([EventType.PUMP_FUN_CREATE,EventType.PUMP_FUN_TRADE])
        for mode,events in (
            ('static_keys',parse_shred_transaction(wire,slot=raw['slot'],tx_index=888,recv_us=123456,filter=filter)),
            ('resolved_alt',parse_shred_transaction_with_loaded_addresses(wire,loaded['writable'],loaded['readonly'],slot=raw['slot'],tx_index=888,recv_us=123456,filter=filter))):
            print(f'shred {mode} event_count={len(events)} signature={raw["transaction"]["signatures"][0]}')
            for event in events:print(format_dex_event_json(event))
    logs = raw['meta']['logMessages']
    for mode, variant in [('full',logs),('no_logs',[]),('truncated_logs',logs[:len(logs)//2])]:
        raw['meta']['logMessages'] = variant
        signature = raw['transaction']['signatures'][0]
        events, error = parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(raw), signature, None, 0)
        if error:
            raise RuntimeError(error)
        print(f'execution_replay {mode} event_count={len(events)} slot={raw["slot"]} signature={signature}')
        for event in events:
            print(format_dex_event_json(event))
