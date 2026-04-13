"""账户解析器 — 对齐 Rust ``accounts`` 模块（含 ``utils`` / ``rpc_wallet`` 子模块）。"""

from __future__ import annotations

import struct
from typing import Optional
from dataclasses import dataclass

import base58

from ..grpc_types import EventTypeFilter, EventType, EventMetadata
from ..dex_parsers import DexEvent

from . import rpc_wallet
from . import utils as acc_utils

# 程序 ID（与 Rust ``accounts/program_ids`` / ``instr/program_ids`` 一致）
PUMPSWAP_PROGRAM_ID = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"

_DISC_GLOBAL_CONFIG = bytes([149, 8, 156, 202, 160, 252, 176, 217])
_DISC_POOL = bytes([241, 154, 109, 4, 17, 177, 109, 188])
_DISC_NONCE = bytes([1, 0, 0, 0, 1, 0, 0, 0])

MINT_SIZE = 82
TOKEN_ACCOUNT_SIZE = 165
NONCE_ACCOUNT_SIZE = 80
GLOBAL_CONFIG_BODY = 634
POOL_BODY = 244

SUPPLY_OFFSET = 36
DECIMALS_OFFSET = 44
AMOUNT_OFFSET = 64
NONCE_AUTHORITY_OFFSET = 8
NONCE_NONCE_OFFSET = 40

EMPTY_PUBKEY = ""


@dataclass
class AccountData:
    pubkey: str
    executable: bool
    lamports: int
    owner: str
    rent_epoch: int
    data: bytes


def has_discriminator(data: bytes, discriminator: bytes) -> bool:
    return acc_utils.has_discriminator(data, discriminator)


def base58_encode_32(data: bytes) -> str:
    return base58.b58encode(data).decode("ascii")


def read_pubkey_fast(data: bytes, offset: int) -> str:
    if offset + 32 > len(data):
        return EMPTY_PUBKEY
    return base58.b58encode(data[offset : offset + 32]).decode("ascii")


def read_u64_fast(data: bytes, offset: int) -> int:
    return struct.unpack_from("<Q", data, offset)[0]


def read_u16_fast(data: bytes, offset: int) -> int:
    return struct.unpack_from("<H", data, offset)[0]


def parse_account_unified(
    account: AccountData,
    metadata: EventMetadata,
    event_type_filter: Optional[EventTypeFilter] = None,
) -> Optional[DexEvent]:
    """对齐 Rust ``parse_account_unified``（含 ``Option<EventTypeFilter>`` 语义）。"""
    data = account.data
    if not data:
        return None

    if event_type_filter is not None:
        inc = getattr(event_type_filter, "include_only", None)
        if inc is not None and len(inc) > 0:
            need = {
                EventType.TOKEN_ACCOUNT,
                EventType.TOKEN_INFO,
                EventType.NONCE_ACCOUNT,
                EventType.ACCOUNT_PUMP_SWAP_GLOBAL_CONFIG,
                EventType.ACCOUNT_PUMP_SWAP_POOL,
            }
            if not any(t in need for t in inc):
                return None

    if account.owner == PUMPSWAP_PROGRAM_ID and event_type_filter is not None:
        if event_type_filter.should_include(
            EventType.ACCOUNT_PUMP_SWAP_GLOBAL_CONFIG
        ) or event_type_filter.should_include(EventType.ACCOUNT_PUMP_SWAP_POOL):
            ev = _parse_pumpswap_account(account, metadata)
            if ev is not None:
                return ev

    if acc_utils.is_nonce_account(data):
        if event_type_filter is not None:
            if not event_type_filter.should_include(EventType.NONCE_ACCOUNT):
                return None
        return _parse_nonce_fast(account, metadata)

    if event_type_filter is not None:
        if not event_type_filter.should_include(EventType.TOKEN_ACCOUNT):
            return None
    return parse_token_account(account, metadata)


def _parse_pumpswap_account(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    if acc_utils.has_discriminator(account.data, _DISC_GLOBAL_CONFIG):
        return parse_pumpswap_global_config(account, metadata)
    if acc_utils.has_discriminator(account.data, _DISC_POOL):
        return parse_pumpswap_pool(account, metadata)
    return None


def _parse_mint_fast(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    data = account.data
    return {
        "TokenInfo": {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "executable": account.executable,
            "lamports": account.lamports,
            "owner": account.owner,
            "rent_epoch": account.rent_epoch,
            "supply": struct.unpack_from("<Q", data, SUPPLY_OFFSET)[0],
            "decimals": data[DECIMALS_OFFSET],
        }
    }


def _parse_token_fast(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    data = account.data
    return {
        "TokenAccount": {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "executable": account.executable,
            "lamports": account.lamports,
            "owner": account.owner,
            "rent_epoch": account.rent_epoch,
            "amount": struct.unpack_from("<Q", data, AMOUNT_OFFSET)[0],
        }
    }


def _parse_nonce_fast(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    data = account.data
    authority = base58_encode_32(data[NONCE_AUTHORITY_OFFSET : NONCE_AUTHORITY_OFFSET + 32])
    nonce = base58_encode_32(data[NONCE_NONCE_OFFSET : NONCE_NONCE_OFFSET + 32])
    return {
        "NonceAccount": {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "executable": account.executable,
            "lamports": account.lamports,
            "owner": account.owner,
            "rent_epoch": account.rent_epoch,
            "nonce": nonce,
            "authority": authority,
        }
    }


def _parse_pumpswap_global_config_fast(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    data = account.data[8:]
    o = 0
    admin = read_pubkey_fast(data, o)
    o += 32
    lp_fee = read_u64_fast(data, o)
    o += 8
    protocol_fee = read_u64_fast(data, o)
    o += 8
    disable_flags = data[o]
    o += 1
    recipients = [
        read_pubkey_fast(data, o),
        read_pubkey_fast(data, o + 32),
        read_pubkey_fast(data, o + 64),
        read_pubkey_fast(data, o + 96),
        read_pubkey_fast(data, o + 128),
        read_pubkey_fast(data, o + 160),
        read_pubkey_fast(data, o + 192),
        read_pubkey_fast(data, o + 224),
    ]
    o += 256
    coin_creator_fee = read_u64_fast(data, o)
    o += 8
    admin_auth = read_pubkey_fast(data, o)
    o += 32
    whitelist = read_pubkey_fast(data, o)
    o += 32
    reserved = read_pubkey_fast(data, o)
    o += 32
    mayhem = data[o] != 0
    o += 1
    reserved_list = [
        read_pubkey_fast(data, o),
        read_pubkey_fast(data, o + 32),
        read_pubkey_fast(data, o + 64),
        read_pubkey_fast(data, o + 96),
        read_pubkey_fast(data, o + 128),
        read_pubkey_fast(data, o + 160),
        read_pubkey_fast(data, o + 192),
    ]
    return {
        "PumpSwapGlobalConfigAccount": {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "config": {
                "admin": admin,
                "lp_fee_basis_points": lp_fee,
                "protocol_fee_basis_points": protocol_fee,
                "disable_flags": disable_flags,
                "protocol_fee_recipients": recipients,
                "coin_creator_fee_basis_points": coin_creator_fee,
                "admin_set_coin_creator_authority": admin_auth,
                "whitelist_pda": whitelist,
                "reserved_fee_recipient": reserved,
                "mayhem_mode_enabled": mayhem,
                "reserved_fee_recipients": reserved_list,
            },
        }
    }


def _parse_pumpswap_pool_fast(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    data = account.data[8:]
    o = 0
    pool_bump = data[o]
    o += 1
    index = read_u16_fast(data, o)
    o += 2
    creator = read_pubkey_fast(data, o)
    base_mint = read_pubkey_fast(data, o + 32)
    quote_mint = read_pubkey_fast(data, o + 64)
    lp_mint = read_pubkey_fast(data, o + 96)
    pool_base = read_pubkey_fast(data, o + 128)
    pool_quote = read_pubkey_fast(data, o + 160)
    o += 192
    lp_supply = read_u64_fast(data, o)
    o += 8
    coin_creator = read_pubkey_fast(data, o)
    o += 32
    is_mayhem = data[o] != 0
    is_cashback = data[o + 1] != 0
    return {
        "PumpSwapPoolAccount": {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "pool": {
                "pool_bump": pool_bump,
                "index": index,
                "creator": creator,
                "base_mint": base_mint,
                "quote_mint": quote_mint,
                "lp_mint": lp_mint,
                "pool_base_token_account": pool_base,
                "pool_quote_token_account": pool_quote,
                "lp_supply": lp_supply,
                "coin_creator": coin_creator,
                "is_mayhem_mode": is_mayhem,
                "is_cashback_coin": is_cashback,
            },
        }
    }


def parse_token_account(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    if len(account.data) <= 100:
        event = _parse_mint_fast(account, metadata)
        if event:
            return event
    return _parse_token_fast(account, metadata)


def parse_nonce_account(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    if len(account.data) != NONCE_ACCOUNT_SIZE:
        return None
    if not has_discriminator(account.data, _DISC_NONCE):
        return None
    return _parse_nonce_fast(account, metadata)


def is_nonce_account(data: bytes) -> bool:
    return acc_utils.is_nonce_account(data)


def parse_pumpswap_global_config(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    if len(account.data) < 8 + GLOBAL_CONFIG_BODY:
        return None
    if not has_discriminator(account.data, _DISC_GLOBAL_CONFIG):
        return None
    return _parse_pumpswap_global_config_fast(account, metadata)


def parse_pumpswap_pool(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    if len(account.data) < 8 + POOL_BODY:
        return None
    if not has_discriminator(account.data, _DISC_POOL):
        return None
    return _parse_pumpswap_pool_fast(account, metadata)


def is_global_config_account(data: bytes) -> bool:
    return has_discriminator(data, _DISC_GLOBAL_CONFIG)


def is_pool_account(data: bytes) -> bool:
    return has_discriminator(data, _DISC_POOL)


base58_encode = base58_encode_32
read_pubkey = read_pubkey_fast
read_u64_le = read_u64_fast
read_u8 = lambda data, offset: data[offset] if offset < len(data) else 0

rpc_resolve_user_wallet_pubkey = rpc_wallet.rpc_resolve_user_wallet_pubkey
user_wallet_pubkey_for_onchain_account = acc_utils.user_wallet_pubkey_for_onchain_account

__all__ = [
    "AccountData",
    "parse_account_unified",
    "parse_token_account",
    "parse_nonce_account",
    "is_nonce_account",
    "parse_pumpswap_global_config",
    "parse_pumpswap_pool",
    "is_global_config_account",
    "is_pool_account",
    "has_discriminator",
    "PUMPSWAP_PROGRAM_ID",
    "rpc_resolve_user_wallet_pubkey",
    "user_wallet_pubkey_for_onchain_account",
    "rpc_wallet",
    "acc_utils",
]
