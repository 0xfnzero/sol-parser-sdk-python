"""账户解析器 - 对齐 Rust 实现"""

from __future__ import annotations

import struct
from typing import Optional, List
from dataclasses import dataclass

from .grpc_types import EventTypeFilter, EventType, EventMetadata
from .dex_parsers import DexEvent


@dataclass
class AccountData:
    """账户数据结构"""
    pubkey: str
    executable: bool
    lamports: int
    owner: str
    rent_epoch: int
    data: bytes


def parse_account_unified(
    account: AccountData,
    metadata: EventMetadata,
    filter: EventTypeFilter
) -> Optional[DexEvent]:
    """统一的账户解析入口
    
    对齐 Rust `parse_account_unified`
    """
    if not account.data:
        return None

    # Early filtering based on event type filter
    if filter.include_only:
        should_parse = any(
            t in [
                EventType.TOKEN_ACCOUNT,
                EventType.TOKEN_INFO,
                EventType.NONCE_ACCOUNT,
                EventType.ACCOUNT_PUMP_SWAP_GLOBAL_CONFIG,
                EventType.ACCOUNT_PUMP_SWAP_POOL,
            ]
            for t in filter.include_only
        )
        if not should_parse:
            return None

    # PumpSwap 账户解析
    if account.owner == PUMPSWAP_PROGRAM_ID:
        if filter.should_include(EventType.ACCOUNT_PUMP_SWAP_GLOBAL_CONFIG) or \
           filter.should_include(EventType.ACCOUNT_PUMP_SWAP_POOL):
            event = _parse_pumpswap_account(account, metadata)
            if event:
                return event

    # Nonce 账户解析
    if is_nonce_account(account.data):
        if not filter.should_include(EventType.NONCE_ACCOUNT):
            return None
        return parse_nonce_account(account, metadata)

    # Token 账户解析
    if not filter.should_include(EventType.TOKEN_ACCOUNT) and not filter.should_include(EventType.TOKEN_INFO):
        return None
    return parse_token_account(account, metadata)


def parse_token_account(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    """解析 Token 账户
    
    对齐 Rust `parse_token_account`
    """
    # 快速路径：尝试解析 Mint 账户
    if len(account.data) <= 100:
        event = _parse_mint_fast(account, metadata)
        if event:
            return event

    # 快速路径：尝试解析 Token Account
    event = _parse_token_fast(account, metadata)
    if event:
        return event

    return None


def _parse_mint_fast(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    """快速解析 Mint 账户（零拷贝）"""
    MINT_SIZE = 82
    SUPPLY_OFFSET = 36
    DECIMALS_OFFSET = 44

    if len(account.data) < MINT_SIZE:
        return None

    supply = struct.unpack_from("<Q", account.data, SUPPLY_OFFSET)[0]
    decimals = account.data[DECIMALS_OFFSET]

    return {
        "TokenInfo": {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "executable": account.executable,
            "lamports": account.lamports,
            "owner": account.owner,
            "rent_epoch": account.rent_epoch,
            "supply": supply,
            "decimals": decimals,
        }
    }


def _parse_token_fast(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    """快速解析 Token Account（零拷贝）"""
    TOKEN_ACCOUNT_SIZE = 165
    AMOUNT_OFFSET = 64

    if len(account.data) < TOKEN_ACCOUNT_SIZE:
        return None

    amount = struct.unpack_from("<Q", account.data, AMOUNT_OFFSET)[0]

    return {
        "TokenAccount": {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "executable": account.executable,
            "lamports": account.lamports,
            "owner": account.owner,
            "rent_epoch": account.rent_epoch,
            "amount": amount,
        }
    }


def parse_nonce_account(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    """解析 Nonce 账户
    
    对齐 Rust `parse_nonce_account`
    """
    NONCE_ACCOUNT_SIZE = 80
    AUTHORITY_OFFSET = 8
    NONCE_OFFSET = 40

    if len(account.data) != NONCE_ACCOUNT_SIZE:
        return None

    # Extract authority (32 bytes at offset 8)
    authority_bytes = account.data[AUTHORITY_OFFSET:AUTHORITY_OFFSET + 32]
    authority = base58_encode(authority_bytes)

    # Extract nonce/blockhash (32 bytes at offset 40)
    nonce_bytes = account.data[NONCE_OFFSET:NONCE_OFFSET + 32]
    nonce = base58_encode(nonce_bytes)

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


def is_nonce_account(data: bytes) -> bool:
    """检测是否为 Nonce 账户
    
    对齐 Rust `is_nonce_account`
    """
    if len(data) < 8:
        return False
    discriminator = bytes([1, 0, 0, 0, 1, 0, 0, 0])
    return data[:8] == discriminator


def parse_pumpswap_global_config(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    """解析 PumpSwap Global Config 账户
    
    对齐 Rust `parse_pumpswap_global_config`
    """
    GLOBAL_CONFIG_SIZE = 32 + 8 + 8 + 1 + 32 * 8 + 8 + 32

    if len(account.data) < GLOBAL_CONFIG_SIZE + 8:
        return None

    # Check discriminator
    global_config_disc = bytes([149, 8, 156, 202, 160, 252, 176, 217])
    if not has_discriminator(account.data, global_config_disc):
        return None

    data = account.data[8:]
    offset = 0

    admin = read_pubkey(data, offset)
    offset += 32

    lp_fee_basis_points = struct.unpack_from("<Q", data, offset)[0]
    offset += 8

    protocol_fee_basis_points = struct.unpack_from("<Q", data, offset)[0]
    offset += 8

    disable_flags = data[offset]
    offset += 1

    # Read 8 protocol_fee_recipients
    protocol_fee_recipients = []
    for _ in range(8):
        protocol_fee_recipients.append(read_pubkey(data, offset))
        offset += 32

    coin_creator_fee_basis_points = struct.unpack_from("<Q", data, offset)[0]
    offset += 8

    admin_set_coin_creator_authority = read_pubkey(data, offset)
    offset += 32

    whitelist_pda = read_pubkey(data, offset)
    offset += 32

    reserved_fee_recipient = read_pubkey(data, offset)
    offset += 32

    mayhem_mode_enabled = data[offset] != 0
    offset += 1

    # Read 7 reserved_fee_recipients
    reserved_fee_recipients = []
    for _ in range(7):
        reserved_fee_recipients.append(read_pubkey(data, offset))
        offset += 32

    return {
        "PumpSwapGlobalConfigAccount": {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "config": {
                "admin": admin,
                "lp_fee_basis_points": lp_fee_basis_points,
                "protocol_fee_basis_points": protocol_fee_basis_points,
                "disable_flags": disable_flags,
                "protocol_fee_recipients": protocol_fee_recipients,
                "coin_creator_fee_basis_points": coin_creator_fee_basis_points,
                "admin_set_coin_creator_authority": admin_set_coin_creator_authority,
                "whitelist_pda": whitelist_pda,
                "reserved_fee_recipient": reserved_fee_recipient,
                "mayhem_mode_enabled": mayhem_mode_enabled,
                "reserved_fee_recipients": reserved_fee_recipients,
            }
        }
    }


def parse_pumpswap_pool(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    """解析 PumpSwap Pool 账户
    
    对齐 Rust `parse_pumpswap_pool`
    """
    POOL_SIZE = 244

    if len(account.data) < POOL_SIZE + 8:
        return None

    # Check discriminator
    pool_disc = bytes([241, 154, 109, 4, 17, 177, 109, 188])
    if not has_discriminator(account.data, pool_disc):
        return None

    data = account.data[8:]
    offset = 0

    pool_bump = data[offset]
    offset += 1

    index = struct.unpack_from("<H", data, offset)[0]
    offset += 2

    # Read 6 pubkeys
    mint_a = read_pubkey(data, offset)
    offset += 32
    mint_b = read_pubkey(data, offset)
    offset += 32
    lp_mint = read_pubkey(data, offset)
    offset += 32
    pool_authority = read_pubkey(data, offset)
    offset += 32
    pool_token_a = read_pubkey(data, offset)
    offset += 32
    pool_token_b = read_pubkey(data, offset)
    offset += 32

    lp_supply = struct.unpack_from("<Q", data, offset)[0]
    offset += 8

    coin_creator = read_pubkey(data, offset)
    offset += 32

    is_mayhem_mode = data[offset] != 0
    offset += 1

    is_cashback_coin = data[offset] != 0
    offset += 1

    return {
        "PumpSwapPoolAccount": {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "pool": {
                "pool_bump": pool_bump,
                "index": index,
                "mint_a": mint_a,
                "mint_b": mint_b,
                "lp_mint": lp_mint,
                "pool_authority": pool_authority,
                "pool_token_a": pool_token_a,
                "pool_token_b": pool_token_b,
                "lp_supply": lp_supply,
                "coin_creator": coin_creator,
                "is_mayhem_mode": is_mayhem_mode,
                "is_cashback_coin": is_cashback_coin,
            }
        }
    }


def _parse_pumpswap_account(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    """解析 PumpSwap 账户（内部函数）"""
    # Check Global Config discriminator
    global_config_disc = bytes([149, 8, 156, 202, 160, 252, 176, 217])
    if has_discriminator(account.data, global_config_disc):
        return parse_pumpswap_global_config(account, metadata)

    # Check Pool discriminator
    pool_disc = bytes([241, 154, 109, 4, 17, 177, 109, 188])
    if has_discriminator(account.data, pool_disc):
        return parse_pumpswap_pool(account, metadata)

    return None


def is_global_config_account(data: bytes) -> bool:
    """检查是否为 Global Config 账户"""
    global_config_disc = bytes([149, 8, 156, 202, 160, 252, 176, 217])
    return has_discriminator(data, global_config_disc)


def is_pool_account(data: bytes) -> bool:
    """检查是否为 Pool 账户"""
    pool_disc = bytes([241, 154, 109, 4, 17, 177, 109, 188])
    return has_discriminator(data, pool_disc)


def has_discriminator(data: bytes, discriminator: bytes) -> bool:
    """检查是否有指定的 discriminator"""
    if len(data) < len(discriminator):
        return False
    return data[:len(discriminator)] == discriminator


def base58_encode(data: bytes) -> str:
    """将字节编码为 Base58 字符串"""
    import base58
    return base58.b58encode(data).decode('ascii')


def read_pubkey(data: bytes, offset: int) -> str:
    """从字节数组读取公钥（32字节）"""
    if offset + 32 > len(data):
        return ""
    return base58_encode(data[offset:offset + 32])


def read_u64_le(data: bytes, offset: int) -> int:
    """读取小端序 uint64"""
    if offset + 8 > len(data):
        return 0
    return struct.unpack_from("<Q", data, offset)[0]


def read_u8(data: bytes, offset: int) -> int:
    """读取 uint8"""
    if offset >= len(data):
        return 0
    return data[offset]


# 程序 ID 常量
PUMPSWAP_PROGRAM_ID = "pAMMBay6oceH9fJKBRdGP4LmT4saRGfEE7xmrCaGWpZ"


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
]
