"""对齐 Rust ``accounts/utils.rs`` 的通用工具。"""

from __future__ import annotations

import struct
from typing import Optional

# Solana 系统程序、SPL Token / Token-2022（与 Rust 一致）
SYSTEM_PROGRAM_ID = "11111111111111111111111111111111"
SPL_TOKEN_PROGRAM_ID = "TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA"
SPL_TOKEN_2022_PROGRAM_ID = "TokenzQdBNbLqP5VEhdkAS6EPFLC1PHnBqCXEpPxuEb"

SPL_TOKEN_ACCOUNT_LEN = 165


def read_pubkey(data: bytes, offset: int) -> Optional[str]:
    """32 字节 → base58；越界返回 None。"""
    import base58

    if len(data) < offset + 32:
        return None
    return base58.b58encode(data[offset : offset + 32]).decode("ascii")


def read_u64_le(data: bytes, offset: int) -> Optional[int]:
    if len(data) < offset + 8:
        return None
    return struct.unpack_from("<Q", data, offset)[0]


def read_u16_le(data: bytes, offset: int) -> Optional[int]:
    if len(data) < offset + 2:
        return None
    return struct.unpack_from("<H", data, offset)[0]


def read_u8(data: bytes, offset: int) -> Optional[int]:
    if offset >= len(data):
        return None
    return data[offset]


def is_nonce_account(data: bytes) -> bool:
    return len(data) >= 8 and data[:8] == bytes([1, 0, 0, 0, 1, 0, 0, 0])


def is_token_program_account(owner: str) -> bool:
    return owner in (SPL_TOKEN_PROGRAM_ID, SPL_TOKEN_2022_PROGRAM_ID)


def has_discriminator(data: bytes, discriminator: bytes) -> bool:
    if len(data) < len(discriminator):
        return False
    return data[: len(discriminator)] == discriminator


def user_wallet_pubkey_for_onchain_account(
    address: str,
    owner: str,
    data: bytes,
    executable: bool,
) -> Optional[str]:
    """对齐 Rust ``user_wallet_pubkey_for_onchain_account``：系统钱包或 SPL token 账户 owner。"""
    if executable:
        return None
    if owner == SYSTEM_PROGRAM_ID:
        return address if len(data) == 0 else None
    if is_token_program_account(owner) and len(data) == SPL_TOKEN_ACCOUNT_LEN:
        # spl_token::state::Account: owner at offset 32
        return read_pubkey(data, 32)
    return None
