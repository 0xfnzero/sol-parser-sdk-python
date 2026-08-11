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
from .raydium_orca import (
    ORCA_WHIRLPOOL_PROGRAM_ID,
    RAYDIUM_CLMM_PROGRAM_ID,
    RAYDIUM_CPMM_PROGRAM_ID,
    parse_orca_whirlpool_account,
    parse_raydium_clmm_account,
    parse_raydium_cpmm_account,
)

# 程序 ID（与 Rust ``accounts/program_ids`` / ``instr/program_ids`` 一致）
PUMPFUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMP_FEES_PROGRAM_ID = "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"
PUMPSWAP_PROGRAM_ID = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"

_DISC_PUMPFUN_GLOBAL = bytes([167, 232, 232, 177, 200, 108, 114, 127])
_DISC_PUMPFUN_BONDING_CURVE = bytes([23, 183, 248, 55, 96, 216, 172, 96])
_DISC_PUMPFUN_FEE_CONFIG = bytes([143, 52, 146, 187, 219, 123, 76, 155])
_DISC_PUMPFUN_GLOBAL_VOLUME_ACCUMULATOR = bytes([202, 42, 246, 43, 142, 190, 30, 255])
_DISC_PUMPFUN_SHARING_CONFIG = bytes([216, 74, 9, 0, 56, 140, 93, 75])
_DISC_PUMPFUN_USER_VOLUME_ACCUMULATOR = bytes([86, 255, 112, 14, 102, 53, 154, 250])
_DISC_GLOBAL_CONFIG = bytes([149, 8, 156, 202, 160, 252, 176, 217])
_DISC_POOL = bytes([241, 154, 109, 4, 17, 177, 109, 188])
_DISC_NONCE = bytes([1, 0, 0, 0, 1, 0, 0, 0])

MINT_SIZE = 82
TOKEN_ACCOUNT_SIZE = 165
NONCE_ACCOUNT_SIZE = 80
PUMPFUN_GLOBAL_BODY = 1037
PUMPFUN_BONDING_CURVE_BODY = 107
PUMPFUN_GLOBAL_VOLUME_ACCUMULATOR_BODY = 536
PUMPFUN_USER_VOLUME_ACCUMULATOR_BODY = 98
GLOBAL_CONFIG_BODY = 634
POOL_LEGACY_BODY = 244
POOL_BODY = 253
MAX_PUMPFUN_FEE_TIERS = 64
MAX_PUMPFUN_SHAREHOLDERS = 64

SUPPLY_OFFSET = 36
DECIMALS_OFFSET = 44
AMOUNT_OFFSET = 64
NONCE_AUTHORITY_OFFSET = 8
NONCE_NONCE_OFFSET = 40

EMPTY_PUBKEY = ""


def _account_event(event_type: EventType, data: dict) -> DexEvent:
    return DexEvent(type=event_type, data=data)


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


def read_i64_fast(data: bytes, offset: int) -> int:
    return struct.unpack_from("<q", data, offset)[0]


def read_u32_fast(data: bytes, offset: int) -> int:
    return struct.unpack_from("<I", data, offset)[0]


def read_u128_fast(data: bytes, offset: int) -> int:
    return int.from_bytes(data[offset : offset + 16], "little")


def _read_pumpfun_fees(data: bytes, offset: int) -> Optional[tuple[dict, int]]:
    if offset + 24 > len(data):
        return None
    return (
        {
            "lp_fee_bps": read_u64_fast(data, offset),
            "protocol_fee_bps": read_u64_fast(data, offset + 8),
            "creator_fee_bps": read_u64_fast(data, offset + 16),
        },
        offset + 24,
    )


def _read_pumpfun_fee_tiers(data: bytes, offset: int) -> Optional[tuple[list[dict], int]]:
    if offset + 4 > len(data):
        return None
    length = read_u32_fast(data, offset)
    if length > MAX_PUMPFUN_FEE_TIERS:
        return None
    offset += 4
    if offset + length * 40 > len(data):
        return None
    out = []
    for _ in range(length):
        threshold = read_u128_fast(data, offset)
        offset += 16
        fees_result = _read_pumpfun_fees(data, offset)
        if fees_result is None:
            return None
        fees, offset = fees_result
        out.append({"market_cap_lamports_threshold": threshold, "fees": fees})
    return out, offset


def _read_pumpfun_shareholders(data: bytes, offset: int) -> Optional[tuple[list[dict], int]]:
    if offset + 4 > len(data):
        return None
    length = read_u32_fast(data, offset)
    if length > MAX_PUMPFUN_SHAREHOLDERS:
        return None
    offset += 4
    if offset + length * 34 > len(data):
        return None
    out = []
    for _ in range(length):
        address = read_pubkey_fast(data, offset)
        offset += 32
        share_bps = read_u16_fast(data, offset)
        offset += 2
        out.append({"address": address, "share_bps": share_bps})
    return out, offset


def _filter_account_event(
    ev: Optional[DexEvent],
    event_type_filter: Optional[EventTypeFilter],
) -> Optional[DexEvent]:
    if ev is None or event_type_filter is None:
        return ev
    return ev if event_type_filter.should_include(ev.type) else None


ACCOUNT_EVENT_TYPES = frozenset(
    (
        EventType.TOKEN_ACCOUNT,
        EventType.TOKEN_INFO,
        EventType.NONCE_ACCOUNT,
        EventType.ACCOUNT_PUMP_FUN_GLOBAL,
        EventType.ACCOUNT_PUMP_FUN_BONDING_CURVE,
        EventType.ACCOUNT_PUMP_FUN_FEE_CONFIG,
        EventType.ACCOUNT_PUMP_FUN_SHARING_CONFIG,
        EventType.ACCOUNT_PUMP_FUN_GLOBAL_VOLUME_ACCUMULATOR,
        EventType.ACCOUNT_PUMP_FUN_USER_VOLUME_ACCUMULATOR,
        EventType.ACCOUNT_PUMP_SWAP_GLOBAL_CONFIG,
        EventType.ACCOUNT_PUMP_SWAP_POOL,
        EventType.ACCOUNT_RAYDIUM_CLMM_AMM_CONFIG,
        EventType.ACCOUNT_RAYDIUM_CLMM_POOL_STATE,
        EventType.ACCOUNT_RAYDIUM_CLMM_TICK_ARRAY_STATE,
        EventType.ACCOUNT_RAYDIUM_CPMM_AMM_CONFIG,
        EventType.ACCOUNT_RAYDIUM_CPMM_POOL_STATE,
        EventType.ACCOUNT_ORCA_WHIRLPOOL,
        EventType.ACCOUNT_ORCA_POSITION,
        EventType.ACCOUNT_ORCA_TICK_ARRAY,
        EventType.ACCOUNT_ORCA_FEE_TIER,
        EventType.ACCOUNT_ORCA_WHIRLPOOLS_CONFIG,
    )
)


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
            if not any(t in ACCOUNT_EVENT_TYPES for t in inc):
                return None

    if account.owner == PUMPSWAP_PROGRAM_ID:
        should_parse_pumpswap = event_type_filter is None or (
            event_type_filter.should_include(EventType.ACCOUNT_PUMP_SWAP_GLOBAL_CONFIG)
            or event_type_filter.should_include(EventType.ACCOUNT_PUMP_SWAP_POOL)
        )
        if should_parse_pumpswap:
            ev = _parse_pumpswap_account(account, metadata)
            if ev is not None:
                return _filter_account_event(ev, event_type_filter)
        return None

    if account.owner in (PUMPFUN_PROGRAM_ID, PUMP_FEES_PROGRAM_ID):
        should_parse_pumpfun = event_type_filter is None or (
            event_type_filter.should_include(EventType.ACCOUNT_PUMP_FUN_GLOBAL)
            or event_type_filter.should_include(EventType.ACCOUNT_PUMP_FUN_BONDING_CURVE)
            or event_type_filter.should_include(EventType.ACCOUNT_PUMP_FUN_FEE_CONFIG)
            or event_type_filter.should_include(EventType.ACCOUNT_PUMP_FUN_SHARING_CONFIG)
            or event_type_filter.should_include(EventType.ACCOUNT_PUMP_FUN_GLOBAL_VOLUME_ACCUMULATOR)
            or event_type_filter.should_include(EventType.ACCOUNT_PUMP_FUN_USER_VOLUME_ACCUMULATOR)
        )
        if should_parse_pumpfun:
            ev = _parse_pumpfun_account(account, metadata)
            if ev is not None:
                return _filter_account_event(ev, event_type_filter)
        return None

    if account.owner == RAYDIUM_CLMM_PROGRAM_ID:
        should_parse_clmm = event_type_filter is None or (
            event_type_filter.should_include(EventType.ACCOUNT_RAYDIUM_CLMM_AMM_CONFIG)
            or event_type_filter.should_include(EventType.ACCOUNT_RAYDIUM_CLMM_POOL_STATE)
            or event_type_filter.should_include(EventType.ACCOUNT_RAYDIUM_CLMM_TICK_ARRAY_STATE)
        )
        if should_parse_clmm:
            ev = parse_raydium_clmm_account(account, metadata)
            if ev is not None:
                return _filter_account_event(ev, event_type_filter)
        return None

    if account.owner == RAYDIUM_CPMM_PROGRAM_ID:
        should_parse_cpmm = event_type_filter is None or (
            event_type_filter.should_include(EventType.ACCOUNT_RAYDIUM_CPMM_AMM_CONFIG)
            or event_type_filter.should_include(EventType.ACCOUNT_RAYDIUM_CPMM_POOL_STATE)
        )
        if should_parse_cpmm:
            ev = parse_raydium_cpmm_account(account, metadata)
            if ev is not None:
                return _filter_account_event(ev, event_type_filter)
        return None

    if account.owner == ORCA_WHIRLPOOL_PROGRAM_ID:
        should_parse_orca = event_type_filter is None or (
            event_type_filter.should_include(EventType.ACCOUNT_ORCA_WHIRLPOOL)
            or event_type_filter.should_include(EventType.ACCOUNT_ORCA_POSITION)
            or event_type_filter.should_include(EventType.ACCOUNT_ORCA_TICK_ARRAY)
            or event_type_filter.should_include(EventType.ACCOUNT_ORCA_FEE_TIER)
            or event_type_filter.should_include(EventType.ACCOUNT_ORCA_WHIRLPOOLS_CONFIG)
        )
        if should_parse_orca:
            ev = parse_orca_whirlpool_account(account, metadata)
            if ev is not None:
                return _filter_account_event(ev, event_type_filter)
        return None

    if acc_utils.is_nonce_account(data):
        if event_type_filter is not None:
            if not event_type_filter.should_include(EventType.NONCE_ACCOUNT):
                return None
        return _parse_nonce_fast(account, metadata)

    if event_type_filter is not None:
        if not event_type_filter.should_include(
            EventType.TOKEN_ACCOUNT
        ) and not event_type_filter.should_include(EventType.TOKEN_INFO):
            return None
    return _filter_account_event(parse_token_account(account, metadata), event_type_filter)


def _parse_pumpswap_account(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    if acc_utils.has_discriminator(account.data, _DISC_GLOBAL_CONFIG):
        return parse_pumpswap_global_config(account, metadata)
    if acc_utils.has_discriminator(account.data, _DISC_POOL):
        return parse_pumpswap_pool(account, metadata)
    return None


def _parse_pumpfun_account(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    if acc_utils.has_discriminator(account.data, _DISC_PUMPFUN_FEE_CONFIG):
        return parse_pumpfun_fee_config(account, metadata)
    if acc_utils.has_discriminator(account.data, _DISC_PUMPFUN_SHARING_CONFIG):
        return parse_pumpfun_sharing_config(account, metadata)
    if acc_utils.has_discriminator(account.data, _DISC_PUMPFUN_GLOBAL_VOLUME_ACCUMULATOR):
        return parse_pumpfun_global_volume_accumulator(account, metadata)
    if acc_utils.has_discriminator(account.data, _DISC_PUMPFUN_USER_VOLUME_ACCUMULATOR):
        return parse_pumpfun_user_volume_accumulator(account, metadata)
    if acc_utils.has_discriminator(account.data, _DISC_PUMPFUN_BONDING_CURVE):
        return parse_pumpfun_bonding_curve(account, metadata)
    if acc_utils.has_discriminator(account.data, _DISC_PUMPFUN_GLOBAL):
        return parse_pumpfun_global(account, metadata)
    return None


def _parse_mint_fast(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    data = account.data
    return _account_event(
        EventType.TOKEN_INFO,
        {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "executable": account.executable,
            "lamports": account.lamports,
            "owner": account.owner,
            "rent_epoch": account.rent_epoch,
            "supply": struct.unpack_from("<Q", data, SUPPLY_OFFSET)[0],
            "decimals": data[DECIMALS_OFFSET],
        },
    )


def _parse_token_fast(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    data = account.data
    return _account_event(
        EventType.TOKEN_ACCOUNT,
        {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "executable": account.executable,
            "lamports": account.lamports,
            "owner": account.owner,
            "rent_epoch": account.rent_epoch,
            "amount": struct.unpack_from("<Q", data, AMOUNT_OFFSET)[0],
        },
    )


def _parse_nonce_fast(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    data = account.data
    authority = base58_encode_32(data[NONCE_AUTHORITY_OFFSET : NONCE_AUTHORITY_OFFSET + 32])
    nonce = base58_encode_32(data[NONCE_NONCE_OFFSET : NONCE_NONCE_OFFSET + 32])
    return _account_event(
        EventType.NONCE_ACCOUNT,
        {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "executable": account.executable,
            "lamports": account.lamports,
            "owner": account.owner,
            "rent_epoch": account.rent_epoch,
            "nonce": nonce,
            "authority": authority,
        },
    )


def _parse_pumpfun_global_fast(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    data = account.data[8:]
    o = 0
    initialized = data[o] != 0
    o += 1
    authority = read_pubkey_fast(data, o)
    o += 32
    fee_recipient = read_pubkey_fast(data, o)
    o += 32
    initial_virtual_token_reserves = read_u64_fast(data, o)
    o += 8
    initial_virtual_sol_reserves = read_u64_fast(data, o)
    o += 8
    initial_real_token_reserves = read_u64_fast(data, o)
    o += 8
    token_total_supply = read_u64_fast(data, o)
    o += 8
    fee_basis_points = read_u64_fast(data, o)
    o += 8
    withdraw_authority = read_pubkey_fast(data, o)
    o += 32
    enable_migrate = data[o] != 0
    o += 1
    pool_migration_fee = read_u64_fast(data, o)
    o += 8
    creator_fee_basis_points = read_u64_fast(data, o)
    o += 8
    fee_recipients = []
    for _ in range(7):
        fee_recipients.append(read_pubkey_fast(data, o))
        o += 32
    set_creator_authority = read_pubkey_fast(data, o)
    o += 32
    admin_set_creator_authority = read_pubkey_fast(data, o)
    o += 32
    create_v2_enabled = data[o] != 0
    o += 1
    whitelist_pda = read_pubkey_fast(data, o)
    o += 32
    reserved_fee_recipient = read_pubkey_fast(data, o)
    o += 32
    mayhem_mode_enabled = data[o] != 0
    o += 1
    reserved_fee_recipients = []
    for _ in range(7):
        reserved_fee_recipients.append(read_pubkey_fast(data, o))
        o += 32
    is_cashback_enabled = data[o] != 0
    o += 1
    buyback_fee_recipients = []
    for _ in range(8):
        buyback_fee_recipients.append(read_pubkey_fast(data, o))
        o += 32
    buyback_basis_points = read_u64_fast(data, o)
    o += 8
    initial_virtual_quote_reserves = read_u64_fast(data, o)
    o += 8
    whitelisted_quote_mints = [read_pubkey_fast(data, o)]
    o += 32
    return _account_event(
        EventType.ACCOUNT_PUMP_FUN_GLOBAL,
        {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "global": {
                "initialized": initialized,
                "authority": authority,
                "fee_recipient": fee_recipient,
                "initial_virtual_token_reserves": initial_virtual_token_reserves,
                "initial_virtual_sol_reserves": initial_virtual_sol_reserves,
                "initial_real_token_reserves": initial_real_token_reserves,
                "token_total_supply": token_total_supply,
                "fee_basis_points": fee_basis_points,
                "withdraw_authority": withdraw_authority,
                "enable_migrate": enable_migrate,
                "pool_migration_fee": pool_migration_fee,
                "creator_fee_basis_points": creator_fee_basis_points,
                "fee_recipients": fee_recipients,
                "set_creator_authority": set_creator_authority,
                "admin_set_creator_authority": admin_set_creator_authority,
                "create_v2_enabled": create_v2_enabled,
                "whitelist_pda": whitelist_pda,
                "reserved_fee_recipient": reserved_fee_recipient,
                "mayhem_mode_enabled": mayhem_mode_enabled,
                "reserved_fee_recipients": reserved_fee_recipients,
                "is_cashback_enabled": is_cashback_enabled,
                "buyback_fee_recipients": buyback_fee_recipients,
                "buyback_basis_points": buyback_basis_points,
                "initial_virtual_quote_reserves": initial_virtual_quote_reserves,
                "whitelisted_quote_mints": whitelisted_quote_mints,
            },
        },
    )


def _parse_pumpfun_bonding_curve_fast(
    account: AccountData, metadata: EventMetadata
) -> Optional[DexEvent]:
    data = account.data[8:]
    o = 0
    virtual_token_reserves = read_u64_fast(data, o)
    o += 8
    virtual_quote_reserves = read_u64_fast(data, o)
    o += 8
    real_token_reserves = read_u64_fast(data, o)
    o += 8
    real_quote_reserves = read_u64_fast(data, o)
    o += 8
    token_total_supply = read_u64_fast(data, o)
    o += 8
    complete = data[o] != 0
    o += 1
    creator = read_pubkey_fast(data, o)
    o += 32
    is_mayhem_mode = data[o] != 0
    o += 1
    is_cashback_coin = data[o] != 0
    o += 1
    quote_mint = read_pubkey_fast(data, o)
    return _account_event(
        EventType.ACCOUNT_PUMP_FUN_BONDING_CURVE,
        {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "bonding_curve": {
                "virtual_token_reserves": virtual_token_reserves,
                "virtual_quote_reserves": virtual_quote_reserves,
                "real_token_reserves": real_token_reserves,
                "real_quote_reserves": real_quote_reserves,
                "token_total_supply": token_total_supply,
                "complete": complete,
                "creator": creator,
                "is_mayhem_mode": is_mayhem_mode,
                "is_cashback_coin": is_cashback_coin,
                "quote_mint": quote_mint,
            },
        },
    )


def _parse_pumpfun_fee_config_fast(
    account: AccountData, metadata: EventMetadata
) -> Optional[DexEvent]:
    data = account.data[8:]
    o = 0
    bump = data[o]
    o += 1
    admin = read_pubkey_fast(data, o)
    o += 32
    flat_fees_result = _read_pumpfun_fees(data, o)
    if flat_fees_result is None:
        return None
    flat_fees, o = flat_fees_result
    fee_tiers_result = _read_pumpfun_fee_tiers(data, o)
    if fee_tiers_result is None:
        return None
    fee_tiers, o = fee_tiers_result
    stable_fee_tiers_result = _read_pumpfun_fee_tiers(data, o)
    if stable_fee_tiers_result is None:
        return None
    stable_fee_tiers, _ = stable_fee_tiers_result
    return _account_event(
        EventType.ACCOUNT_PUMP_FUN_FEE_CONFIG,
        {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "fee_config": {
                "bump": bump,
                "admin": admin,
                "flat_fees": flat_fees,
                "fee_tiers": fee_tiers,
                "stable_fee_tiers": stable_fee_tiers,
            },
        },
    )


def _parse_pumpfun_sharing_config_fast(
    account: AccountData, metadata: EventMetadata
) -> Optional[DexEvent]:
    data = account.data[8:]
    o = 0
    bump = data[o]
    o += 1
    version = data[o]
    o += 1
    status_raw = data[o]
    if status_raw > 1:
        return None
    status = "Paused" if status_raw == 0 else "Active"
    o += 1
    mint = read_pubkey_fast(data, o)
    o += 32
    admin = read_pubkey_fast(data, o)
    o += 32
    admin_revoked = data[o] != 0
    o += 1
    shareholders_result = _read_pumpfun_shareholders(data, o)
    if shareholders_result is None:
        return None
    shareholders, _ = shareholders_result
    return _account_event(
        EventType.ACCOUNT_PUMP_FUN_SHARING_CONFIG,
        {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "sharing_config": {
                "bump": bump,
                "version": version,
                "status": status,
                "mint": mint,
                "admin": admin,
                "admin_revoked": admin_revoked,
                "shareholders": shareholders,
            },
        },
    )


def _parse_pumpfun_global_volume_accumulator_fast(
    account: AccountData, metadata: EventMetadata
) -> Optional[DexEvent]:
    data = account.data[8:]
    o = 0
    start_time = read_i64_fast(data, o)
    o += 8
    end_time = read_i64_fast(data, o)
    o += 8
    seconds_in_a_day = read_i64_fast(data, o)
    o += 8
    mint = read_pubkey_fast(data, o)
    o += 32
    total_token_supply = []
    for _ in range(30):
        total_token_supply.append(read_u64_fast(data, o))
        o += 8
    sol_volumes = []
    for _ in range(30):
        sol_volumes.append(read_u64_fast(data, o))
        o += 8
    return _account_event(
        EventType.ACCOUNT_PUMP_FUN_GLOBAL_VOLUME_ACCUMULATOR,
        {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "global_volume_accumulator": {
                "start_time": start_time,
                "end_time": end_time,
                "seconds_in_a_day": seconds_in_a_day,
                "mint": mint,
                "total_token_supply": total_token_supply,
                "sol_volumes": sol_volumes,
            },
        },
    )


def _parse_pumpfun_user_volume_accumulator_fast(
    account: AccountData, metadata: EventMetadata
) -> Optional[DexEvent]:
    data = account.data[8:]
    o = 0
    user = read_pubkey_fast(data, o)
    o += 32
    needs_claim = data[o] != 0
    o += 1
    total_unclaimed_tokens = read_u64_fast(data, o)
    o += 8
    total_claimed_tokens = read_u64_fast(data, o)
    o += 8
    current_sol_volume = read_u64_fast(data, o)
    o += 8
    last_update_timestamp = read_i64_fast(data, o)
    o += 8
    has_total_claimed_tokens = data[o] != 0
    o += 1
    cashback_earned = read_u64_fast(data, o)
    o += 8
    total_cashback_claimed = read_u64_fast(data, o)
    o += 8
    stable_cashback_earned = read_u64_fast(data, o)
    o += 8
    total_stable_cashback_claimed = read_u64_fast(data, o)
    return _account_event(
        EventType.ACCOUNT_PUMP_FUN_USER_VOLUME_ACCUMULATOR,
        {
            "metadata": metadata,
            "pubkey": account.pubkey,
            "user_volume_accumulator": {
                "user": user,
                "needs_claim": needs_claim,
                "total_unclaimed_tokens": total_unclaimed_tokens,
                "total_claimed_tokens": total_claimed_tokens,
                "current_sol_volume": current_sol_volume,
                "last_update_timestamp": last_update_timestamp,
                "has_total_claimed_tokens": has_total_claimed_tokens,
                "cashback_earned": cashback_earned,
                "total_cashback_claimed": total_cashback_claimed,
                "stable_cashback_earned": stable_cashback_earned,
                "total_stable_cashback_claimed": total_stable_cashback_claimed,
            },
        },
    )


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
    return _account_event(
        EventType.ACCOUNT_PUMP_SWAP_GLOBAL_CONFIG,
        {
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
        },
    )


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
    o += 2
    virtual_quote_reserves = (
        int.from_bytes(data[o : o + 16], "little", signed=True) if len(data) >= POOL_BODY else 0
    )
    return _account_event(
        EventType.ACCOUNT_PUMP_SWAP_POOL,
        {
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
                "virtual_quote_reserves": virtual_quote_reserves,
            },
        },
    )


def parse_token_account(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    if not acc_utils.is_token_program_account(account.owner):
        return None

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


def parse_pumpfun_global(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    if len(account.data) < 8 + PUMPFUN_GLOBAL_BODY:
        return None
    if not has_discriminator(account.data, _DISC_PUMPFUN_GLOBAL):
        return None
    return _parse_pumpfun_global_fast(account, metadata)


def parse_pumpfun_bonding_curve(
    account: AccountData, metadata: EventMetadata
) -> Optional[DexEvent]:
    if len(account.data) < 8 + PUMPFUN_BONDING_CURVE_BODY:
        return None
    if not has_discriminator(account.data, _DISC_PUMPFUN_BONDING_CURVE):
        return None
    return _parse_pumpfun_bonding_curve_fast(account, metadata)


def parse_pumpfun_fee_config(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    if len(account.data) < 8 + 1 + 32 + 24 + 4 + 4:
        return None
    if not has_discriminator(account.data, _DISC_PUMPFUN_FEE_CONFIG):
        return None
    return _parse_pumpfun_fee_config_fast(account, metadata)


def parse_pumpfun_sharing_config(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    if len(account.data) < 8 + 1 + 1 + 1 + 32 + 32 + 1 + 4:
        return None
    if not has_discriminator(account.data, _DISC_PUMPFUN_SHARING_CONFIG):
        return None
    return _parse_pumpfun_sharing_config_fast(account, metadata)


def parse_pumpfun_global_volume_accumulator(
    account: AccountData, metadata: EventMetadata
) -> Optional[DexEvent]:
    if len(account.data) < 8 + PUMPFUN_GLOBAL_VOLUME_ACCUMULATOR_BODY:
        return None
    if not has_discriminator(account.data, _DISC_PUMPFUN_GLOBAL_VOLUME_ACCUMULATOR):
        return None
    return _parse_pumpfun_global_volume_accumulator_fast(account, metadata)


def parse_pumpfun_user_volume_accumulator(
    account: AccountData, metadata: EventMetadata
) -> Optional[DexEvent]:
    if len(account.data) < 8 + PUMPFUN_USER_VOLUME_ACCUMULATOR_BODY:
        return None
    if not has_discriminator(account.data, _DISC_PUMPFUN_USER_VOLUME_ACCUMULATOR):
        return None
    return _parse_pumpfun_user_volume_accumulator_fast(account, metadata)


def is_nonce_account(data: bytes) -> bool:
    return acc_utils.is_nonce_account(data)


def parse_pumpswap_global_config(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    if len(account.data) < 8 + GLOBAL_CONFIG_BODY:
        return None
    if not has_discriminator(account.data, _DISC_GLOBAL_CONFIG):
        return None
    return _parse_pumpswap_global_config_fast(account, metadata)


def parse_pumpswap_pool(account: AccountData, metadata: EventMetadata) -> Optional[DexEvent]:
    if len(account.data) < 8 + POOL_LEGACY_BODY:
        return None
    if len(account.data) != 8 + POOL_LEGACY_BODY and len(account.data) < 8 + POOL_BODY:
        return None
    if not has_discriminator(account.data, _DISC_POOL):
        return None
    return _parse_pumpswap_pool_fast(account, metadata)


def is_global_config_account(data: bytes) -> bool:
    return has_discriminator(data, _DISC_GLOBAL_CONFIG)


def is_pool_account(data: bytes) -> bool:
    return has_discriminator(data, _DISC_POOL)


def is_pumpfun_global_account(data: bytes) -> bool:
    return has_discriminator(data, _DISC_PUMPFUN_GLOBAL)


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
    "parse_pumpfun_global",
    "parse_pumpfun_bonding_curve",
    "parse_pumpfun_fee_config",
    "parse_pumpfun_sharing_config",
    "parse_pumpfun_global_volume_accumulator",
    "parse_pumpfun_user_volume_accumulator",
    "is_nonce_account",
    "is_pumpfun_global_account",
    "parse_pumpswap_global_config",
    "parse_pumpswap_pool",
    "parse_raydium_clmm_account",
    "parse_raydium_cpmm_account",
    "parse_orca_whirlpool_account",
    "is_global_config_account",
    "is_pool_account",
    "has_discriminator",
    "PUMPFUN_PROGRAM_ID",
    "PUMP_FEES_PROGRAM_ID",
    "PUMPSWAP_PROGRAM_ID",
    "RAYDIUM_CLMM_PROGRAM_ID",
    "RAYDIUM_CPMM_PROGRAM_ID",
    "ORCA_WHIRLPOOL_PROGRAM_ID",
    "rpc_resolve_user_wallet_pubkey",
    "user_wallet_pubkey_for_onchain_account",
    "rpc_wallet",
    "acc_utils",
]
