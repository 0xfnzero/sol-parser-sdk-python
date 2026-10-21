"""Trade evidence and lossless router input. No network access or inferred amounts."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class TradeParseStatus(str, Enum):
    UNRESOLVED = "Unresolved"
    INSTRUCTION_DECODED = "InstructionDecoded"
    EXECUTION_CONFIRMED = "ExecutionConfirmed"


@dataclass
class RawInstructionPayload:
    program_id: str
    instruction_index: int
    accounts: list[Optional[str]] = field(default_factory=list)
    account_indices: list[int] = field(default_factory=list)
    instruction_data: list[int] = field(default_factory=list)

    def __getitem__(self, key):
        """Compatibility with the former dictionary-shaped third_program."""
        return getattr(self, key)


def native_trade_program(event):
    from .raw_instruction import _DEX_PROGRAMS
    from . import instructions

    name = event.type.value
    if name in ("PumpFunBuy", "PumpFunSell", "PumpFunBuyExactSolIn"):
        name = "PumpFunTrade"
    if name in ("PumpSwapBuy", "PumpSwapSell"):
        name = "PumpSwapTrade"
    return next(
        (
            getattr(instructions, program)
            for _, program, trade in _DEX_PROGRAMS
            if trade == name
        ),
        None,
    )


def mark_execution_source(event, outer_index, msg, meta):
    """Uses the exact compiled instruction index; never joins on user/mint."""
    native = native_trade_program(event)
    if native is None or meta.HasField("err"):
        return
    event.data.parse_status = TradeParseStatus.EXECUTION_CONFIRMED
    if not 0 <= outer_index < len(msg.instructions):
        return
    import base58

    keys = [
        *msg.account_keys,
        *meta.loaded_writable_addresses,
        *meta.loaded_readonly_addresses,
    ]

    def key(index):
        return (
            base58.b58encode(bytes(keys[index])).decode()
            if 0 <= index < len(keys) and len(keys[index]) == 32
            else None
        )

    ix = msg.instructions[outer_index]
    program = key(ix.program_id_index)
    name = event.type.value
    if name in ("RaydiumClmmSwap", "OrcaWhirlpoolSwap"):
        clmm = name == "RaydiumClmmSwap"
        candidates = [ix] + [
            inner
            for group in meta.inner_instructions
            if group.index == outer_index
            for inner in group.instructions
        ]
        pairs = set()
        for candidate in candidates:
            if key(candidate.program_id_index) != native or bytes(
                candidate.data[:8]
            ) != bytes([43, 4, 237, 11, 26, 201, 30, 98]):
                continue
            get = lambda i: (
                key(candidate.accounts[i]) if i < len(candidate.accounts) else None
            )
            if get(2 if clmm else 4) != (
                event.data.pool_state if clmm else event.data.whirlpool
            ):
                continue
            a, b = get(11 if clmm else 5), get(12 if clmm else 6)
            if a and b:
                pairs.add((a, b))
        if len(pairs) == 1:
            a, b = next(iter(pairs))
            if clmm:
                event.data.input_mint, event.data.output_mint = a, b
            else:
                event.data.token_mint_a, event.data.token_mint_b = a, b
    if program and program != native:
        event.data.third_program = RawInstructionPayload(
            program,
            outer_index,
            [key(i) for i in ix.accounts],
            list(ix.accounts),
            list(ix.data),
        )


def log_outer_indices(logs, programs):
    """Reject ambiguous ordinal mapping after truncated/missing invocations."""
    import re
    from collections import Counter, defaultdict

    positions = defaultdict(list)
    for i, program in enumerate(programs):
        positions[program].append(i)
    invocations = [re.fullmatch(r"Program (\S+) invoke \[1\]", line) for line in logs]
    counts = Counter(m[1] for m in invocations if m)
    used = Counter()
    current = -1
    result = []
    for match in invocations:
        if match:
            program = match[1]
            current = (
                positions[program][used[program]]
                if counts[program] == len(positions[program])
                else -1
            )
            used[program] += 1
        result.append(current)
    return result
