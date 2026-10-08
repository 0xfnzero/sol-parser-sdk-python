"""Log-only account enrichment from captured mainnet instruction contexts."""
import json
from pathlib import Path
import base58
import pytest
from sol_parser import solana_storage_pb2 as pb
from sol_parser.account_dispatcher import fill_accounts_with_owned_keys
from sol_parser.event_types import DexEvent, PumpSwapBuyEvent, PumpSwapSellEvent
from sol_parser.grpc_types import EventType

FIXTURE = json.loads((Path(__file__).parent / 'fixtures/pump_upgrade/account_context.json').read_text())

@pytest.mark.parametrize('case', FIXTURE['cases'], ids=lambda c: c['signature'][:12])
@pytest.mark.parametrize('inner', [False, True])
def test_mainnet_log_only_account_context(case, inner):
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
    for expected in case['events']:
        cls = PumpSwapBuyEvent if expected['buy'] else PumpSwapSellEvent
        kind = EventType.PUMP_SWAP_BUY if expected['buy'] else EventType.PUMP_SWAP_SELL
        event = DexEvent(kind, cls(pool=expected['pool'], user=expected['user']))
        fill_accounts_with_owned_keys(event, meta, tx, invokes)
        for field, key in expected['expected'].items():
            assert getattr(event.data, field) == key, field

@pytest.mark.parametrize('mode', ['duplicate', 'wrong_user', 'wrong_direction', 'truncated', 'foreign_instruction'])
def test_unmatched_or_ambiguous_context_stays_unresolved(mode):
    case = FIXTURE['cases'][0]
    expected = case['events'][0]
    i = case['instructions'][0]
    tx, meta = pb.Transaction(), pb.TransactionStatusMeta()
    tx.message.account_keys.extend(base58.b58decode(k) for k in case['keys'])
    data = bytes.fromhex(i['data']) if mode != 'foreign_instruction' else bytes(24)
    accounts = bytes(i['accounts'][:-1] if mode == 'truncated' else i['accounts'])
    tx.message.instructions.add(accounts=accounts, data=data)
    indices = [(0, -1)]
    if mode == 'duplicate':
        tx.message.instructions.add(accounts=accounts, data=data)
        indices.append((1, -1))
    user = case['keys'][0] if mode == 'wrong_user' else expected['user']
    cls = PumpSwapSellEvent if mode == 'wrong_direction' else PumpSwapBuyEvent
    kind = EventType.PUMP_SWAP_SELL if mode == 'wrong_direction' else EventType.PUMP_SWAP_BUY
    event = DexEvent(kind, cls(pool=expected['pool'], user=user))
    before = event.data.user_base_token_account
    fill_accounts_with_owned_keys(event, meta, tx, {base58.b58decode(FIXTURE['program']): indices})
    assert event.data.user_base_token_account == before
