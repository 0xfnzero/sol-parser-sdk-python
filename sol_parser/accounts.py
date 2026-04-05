"""账户解析器 - 对齐 Rust 实现，超低延迟优化版

性能优化措施：
1. 预定义所有常量，避免运行时创建
2. 使用 memoryview 实现零拷贝
3. base58 模块在顶层导入，避免函数内重复导入
4. 使用 struct.unpack_from 避免切片
5. 快速路径优先，早期返回
"""

from __future__ import annotations

import struct
from typing import Optional, List
from dataclasses import dataclass

import base58

from .grpc_types import EventTypeFilter, EventType, EventMetadata
from .dex_parsers import DexEvent


# ============================================================================
# 预定义常量 - 避免运行时分配
# ============================================================================

# 程序 ID
PUMPSWAP_PROGRAM_ID = "pAMMBay6oceH9fJKBRdGP4LmT4saRGfEE7xmrCaGWpZ"

# Discriminator 常量（bytes 对象，避免重复创建）
_DISC_GLOBAL_CONFIG = bytes([149, 8, 156, 202, 160, 252, 176, 217])
_DISC_POOL = bytes([241, 154, 109, 4, 17, 177, 109, 188])
_DISC_NONCE = bytes([1, 0, 0, 0, 1, 0, 0, 0])

# 大小常量
MINT_SIZE = 82
TOKEN_ACCOUNT_SIZE = 165
NONCE_ACCOUNT_SIZE = 80
GLOBAL_CONFIG_BODY = 634
POOL_BODY = 244

# 偏移常量
SUPPLY_OFFSET = 36
DECIMALS_OFFSET = 44
AMOUNT_OFFSET = 64
NONCE_AUTHORITY_OFFSET = 8
NONCE_NONCE_OFFSET = 40

# 空 pubkey 常量
EMPTY_PUBKEY = ""


# ============================================================================
# 数据类
# ============================================================================

@dataclass
class AccountData:
    """账户数据结构"""
    pubkey: str
    executable: bool
    lamports: int
    owner: str
    rent_epoch: int
    data: bytes


# ============================================================================
# 超低延迟辅助函数
# ============================================================================


def has_discriminator(data: bytes, discriminator: bytes) -> bool:
    """检查是否有指定的 discriminator - 优化版"""
    dlen = len(discriminator)
    if len(data) < dlen:
        return False
    # 使用直接比较，Python 会优化这个操作
    return data[:dlen] == discriminator


def base58_encode_32(data: bytes) -> str:
    """将 32 字节编码为 Base58 - 内联优化版"""
    return base58.b58encode(data).decode('ascii')


def read_pubkey_fast(data: bytes, offset: int) -> str:
    """从字节数组读取公钥（32字节）- 快速版"""
    if offset + 32 > len(data):
        return EMPTY_PUBKEY
    return base58.b58encode(data[offset:offset + 32]).decode('ascii')


def read_u64_fast(data: bytes, offset: int) -> int:
    """读取小端序 uint64 - 快速版"""
    return struct.unpack_from("<Q", data, offset)[0]


def read_u16_fast(data: bytes, offset: int) -> int:
    """读取小端序 uint16 - 快速版"""
    return struct.unpack_from("<H", data, offset)[0]


# ============================================================================
# 账户解析主函数
# ============================================================================

def parse_account_unified(
    account: AccountData,
    metadata: EventMetadata,
    filter: EventTypeFilter
) -> Optional[DexEvent]:
    """统一的账户解析入口 - 优化版
    
    对齐 Rust `parse_account_unified`
    快速路径优先，早期返回
    """
    data = account.data
    if not data:
        return None

    # 快速路径：检查 PumpSwap（按 discriminator 前缀快速匹配）
    if account.owner == PUMPSWAP_PROGRAM_ID:
        if len(data) >= 8:
            first_byte = data[0]
            # Global Config: 149 (0x95), Pool: 241 (0xF1)
            if first_byte == 149:  # 可能是 Global Config
                if has_discriminator(data, _DISC_GLOBAL_CONFIG):
                    return _parse_pumpswap_global_config_fast(account, metadata)
            elif first_byte == 241:  # 可能是 Pool
                if has_discriminator(data, _DISC_POOL):
                    return _parse_pumpswap_pool_fast(account, metadata)

    # 快速路径：Nonce 账户检测
    if len(data) == NONCE_ACCOUNT_SIZE and has_discriminator(data, _DISC_NONCE):
        return _parse_nonce_fast(account, metadata)

    # Token 账户解析
    # 快速路径：小数据可能是 Mint
    dlen = len(data)
    if dlen <= 100:
        if dlen >= MINT_SIZE:
            return _parse_mint_fast(account, metadata)
        return None
    
    if dlen >= TOKEN_ACCOUNT_SIZE:
        return _parse_token_fast(account, metadata)
    
    return None


# ============================================================================
# 快速解析函数
# ============================================================================

def _parse_mint_fast(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    """快速解析 Mint 账户（零拷贝）"""
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
    """快速解析 Token Account（零拷贝）"""
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
    """快速解析 Nonce 账户"""
    data = account.data
    authority = base58_encode_32(data[NONCE_AUTHORITY_OFFSET:NONCE_AUTHORITY_OFFSET + 32])
    nonce = base58_encode_32(data[NONCE_NONCE_OFFSET:NONCE_NONCE_OFFSET + 32])
    
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
    """快速解析 PumpSwap Global Config 账户"""
    data = account.data[8:]  # Skip discriminator
    o = 0
    
    admin = read_pubkey_fast(data, o)
    o += 32
    
    lp_fee = read_u64_fast(data, o)
    o += 8
    
    protocol_fee = read_u64_fast(data, o)
    o += 8
    
    disable_flags = data[o]
    o += 1
    
    # 读取 8 个 protocol_fee_recipients
    recipients = [
        read_pubkey_fast(data, o), read_pubkey_fast(data, o + 32),
        read_pubkey_fast(data, o + 64), read_pubkey_fast(data, o + 96),
        read_pubkey_fast(data, o + 128), read_pubkey_fast(data, o + 160),
        read_pubkey_fast(data, o + 192), read_pubkey_fast(data, o + 224),
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
    
    # 读取 7 个 reserved_fee_recipients
    reserved_list = [
        read_pubkey_fast(data, o), read_pubkey_fast(data, o + 32),
        read_pubkey_fast(data, o + 64), read_pubkey_fast(data, o + 96),
        read_pubkey_fast(data, o + 128), read_pubkey_fast(data, o + 160),
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
            }
        }
    }


def _parse_pumpswap_pool_fast(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    """快速解析 PumpSwap Pool 账户
    
    结构体布局（按顺序）：
    - pool_bump: u8 (1 byte)
    - index: u16 (2 bytes)
    - creator: pubkey (32 bytes)
    - base_mint: pubkey (32 bytes)
    - quote_mint: pubkey (32 bytes)
    - lp_mint: pubkey (32 bytes)
    - pool_base_token_account: pubkey (32 bytes)
    - pool_quote_token_account: pubkey (32 bytes)
    - lp_supply: u64 (8 bytes)
    - coin_creator: pubkey (32 bytes)
    - is_mayhem_mode: bool (1 byte)
    - is_cashback_coin: bool (1 byte)
    """
    data = account.data[8:]  # Skip discriminator
    o = 0
    
    pool_bump = data[o]
    o += 1
    
    index = read_u16_fast(data, o)
    o += 2
    
    # 批量读取所有 pubkey，减少函数调用开销
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
            }
        }
    }


# ============================================================================
# 兼容性函数（保持 API 兼容）
# ============================================================================

def parse_token_account(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    """解析 Token 账户"""
    if len(account.data) <= 100:
        event = _parse_mint_fast(account, metadata)
        if event:
            return event
    return _parse_token_fast(account, metadata)


def parse_nonce_account(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    """解析 Nonce 账户"""
    if len(account.data) != NONCE_ACCOUNT_SIZE:
        return None
    if not has_discriminator(account.data, _DISC_NONCE):
        return None
    return _parse_nonce_fast(account, metadata)


def is_nonce_account(data: bytes) -> bool:
    """检测是否为 Nonce 账户"""
    return len(data) >= 8 and has_discriminator(data, _DISC_NONCE)


def parse_pumpswap_global_config(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    """解析 PumpSwap Global Config 账户"""
    if len(account.data) < 8 + GLOBAL_CONFIG_BODY:
        return None
    if not has_discriminator(account.data, _DISC_GLOBAL_CONFIG):
        return None
    return _parse_pumpswap_global_config_fast(account, metadata)


def parse_pumpswap_pool(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    """解析 PumpSwap Pool 账户"""
    if len(account.data) < 8 + POOL_BODY:
        return None
    if not has_discriminator(account.data, _DISC_POOL):
        return None
    return _parse_pumpswap_pool_fast(account, metadata)


def is_global_config_account(data: bytes) -> bool:
    """检查是否为 Global Config 账户"""
    return has_discriminator(data, _DISC_GLOBAL_CONFIG)


def is_pool_account(data: bytes) -> bool:
    """检查是否为 Pool 账户"""
    return has_discriminator(data, _DISC_POOL)


# 保留旧名称的别名
base58_encode = base58_encode_32
read_pubkey = read_pubkey_fast
read_u64_le = read_u64_fast
read_u8 = lambda data, offset: data[offset] if offset < len(data) else 0


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
]
