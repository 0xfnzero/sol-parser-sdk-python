"""对齐 Rust ``instr/utils::get_instruction_account_getter``：从 meta + transaction 解析某条指令的账户 getter。"""

from __future__ import annotations

from typing import Any, Callable, List, Optional, Tuple

import base58


def _read_pk(raw: Optional[bytes]) -> str:
    if raw is None or len(raw) != 32:
        return "11111111111111111111111111111111"
    return base58.b58encode(raw).decode("ascii")


def get_instruction_account_getter(
    meta_pb: Any,
    transaction_pb: Any,
    account_keys: Optional[List[bytes]],
    loaded_writable_addresses: List[bytes],
    loaded_readonly_addresses: List[bytes],
    index: Tuple[int, int],
) -> Optional[Callable[[int], str]]:
    """``index`` 为 ``(outer_index, inner_index)``，inner 为 ``-1`` 表示外层指令。"""
    outer_i, inner_i = index
    accounts_idx: bytes
    if inner_i >= 0:
        grp = None
        for inn in meta_pb.inner_instructions:
            if int(inn.index) == int(outer_i):
                grp = inn
                break
        if grp is None or inner_i >= len(grp.instructions):
            return None
        accounts_idx = bytes(grp.instructions[inner_i].accounts)
    else:
        msg = transaction_pb.message
        if outer_i >= len(msg.instructions):
            return None
        accounts_idx = bytes(msg.instructions[outer_i].accounts)

    keys = account_keys or []

    def getter(acc_i: int) -> str:
        if acc_i >= len(accounts_idx):
            return "11111111111111111111111111111111"
        ai = accounts_idx[acc_i]
        if ai < len(keys):
            return _read_pk(bytes(keys[ai]))
        j = ai - len(keys)
        if j < len(loaded_writable_addresses):
            return _read_pk(bytes(loaded_writable_addresses[j]))
        j2 = j - len(loaded_writable_addresses)
        if j2 < len(loaded_readonly_addresses):
            return _read_pk(bytes(loaded_readonly_addresses[j2]))
        return "11111111111111111111111111111111"

    return getter
