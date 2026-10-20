"""Explicit Shred rule opt-in; no network access. Load reviewed rules at startup."""
import base58
from .event_types import DexEvent, PumpFunTradeEvent
from .grpc_types import EventType
from .instructions import parse_instruction_unified, PUMPFUN_PROGRAM_ID

def _key(value):
    return value if isinstance(value, str) else base58.b58encode(bytes(value)).decode()

def parse_wrapped_pumpfun_instruction(raw, rule, filter=None):
    """Return PumpFunTrade input intent or None, retaining RawInstruction on miss.

    rule is the JSON candidate emitted by the Rust offline analyzer. Explicitly
    validate independent transactions before opting in; it cannot detect upgrades.
    """
    if filter is not None and not filter.should_include(EventType.PUMP_FUN_TRADE):
        return None
    data, accounts = raw.instruction_data, raw.accounts
    pattern = rule['data_pattern']
    if (raw.program_id != _key(rule['program_id']) or len(accounts) != rule['outer_account_count']
        or any(k is None for k in accounts) or len(data) != len(pattern)
        or not any(v is not None for v in pattern)
        or any(v is not None and v != data[i] for i, v in enumerate(pattern))):
        return None
    disc = bytes(rule['pump_discriminator'])
    if disc not in (bytes([184,23,238,97,103,197,211,61]), bytes([194,171,28,70,104,77,91,47]), bytes([93,246,130,60,231,233,64,178])):
        return None
    valid = lambda i: isinstance(i, int) and 0 <= i < len(accounts)
    if (any(not valid(i) or accounts[i] != _key(k) for i, k in rule['fixed_accounts'])
        or any(not valid(a) or not valid(b) or accounts[a] != accounts[b] for a, b in rule['equal_accounts'])
        or any(not valid(i) for i in rule['account_map'])):
        return None
    offsets = rule['argument_offsets']
    if len(offsets) != 2 or any(not isinstance(i, int) or i < 0 or i + 8 > len(data) for i in offsets):
        return None
    restored = disc + b''.join(bytes(data[i:i+8]) for i in offsets)
    m = raw.metadata
    event = parse_instruction_unified(restored, [accounts[i] for i in rule['account_map']],
        m.signature, m.slot, m.tx_index, m.block_time_us, m.grpc_recv_us, None, PUMPFUN_PROGRAM_ID)
    if event is None or not isinstance(event.data, PumpFunTradeEvent):
        return None
    trade = event.data
    trade.metadata = m
    trade.sol_amount = trade.quote_amount = trade.token_amount = 0
    from .trade_source import RawInstructionPayload, TradeParseStatus
    trade.third_program = RawInstructionPayload.from_raw(raw)
    trade.third_program.rule_id = rule['rule_id']
    trade.parse_status = TradeParseStatus.INSTRUCTION_DECODED
    return DexEvent(EventType.PUMP_FUN_TRADE, trade)
