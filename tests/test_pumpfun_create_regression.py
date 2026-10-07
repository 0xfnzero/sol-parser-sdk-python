"""Real RPC fixtures plus invocation-selection and historical layout regressions."""
import json
import os
import struct
from pathlib import Path
from types import SimpleNamespace as NS

import base58
import pytest

from sol_parser.rpc_parser import rpc_get_transaction_result_dict_to_response, parse_rpc_transaction
from sol_parser.account_dispatcher import fill_accounts_with_owned_keys
from sol_parser.dex_parsers import parse_create_from_data
from sol_parser.event_types import DexEvent, PumpFunCreateEvent, PumpFunCreateV2TokenEvent
from sol_parser.grpc_types import EventType
from sol_parser.instructions import PUMPFUN_PROGRAM_ID

Z = '11111111111111111111111111111111'
V2 = bytes([214,144,76,236,95,139,49,180])
LEGACY = bytes([24,30,200,40,5,28,7,119])
FIXTURES = Path(os.environ.get('PUMPFUN_CREATE_CORPUS', Path(__file__).parent / 'fixtures/pumpfun_create'))

@pytest.mark.parametrize('path', sorted(FIXTURES.glob('*.json')), ids=lambda p: p.stem)
def test_mainnet_create_accounts(path):
    raw = json.loads(path.read_text())
    events, error = parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(raw), raw['transaction']['signatures'][0], None, 0)
    assert error is None
    if raw["meta"]["err"] is not None:
        assert events == []
        from sol_parser.rpc_parser import convert_rpc_to_grpc, rpc_response_to_solana_storage
        response = rpc_get_transaction_result_dict_to_response(raw)
        meta, _, error = convert_rpc_to_grpc(response)
        assert error is None and meta.HasField("err")
        _, meta = rpc_response_to_solana_storage(response)
        assert meta.HasField("err")
        return
    keys = raw['transaction']['message']['accountKeys'] + raw['meta']['loadedAddresses']['writable'] + raw['meta']['loadedAddresses']['readonly']
    creates = [e.data for e in events if e.type in (EventType.PUMP_FUN_CREATE, EventType.PUMP_FUN_CREATE_V2)]
    assert creates
    for c in creates:
        matches = [ix for ix in raw['transaction']['message']['instructions'] if keys[ix['programIdIndex']] == PUMPFUN_PROGRAM_ID and base58.b58decode(ix['data'])[:8] in (V2,LEGACY) and keys[ix['accounts'][0]] == c.mint]
        assert len(matches) == 1
        ix = matches[0]; v2 = base58.b58decode(ix['data'])[:8] == V2
        assert c.user == keys[ix['accounts'][5 if v2 else 7]]
        assert c.token_program == keys[ix['accounts'][7 if v2 else 9]]
        assert c.quote_mint in ('', Z, 'So11111111111111111111111111111111111111111')
        assert c.quote_vault in ('', Z)

@pytest.mark.parametrize('inner', [False, True])
@pytest.mark.parametrize('ambiguous', [False, True])
def test_create_selector_ignores_buy_and_other_mints(inner, ambiguous):
    keys = [bytes([i+1])*32 for i in range(40)]
    create = NS(data=V2, accounts=bytes(range(19)))
    unrelated = NS(data=V2, accounts=bytes([20]+list(range(1,16))))
    buy = NS(data=bytes([102,6,61,18,1,218,235,234]), accounts=bytes(range(30)))
    instructions = [create, unrelated, buy] + ([create] if ambiguous else [])
    tx = NS(message=NS(account_keys=keys, instructions=[] if inner else instructions))
    meta = NS(loaded_writable_addresses=[], loaded_readonly_addresses=[], inner_instructions=[NS(index=0, instructions=instructions)] if inner else [])
    invokes = {base58.b58decode(PUMPFUN_PROGRAM_ID): [(0,i) if inner else (i,-1) for i in range(len(instructions))]}
    c = PumpFunCreateV2TokenEvent(mint=base58.b58encode(keys[0]).decode(), quote_mint='decoded_quote', quote_vault='decoded_vault', quote_token_program='decoded_program')
    fill_accounts_with_owned_keys(DexEvent(type=EventType.PUMP_FUN_CREATE_V2, data=c), meta, tx, invokes)
    assert c.token_program == ('' if ambiguous else base58.b58encode(keys[7]).decode())
    assert (c.quote_mint,c.quote_vault,c.quote_token_program) == ('decoded_quote','decoded_vault','decoded_program')

def test_exact_historical_layout_and_truncation():
    strings = b''.join(struct.pack('<I',len(s))+s for s in (b'name', b'SYM', b'uri'))
    payload = strings + bytes([1])*32 + bytes([2])*32 + bytes([3])*32
    event = parse_create_from_data(payload,{})
    assert event.type == EventType.PUMP_FUN_CREATE
    assert event.data.timestamp == 0 and event.data.creator == ''
    for tail in (b'', b'\0', bytes(104)):
        invalid = payload[:-1] if not tail else payload+tail
        assert parse_create_from_data(invalid,{}).type != EventType.PUMP_FUN_CREATE

@pytest.mark.parametrize('payload', [b'', b'\x01'])
@pytest.mark.asyncio
async def test_grpc_failed_status_suppresses_instructions_and_callback_logs(payload):
    import asyncio
    from sol_parser import solana_storage_pb2 as pb
    from sol_parser.grpc_types import SubscribeUpdateTransactionInfo
    from sol_parser.grpc_client import YellowstoneGrpc
    from sol_parser.grpc_instruction_parser import parse_instructions_enhanced_from_subscribe_tx_info

    raw = json.loads(next(p for p in FIXTURES.glob('*.json') if p.stem.startswith('2Mfm')).read_text())
    tx = pb.Transaction()
    tx.message.account_keys.extend([base58.b58decode(k) for k in raw['transaction']['message']['accountKeys']])
    for ix in raw['transaction']['message']['instructions']:
        item = tx.message.instructions.add()
        item.program_id_index = ix['programIdIndex']
        item.accounts = bytes(ix['accounts'])
        item.data = base58.b58decode(ix['data'])
    meta = pb.TransactionStatusMeta(log_messages=raw['meta']['logMessages'])
    info = SubscribeUpdateTransactionInfo(transaction_raw=tx.SerializeToString(), meta_raw=meta.SerializeToString(), log_messages=raw['meta']['logMessages'])
    assert parse_instructions_enhanced_from_subscribe_tx_info(info, 1)
    meta.err.err = payload
    info.meta_raw = meta.SerializeToString()
    assert parse_instructions_enhanced_from_subscribe_tx_info(info, 1) == []
    queue = asyncio.Queue()
    client = YellowstoneGrpc('http://localhost:1')
    await client._enqueue_transaction_dex_events(queue, info, 1, None, 0, None)
    assert queue.empty()
