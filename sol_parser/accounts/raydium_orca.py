"""Raydium CLMM/CPMM and Orca Whirlpool account parsers."""

from __future__ import annotations

import struct
from typing import Any, Callable, Optional, TypeVar

import base58

from ..dex_parsers import DexEvent
from ..grpc_types import EventMetadata, EventType

RAYDIUM_CLMM_PROGRAM_ID = "CAMMCzo5YL8w4VFF8KVHrK22GGUsp5VTaW7grrKgrWqK"
RAYDIUM_CPMM_PROGRAM_ID = "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"
ORCA_WHIRLPOOL_PROGRAM_ID = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"

CLMM_AMM_CONFIG_DISC = bytes([218, 244, 33, 104, 203, 203, 43, 111])
CLMM_POOL_STATE_DISC = bytes([247, 237, 227, 245, 215, 195, 222, 70])
CLMM_TICK_ARRAY_STATE_DISC = bytes([192, 155, 85, 205, 49, 249, 129, 42])
CLMM_AMM_CONFIG_BODY = 109
CLMM_POOL_STATE_BODY = 1536
CLMM_TICK_ARRAY_STATE_BODY = 10232
CLMM_TICK_ARRAY_LEN = 60

CPMM_AMM_CONFIG_DISC = CLMM_AMM_CONFIG_DISC
CPMM_POOL_STATE_DISC = CLMM_POOL_STATE_DISC
CPMM_AMM_CONFIG_BODY = 228
CPMM_POOL_STATE_BODY = 629

ORCA_WHIRLPOOL_DISC = bytes([63, 149, 209, 12, 225, 128, 99, 9])
ORCA_POSITION_DISC = bytes([170, 188, 143, 228, 122, 64, 247, 208])
ORCA_TICK_ARRAY_DISC = bytes([69, 97, 189, 190, 110, 7, 66, 187])
ORCA_FEE_TIER_DISC = bytes([56, 75, 159, 76, 142, 68, 190, 105])
ORCA_WHIRLPOOLS_CONFIG_DISC = bytes([157, 20, 49, 224, 217, 87, 193, 254])
ORCA_WHIRLPOOL_BODY = 645
ORCA_POSITION_BODY = 208
ORCA_TICK_ARRAY_BODY = 9980
ORCA_FEE_TIER_BODY = 36
ORCA_WHIRLPOOLS_CONFIG_BODY = 98
ORCA_TICK_ARRAY_LEN = 88

T = TypeVar("T")


class Reader:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0

    def _take(self, size: int) -> int:
        if self.offset + size > len(self.data):
            raise ValueError("account data is truncated")
        start = self.offset
        self.offset += size
        return start

    def u8(self) -> int:
        return self.data[self._take(1)]

    def bool(self) -> bool:
        return self.u8() != 0

    def u16(self) -> int:
        return struct.unpack_from("<H", self.data, self._take(2))[0]

    def u32(self) -> int:
        return struct.unpack_from("<I", self.data, self._take(4))[0]

    def i32(self) -> int:
        return struct.unpack_from("<i", self.data, self._take(4))[0]

    def u64(self) -> int:
        return struct.unpack_from("<Q", self.data, self._take(8))[0]

    def u128(self) -> int:
        start = self._take(16)
        return int.from_bytes(self.data[start : start + 16], "little", signed=False)

    def i128(self) -> int:
        start = self._take(16)
        return int.from_bytes(self.data[start : start + 16], "little", signed=True)

    def pubkey(self) -> str:
        start = self._take(32)
        return base58.b58encode(self.data[start : start + 32]).decode("ascii")

    def bytes(self, length: int) -> list[int]:
        start = self._take(length)
        return list(self.data[start : start + length])


def _event(event_type: EventType, data: dict[str, Any]) -> DexEvent:
    return DexEvent(type=event_type, data=data)


def _parse_body(data: bytes, parse: Callable[[Reader], T]) -> Optional[T]:
    try:
        return parse(Reader(data))
    except (IndexError, struct.error, ValueError):
        return None


def _body_after_discriminator(data: bytes, disc: bytes, body_size: int) -> Optional[bytes]:
    if len(data) < 8 + body_size or not data.startswith(disc):
        return None
    return data[8:]


def _array(count: int, read: Callable[[], T]) -> list[T]:
    return [read() for _ in range(count)]


def parse_raydium_clmm_account(account: Any, metadata: EventMetadata) -> Optional[DexEvent]:
    if account.owner != RAYDIUM_CLMM_PROGRAM_ID:
        return None
    return (
        parse_raydium_clmm_amm_config(account, metadata)
        or parse_raydium_clmm_pool_state(account, metadata)
        or parse_raydium_clmm_tick_array_state(account, metadata)
    )


def parse_raydium_cpmm_account(account: Any, metadata: EventMetadata) -> Optional[DexEvent]:
    if account.owner != RAYDIUM_CPMM_PROGRAM_ID:
        return None
    return parse_raydium_cpmm_amm_config(account, metadata) or parse_raydium_cpmm_pool_state(
        account, metadata
    )


def parse_orca_whirlpool_account(account: Any, metadata: EventMetadata) -> Optional[DexEvent]:
    if account.owner != ORCA_WHIRLPOOL_PROGRAM_ID:
        return None
    return (
        parse_orca_whirlpool(account, metadata)
        or parse_orca_position(account, metadata)
        or parse_orca_tick_array(account, metadata)
        or parse_orca_fee_tier(account, metadata)
        or parse_orca_whirlpools_config(account, metadata)
    )


def parse_raydium_clmm_amm_config(account: Any, metadata: EventMetadata) -> Optional[DexEvent]:
    body = _body_after_discriminator(account.data, CLMM_AMM_CONFIG_DISC, CLMM_AMM_CONFIG_BODY)
    if body is None:
        return None
    amm_config = _parse_body(
        body,
        lambda r: {
            "bump": r.u8(),
            "index": r.u16(),
            "owner": r.pubkey(),
            "protocol_fee_rate": r.u32(),
            "trade_fee_rate": r.u32(),
            "tick_spacing": r.u16(),
            "fund_fee_rate": r.u32(),
            "padding_u32": r.u32(),
            "fund_owner": r.pubkey(),
            "padding": _array(3, r.u64),
        },
    )
    if amm_config is None:
        return None
    return _event(
        EventType.ACCOUNT_RAYDIUM_CLMM_AMM_CONFIG,
        {"metadata": metadata, "pubkey": account.pubkey, "amm_config": amm_config},
    )


def parse_raydium_clmm_pool_state(account: Any, metadata: EventMetadata) -> Optional[DexEvent]:
    body = _body_after_discriminator(account.data, CLMM_POOL_STATE_DISC, CLMM_POOL_STATE_BODY)
    if body is None:
        return None
    pool_state = _parse_body(body, _read_clmm_pool_state)
    if pool_state is None:
        return None
    return _event(
        EventType.ACCOUNT_RAYDIUM_CLMM_POOL_STATE,
        {"metadata": metadata, "pubkey": account.pubkey, "pool_state": pool_state},
    )


def _read_clmm_pool_state(r: Reader) -> dict[str, Any]:
    return {
        "bump": [r.u8()],
        "amm_config": r.pubkey(),
        "owner": r.pubkey(),
        "token_mint_0": r.pubkey(),
        "token_mint_1": r.pubkey(),
        "token_vault_0": r.pubkey(),
        "token_vault_1": r.pubkey(),
        "observation_key": r.pubkey(),
        "mint_decimals_0": r.u8(),
        "mint_decimals_1": r.u8(),
        "tick_spacing": r.u16(),
        "liquidity": r.u128(),
        "sqrt_price_x64": r.u128(),
        "tick_current": r.i32(),
        "padding3": r.u16(),
        "padding4": r.u16(),
        "fee_growth_global_0_x64": r.u128(),
        "fee_growth_global_1_x64": r.u128(),
        "protocol_fees_token_0": r.u64(),
        "protocol_fees_token_1": r.u64(),
        "padding5": _array(4, r.u128),
        "status": r.u8(),
        "fee_on": r.u8(),
        "padding": r.bytes(6),
        "reward_infos": _array(3, lambda: _read_clmm_reward_info(r)),
        "tick_array_bitmap": _array(16, r.u64),
        "padding6": _array(4, r.u64),
        "fund_fees_token_0": r.u64(),
        "fund_fees_token_1": r.u64(),
        "open_time": r.u64(),
        "recent_epoch": r.u64(),
        "dynamic_fee_info": _read_clmm_dynamic_fee_info(r),
        "padding1": _array(14, r.u64),
        "padding2": _array(32, r.u64),
    }


def parse_raydium_clmm_tick_array_state(account: Any, metadata: EventMetadata) -> Optional[DexEvent]:
    body = _body_after_discriminator(account.data, CLMM_TICK_ARRAY_STATE_DISC, CLMM_TICK_ARRAY_STATE_BODY)
    if body is None:
        return None
    tick_array_state = _parse_body(
        body,
        lambda r: {
            "pool_id": r.pubkey(),
            "start_tick_index": r.i32(),
            "ticks": _array(CLMM_TICK_ARRAY_LEN, lambda: _read_clmm_tick(r)),
            "initialized_tick_count": r.u8(),
            "recent_epoch": r.u64(),
            "padding": r.bytes(107),
        },
    )
    if tick_array_state is None:
        return None
    return _event(
        EventType.ACCOUNT_RAYDIUM_CLMM_TICK_ARRAY_STATE,
        {"metadata": metadata, "pubkey": account.pubkey, "tick_array_state": tick_array_state},
    )


def _read_clmm_reward_info(r: Reader) -> dict[str, Any]:
    return {
        "reward_state": r.u8(),
        "open_time": r.u64(),
        "end_time": r.u64(),
        "last_update_time": r.u64(),
        "emissions_per_second_x64": r.u128(),
        "reward_total_emitted": r.u64(),
        "reward_claimed": r.u64(),
        "token_mint": r.pubkey(),
        "token_vault": r.pubkey(),
        "authority": r.pubkey(),
        "reward_growth_global_x64": r.u128(),
    }


def _read_clmm_dynamic_fee_info(r: Reader) -> dict[str, Any]:
    return {
        "filter_period": r.u16(),
        "decay_period": r.u16(),
        "reduction_factor": r.u16(),
        "dynamic_fee_control": r.u32(),
        "max_volatility_accumulator": r.u32(),
        "tick_spacing_index_reference": r.i32(),
        "volatility_reference": r.u32(),
        "volatility_accumulator": r.u32(),
        "last_update_timestamp": r.u64(),
        "padding": r.bytes(46),
    }


def _read_clmm_tick(r: Reader) -> dict[str, Any]:
    return {
        "tick": r.i32(),
        "liquidity_net": r.i128(),
        "liquidity_gross": r.u128(),
        "fee_growth_outside_0_x64": r.u128(),
        "fee_growth_outside_1_x64": r.u128(),
        "reward_growths_outside_x64": _array(3, r.u128),
        "order_phase": r.u64(),
        "orders_amount": r.u64(),
        "part_filled_orders_remaining": r.u64(),
        "unfilled_ratio_x64": r.u128(),
        "padding": _array(3, r.u32),
    }


def parse_raydium_cpmm_amm_config(account: Any, metadata: EventMetadata) -> Optional[DexEvent]:
    body = _body_after_discriminator(account.data, CPMM_AMM_CONFIG_DISC, CPMM_AMM_CONFIG_BODY)
    if body is None:
        return None
    amm_config = _parse_body(
        body,
        lambda r: {
            "bump": r.u8(),
            "disable_create_pool": r.bool(),
            "index": r.u16(),
            "trade_fee_rate": r.u64(),
            "protocol_fee_rate": r.u64(),
            "fund_fee_rate": r.u64(),
            "create_pool_fee": r.u64(),
            "protocol_owner": r.pubkey(),
            "fund_owner": r.pubkey(),
            "creator_fee_rate": r.u64(),
            "padding": _array(15, r.u64),
        },
    )
    if amm_config is None:
        return None
    return _event(
        EventType.ACCOUNT_RAYDIUM_CPMM_AMM_CONFIG,
        {"metadata": metadata, "pubkey": account.pubkey, "amm_config": amm_config},
    )


def parse_raydium_cpmm_pool_state(account: Any, metadata: EventMetadata) -> Optional[DexEvent]:
    body = _body_after_discriminator(account.data, CPMM_POOL_STATE_DISC, CPMM_POOL_STATE_BODY)
    if body is None:
        return None
    pool_state = _parse_body(body, _read_cpmm_pool_state)
    if pool_state is None:
        return None
    return _event(
        EventType.ACCOUNT_RAYDIUM_CPMM_POOL_STATE,
        {"metadata": metadata, "pubkey": account.pubkey, "pool_state": pool_state},
    )


def _read_cpmm_pool_state(r: Reader) -> dict[str, Any]:
    return {
        "amm_config": r.pubkey(),
        "pool_creator": r.pubkey(),
        "token_0_vault": r.pubkey(),
        "token_1_vault": r.pubkey(),
        "lp_mint": r.pubkey(),
        "token_0_mint": r.pubkey(),
        "token_1_mint": r.pubkey(),
        "token_0_program": r.pubkey(),
        "token_1_program": r.pubkey(),
        "observation_key": r.pubkey(),
        "auth_bump": r.u8(),
        "status": r.u8(),
        "lp_mint_decimals": r.u8(),
        "mint_0_decimals": r.u8(),
        "mint_1_decimals": r.u8(),
        "lp_supply": r.u64(),
        "protocol_fees_token_0": r.u64(),
        "protocol_fees_token_1": r.u64(),
        "fund_fees_token_0": r.u64(),
        "fund_fees_token_1": r.u64(),
        "open_time": r.u64(),
        "recent_epoch": r.u64(),
        "creator_fee_on": r.u8(),
        "enable_creator_fee": r.bool(),
        "padding1": r.bytes(6),
        "creator_fees_token_0": r.u64(),
        "creator_fees_token_1": r.u64(),
        "padding": _array(28, r.u64),
    }


def parse_orca_whirlpool(account: Any, metadata: EventMetadata) -> Optional[DexEvent]:
    body = _body_after_discriminator(account.data, ORCA_WHIRLPOOL_DISC, ORCA_WHIRLPOOL_BODY)
    if body is None:
        return None
    whirlpool = _parse_body(
        body,
        lambda r: {
            "whirlpools_config": r.pubkey(),
            "whirlpool_bump": r.u8(),
            "tick_spacing": r.u16(),
            "tick_spacing_seed": r.bytes(2),
            "fee_rate": r.u16(),
            "protocol_fee_rate": r.u16(),
            "liquidity": r.u128(),
            "sqrt_price": r.u128(),
            "tick_current_index": r.i32(),
            "protocol_fee_owed_a": r.u64(),
            "protocol_fee_owed_b": r.u64(),
            "token_mint_a": r.pubkey(),
            "token_vault_a": r.pubkey(),
            "fee_growth_global_a": r.u128(),
            "token_mint_b": r.pubkey(),
            "token_vault_b": r.pubkey(),
            "fee_growth_global_b": r.u128(),
            "reward_last_updated_timestamp": r.u64(),
            "reward_infos": _array(3, lambda: _read_orca_whirlpool_reward_info(r)),
        },
    )
    if whirlpool is None:
        return None
    return _event(
        EventType.ACCOUNT_ORCA_WHIRLPOOL,
        {"metadata": metadata, "pubkey": account.pubkey, "whirlpool": whirlpool},
    )


def parse_orca_position(account: Any, metadata: EventMetadata) -> Optional[DexEvent]:
    body = _body_after_discriminator(account.data, ORCA_POSITION_DISC, ORCA_POSITION_BODY)
    if body is None:
        return None
    position = _parse_body(
        body,
        lambda r: {
            "whirlpool": r.pubkey(),
            "position_mint": r.pubkey(),
            "liquidity": r.u128(),
            "tick_lower_index": r.i32(),
            "tick_upper_index": r.i32(),
            "fee_growth_checkpoint_a": r.u128(),
            "fee_owed_a": r.u64(),
            "fee_growth_checkpoint_b": r.u128(),
            "fee_owed_b": r.u64(),
            "reward_infos": _array(3, lambda: _read_orca_position_reward_info(r)),
        },
    )
    if position is None:
        return None
    return _event(
        EventType.ACCOUNT_ORCA_POSITION,
        {"metadata": metadata, "pubkey": account.pubkey, "position": position},
    )


def parse_orca_tick_array(account: Any, metadata: EventMetadata) -> Optional[DexEvent]:
    body = _body_after_discriminator(account.data, ORCA_TICK_ARRAY_DISC, ORCA_TICK_ARRAY_BODY)
    if body is None:
        return None
    tick_array = _parse_body(
        body,
        lambda r: {
            "start_tick_index": r.i32(),
            "ticks": _array(ORCA_TICK_ARRAY_LEN, lambda: _read_orca_tick(r)),
            "whirlpool": r.pubkey(),
        },
    )
    if tick_array is None:
        return None
    return _event(
        EventType.ACCOUNT_ORCA_TICK_ARRAY,
        {"metadata": metadata, "pubkey": account.pubkey, "tick_array": tick_array},
    )


def parse_orca_fee_tier(account: Any, metadata: EventMetadata) -> Optional[DexEvent]:
    body = _body_after_discriminator(account.data, ORCA_FEE_TIER_DISC, ORCA_FEE_TIER_BODY)
    if body is None:
        return None
    fee_tier = _parse_body(
        body,
        lambda r: {
            "whirlpools_config": r.pubkey(),
            "tick_spacing": r.u16(),
            "default_fee_rate": r.u16(),
        },
    )
    if fee_tier is None:
        return None
    return _event(
        EventType.ACCOUNT_ORCA_FEE_TIER,
        {"metadata": metadata, "pubkey": account.pubkey, "fee_tier": fee_tier},
    )


def parse_orca_whirlpools_config(account: Any, metadata: EventMetadata) -> Optional[DexEvent]:
    body = _body_after_discriminator(account.data, ORCA_WHIRLPOOLS_CONFIG_DISC, ORCA_WHIRLPOOLS_CONFIG_BODY)
    if body is None:
        return None
    config = _parse_body(
        body,
        lambda r: {
            "fee_authority": r.pubkey(),
            "collect_protocol_fees_authority": r.pubkey(),
            "reward_emissions_super_authority": r.pubkey(),
            "default_protocol_fee_rate": r.u16(),
        },
    )
    if config is None:
        return None
    return _event(
        EventType.ACCOUNT_ORCA_WHIRLPOOLS_CONFIG,
        {"metadata": metadata, "pubkey": account.pubkey, "config": config},
    )


def _read_orca_whirlpool_reward_info(r: Reader) -> dict[str, Any]:
    return {
        "mint": r.pubkey(),
        "vault": r.pubkey(),
        "authority": r.pubkey(),
        "emissions_per_second_x64": r.u128(),
        "growth_global_x64": r.u128(),
    }


def _read_orca_position_reward_info(r: Reader) -> dict[str, Any]:
    return {
        "growth_inside_checkpoint": r.u128(),
        "amount_owed": r.u64(),
    }


def _read_orca_tick(r: Reader) -> dict[str, Any]:
    return {
        "initialized": r.bool(),
        "liquidity_net": r.i128(),
        "liquidity_gross": r.u128(),
        "fee_growth_outside_a": r.u128(),
        "fee_growth_outside_b": r.u128(),
        "reward_growths_outside": _array(3, r.u128),
    }
