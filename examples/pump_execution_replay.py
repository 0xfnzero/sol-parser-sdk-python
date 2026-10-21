"""Offline execution replay; optional signature fetch uses SOLANA_RPC_URL.

Inspect third_program and parse_status. Execution metadata is unavailable to Shred;
one outer wrapper may produce several fills, so callback counts may differ.
"""
import json
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sol_parser import format_dex_event_json
from sol_parser.rpc_parser import parse_rpc_transaction, rpc_get_transaction_result_dict_to_response
from parse_tx_by_signature import fetch_transaction

if len(sys.argv) > 1:
    raw = fetch_transaction(sys.argv[1], os.environ.get('SOLANA_RPC_URL', 'https://api.mainnet-beta.solana.com'))
    if raw is None:
        raise RuntimeError('Transaction not found; use a recent signature or an archive RPC')
    cases = [{'raw': raw}]
else:
    cases = sum((json.loads((Path(__file__).resolve().parents[1] / 'tests/fixtures' / name).read_text())['cases']
                 for name in ['pump_execution_20261019.json', 'wrapped_pumpfun_reported.json']), [])
for case in cases:
    raw = case['raw']
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
