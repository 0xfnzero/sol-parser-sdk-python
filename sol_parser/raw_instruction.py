"""Lossless outer instructions, without inferred CPI or trade semantics."""
from dataclasses import dataclass, field
from typing import Optional
from .event_types import DexEventBase

INFRASTRUCTURE_PROGRAMS = frozenset(["11111111111111111111111111111111","TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA","TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb","ATokenGPvbdGVxr1b2hvZbsiqW5xWH25efTNsLJA8knL","ComputeBudget111111111111111111111111111111","MemoSq4gqABAXKb96qnH8TysNcWxMyWCqXgDLGmfcHr","Memo1UhkJRfHyvLMcVucJwxXeuD728EqVDDwQDxFMNo","AddressLookupTab1e1111111111111111111111111","Vote111111111111111111111111111111111111111","Ed25519SigVerify111111111111111111111111111","KeccakSecp256k11111111111111111111111111111","Secp256r1SigVerify1111111111111111111111111"])

@dataclass
class RawInstructionEvent(DexEventBase):
    program_id: str = ''
    instruction_index: int = 0
    # Original order including duplicates. None denotes an unresolved ALT key.
    accounts: list[Optional[str]] = field(default_factory=list)
    account_indices: list[int] = field(default_factory=list)
    instruction_data: list[int] = field(default_factory=list)
