"""Log-only account enrichment from captured mainnet instruction contexts."""
import json
from pathlib import Path
import base58
import pytest
from sol_parser import solana_storage_pb2 as pb
from sol_parser.account_dispatcher import fill_accounts_with_owned_keys
from sol_parser.event_types import DexEvent, PumpFunTradeEvent
from sol_parser.grpc_types import EventType

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/pump_upgrade/pump_trade_account_context.json').read_text())

@pytest.mark.parametrize('case', FIXTURE['cases'], ids=lambda c: c['name'])
@pytest.mark.parametrize('inner', [False, True])
def test_log_only_account_context(case, inner):
    tx, meta = pb.Transaction(), pb.TransactionStatusMeta()
    tx.message.account_keys.extend(base58.b58decode(k) for k in case['keys'])
    instructions = []
    for ix in case['instructions']:
        instructions.append(pb.CompiledInstruction(program_id_index=case['keys'].index(FIXTURE['program']), accounts=bytes(ix['accounts']), data=bytes.fromhex(ix['data'])))
    if inner:
        group = meta.inner_instructions.add(index=0)
        for ix in instructions:
            group.instructions.add(program_id_index=ix.program_id_index, accounts=ix.accounts, data=ix.data)
        indices = [(0, i) for i in range(len(instructions))]
    else:
        tx.message.instructions.extend(instructions)
        indices = [(i, -1) for i in range(len(instructions))]
    invokes = {base58.b58decode(FIXTURE['program']): indices}
    event = DexEvent(EventType.PUMP_FUN_TRADE, PumpFunTradeEvent(mint=case['mint'], user=case['user'], is_buy=case['buy']))
    fill_accounts_with_owned_keys(event, meta, tx, invokes)
    for field, key in case['expected'].items():
        assert getattr(event.data, field) == key, (case['name'], field)

@pytest.mark.parametrize('case', FIXTURE['cases'], ids=lambda c: c['name'])
@pytest.mark.parametrize('mode', ['duplicate', 'wrong_mint', 'wrong_user', 'wrong_direction', 'truncated', 'foreign_instruction'])
def test_unmatched_context_is_not_filled(case, mode):
    tx, meta = pb.Transaction(), pb.TransactionStatusMeta()
    tx.message.account_keys.extend(base58.b58decode(k) for k in case['keys'])
    ix = case['instructions'][0]
    accounts = bytes(ix['accounts'][:-1] if mode == 'truncated' else ix['accounts'])
    data = bytes(24) if mode == 'foreign_instruction' else bytes.fromhex(ix['data'])
    tx.message.instructions.add(accounts=accounts, data=data)
    indices = [(0, -1)]
    if mode == 'duplicate':
        tx.message.instructions.add(accounts=accounts, data=data)
        indices.append((1, -1))
    event = DexEvent(EventType.PUMP_FUN_TRADE, PumpFunTradeEvent(
        mint=case['keys'][-2] if mode == 'wrong_mint' else case['mint'],
        user=case['keys'][-2] if mode == 'wrong_user' else case['user'],
        is_buy=not case['buy'] if mode == 'wrong_direction' else case['buy']))
    fill_accounts_with_owned_keys(event, meta, tx, {base58.b58decode(FIXTURE['program']): indices})
    assert event.data.associated_user == ''
