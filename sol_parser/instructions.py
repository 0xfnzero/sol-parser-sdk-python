"""指令解析器 - 对齐 Rust 实现"""

from __future__ import annotations

import struct
from typing import Optional, List

from .grpc_types import EventTypeFilter, EventType, EventMetadata
from .dex_parsers import Z
from .event_types import DexEvent, PumpFunCreateEvent, PumpFunCreateV2TokenEvent, legacy_dict_to_dex_event

# 程序 ID 常量（与 Rust ``instr::program_ids`` 一致，用于 inner / outer 路由）
PUMPFUN_PROGRAM_ID = "6EF8rrecthR5Dkzon8Nwu78hRvfCKubJ14M5uBEwF6P"
PUMPSWAP_PROGRAM_ID = "pAMMBay6oceH9fJKBRHGP5D4bD4sWpmSwMn52FMfXEA"
METEORA_DAMM_V2_PROGRAM_ID = "cpamdpZCGKUy5JxQXB4dcpGPiikHawvSWAd6mEn1sGG"
RAYDIUM_CLMM_PROGRAM_ID = "CAMMCzo5YL8w4VFF8KVHrK22GGUQtcaMpgYqJPXBDvfE"
RAYDIUM_CPMM_PROGRAM_ID = "CPMMoo8L3F4NbTegBCKVNunggL7H1ZpdTHKxQB5qKP1C"
RAYDIUM_AMM_V4_PROGRAM_ID = "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"
ORCA_WHIRLPOOL_PROGRAM_ID = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
METEORA_POOLS_PROGRAM_ID = "Eo7WjKq67rjJQSZxS6z3YkapzY3eMj6Xy8X5EQVn5UaB"
METEORA_DLMM_PROGRAM_ID = "LBUZKhRxPF3XUpBCjp4YzTKgLccjZhTSDM9YuVaPwxo"
BONK_LAUNCHPAD_PROGRAM_ID = "DjVE6JNiYqPL2QXyCUUh8rNjHrbz9hXHNYt99MQ59qw1"
PUMPSWAP_FEES_PROGRAM_ID = "pfeeUxB6jkeY1Hxd7CsFCAjcbHA9rWtchMGdZ6VojVZ"


def _d(*xs: int) -> int:
    return struct.unpack("<Q", bytes(xs))[0]


# Discriminator 常量
_DISC_PUMPSWAP_BUY  = _d(103, 244, 82, 31, 44, 245, 119, 119)
_DISC_PUMPSWAP_SELL = _d(62, 47, 55, 10, 165, 3, 220, 42)

_DISC_DAMM_SWAP    = _d(27, 60, 21, 213, 138, 170, 187, 147)
_DISC_DAMM_SWAP2   = _d(189, 66, 51, 168, 38, 80, 117, 153)
_DISC_DAMM_ADD_LIQ = _d(175, 242, 8, 157, 30, 247, 185, 169)
_DISC_DAMM_REM_LIQ = _d(87, 46, 88, 98, 175, 96, 34, 91)
_DISC_DAMM_CREATE  = _d(156, 15, 119, 198, 29, 181, 221, 55)
_DISC_DAMM_CLOSE   = _d(20, 145, 144, 68, 143, 142, 214, 178)
_DISC_DAMM_INIT    = _d(228, 50, 246, 85, 203, 66, 134, 37)

_DISC_CLMM_SWAP    = _d(248, 198, 158, 145, 225, 117, 135, 200)
_DISC_CLMM_INC_LIQ = _d(133, 29, 89, 223, 69, 238, 176, 10)
_DISC_CLMM_DEC_LIQ = _d(160, 38, 208, 111, 104, 91, 44, 1)
_DISC_CLMM_CREATE  = _d(233, 146, 209, 142, 207, 104, 64, 188)

_DISC_CPMM_SWAP    = _d(143, 190, 90, 218, 196, 30, 51, 222)
_DISC_CPMM_DEP     = _d(242, 35, 198, 137, 82, 225, 242, 182)
_DISC_CPMM_WIT     = _d(183, 18, 70, 156, 148, 109, 161, 34)

_DISC_ORCA_SWAP    = _d(225, 202, 73, 175, 147, 43, 160, 150)
_DISC_ORCA_INC_LIQ = _d(30, 7, 144, 181, 102, 254, 155, 161)
_DISC_ORCA_DEC_LIQ = _d(166, 1, 36, 71, 112, 202, 181, 171)

_DISC_BONK_TRADE       = _d(2, 3, 4, 5, 6, 7, 8, 9)
_DISC_BONK_POOL_CREATE = _d(1, 2, 3, 4, 5, 6, 7, 8)


def _get_account_safe(accounts: List[str], index: int) -> str:
    """安全获取账户地址"""
    if index < 0 or index >= len(accounts):
        return Z
    return accounts[index]


def _make_meta(
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> EventMetadata:
    return EventMetadata(
        signature=signature,
        slot=slot,
        tx_index=tx_index,
        block_time_us=block_time_us or 0,
        grpc_recv_us=grpc_recv_us,
    )


def parse_instruction_unified(
    instruction_data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
    filter: EventTypeFilter,
    program_id: str,
) -> Optional[DexEvent]:
    """统一的指令解析入口

    对齐 Rust `parse_instruction_unified`
    """
    if not instruction_data:
        return None

    if program_id == PUMPFUN_PROGRAM_ID:
        if not _filter_includes_pumpfun(filter):
            return None
        return parse_pumpfun_instruction(
            instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
        )

    elif program_id == PUMPSWAP_PROGRAM_ID:
        if not _filter_includes_pumpswap(filter):
            return None
        return parse_pumpswap_instruction(
            instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
        )

    elif program_id == METEORA_DAMM_V2_PROGRAM_ID:
        if not _filter_includes_meteora_damm_v2(filter):
            return None
        return parse_meteora_damm_instruction(
            instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
        )

    elif program_id == RAYDIUM_CLMM_PROGRAM_ID:
        if not _filter_includes_raydium_clmm(filter):
            return None
        return parse_raydium_clmm_instruction(
            instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
        )

    elif program_id == RAYDIUM_CPMM_PROGRAM_ID:
        if not _filter_includes_raydium_cpmm(filter):
            return None
        return parse_raydium_cpmm_instruction(
            instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
        )

    elif program_id == RAYDIUM_AMM_V4_PROGRAM_ID:
        if not _filter_includes_raydium_amm_v4(filter):
            return None
        return parse_raydium_amm_v4_instruction(
            instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
        )

    elif program_id == ORCA_WHIRLPOOL_PROGRAM_ID:
        if not _filter_includes_orca_whirlpool(filter):
            return None
        return parse_orca_whirlpool_instruction(
            instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
        )

    elif program_id == BONK_LAUNCHPAD_PROGRAM_ID:
        if not _filter_includes_bonk(filter):
            return None
        return parse_bonk_instruction(
            instruction_data, accounts, signature, slot, tx_index, block_time_us, grpc_recv_us
        )

    return None


def parse_pumpfun_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 PumpFun 指令
    
    注意：PumpFun 的 Buy/Sell 操作通过统一的 TRADE 日志事件捕获，
    在 dex_parsers.py 的 parse_trade_from_data 中处理。
    这里只处理 Create 和 CreateV2 指令。
    
    Discriminators（8字节小端）：
    - CREATE: [24, 30, 200, 40, 5, 28, 7, 119] = 8576854823835016728
    - CREATE_V2: [214, 144, 76, 236, 95, 139, 49, 180] = 12992944682502211062
    """
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    # PumpFun Create: [24, 30, 200, 40, 5, 28, 7, 119]
    if discriminator == 8576854823835016728:
        return _parse_pumpfun_create(data, accounts, meta)

    # PumpFun CreateV2: [214, 144, 76, 236, 95, 139, 49, 180]
    if discriminator == 12992944682502211062:
        return _parse_pumpfun_create_v2(data, accounts, meta)

    # BUY/SELL 是日志事件 discriminator，不是指令 discriminator
    # 交易事件在 dex_parsers.py 的 parse_trade_from_data 中处理

    return None


def _parse_pumpfun_create(data: bytes, accounts: List[str], meta: EventMetadata) -> Optional[DexEvent]:
    """解析 PumpFun Create 指令"""
    offset = 8  # Skip discriminator
    try:
        name_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        name = data[offset:offset + name_len].decode('utf-8')
        offset += name_len

        symbol_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        symbol = data[offset:offset + symbol_len].decode('utf-8')
        offset += symbol_len

        uri_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        uri = data[offset:offset + uri_len].decode('utf-8')
        offset += uri_len
    except Exception:
        return None

    creator = Z
    if offset + 32 <= len(data):
        import base58
        creator = base58.b58encode(data[offset:offset + 32]).decode('ascii')

    return DexEvent(
        type=EventType.PUMP_FUN_CREATE,
        data=PumpFunCreateEvent(
            metadata=meta,
            name=name,
            symbol=symbol,
            uri=uri,
            mint=_get_account_safe(accounts, 0),
            bonding_curve=_get_account_safe(accounts, 2),
            user=_get_account_safe(accounts, 7),
            creator=creator,
            token_program=Z,
            timestamp=0,
            virtual_token_reserves=0,
            virtual_sol_reserves=0,
            real_token_reserves=0,
            token_total_supply=0,
            is_mayhem_mode=False,
            is_cashback_enabled=False,
        ),
    )


def _parse_pumpfun_create_v2(data: bytes, accounts: List[str], meta: EventMetadata) -> Optional[DexEvent]:
    """解析 PumpFun CreateV2 指令
    
    对齐 TS pumpfun_ix.ts CREATE_V2 处理
    """
    if len(accounts) < 16:
        return None
        
    offset = 8  # Skip discriminator
    try:
        name_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        name = data[offset:offset + name_len].decode('utf-8')
        offset += name_len

        symbol_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        symbol = data[offset:offset + symbol_len].decode('utf-8')
        offset += symbol_len

        uri_len = struct.unpack_from("<I", data, offset)[0]
        offset += 4
        uri = data[offset:offset + uri_len].decode('utf-8')
        offset += uri_len
    except Exception:
        return None

    creator = Z
    if offset + 32 <= len(data):
        import base58
        creator = base58.b58encode(data[offset:offset + 32]).decode('ascii')

    return DexEvent(
        type=EventType.PUMP_FUN_CREATE_V2,
        data=PumpFunCreateV2TokenEvent(
            metadata=meta,
            name=name,
            symbol=symbol,
            uri=uri,
            mint=_get_account_safe(accounts, 0),
            mint_authority=_get_account_safe(accounts, 1),
            bonding_curve=_get_account_safe(accounts, 2),
            associated_bonding_curve=_get_account_safe(accounts, 3),
            global_account=_get_account_safe(accounts, 4),
            user=_get_account_safe(accounts, 5),
            system_program=_get_account_safe(accounts, 6),
            token_program=_get_account_safe(accounts, 7),
            associated_token_program=_get_account_safe(accounts, 8),
            mayhem_program_id=_get_account_safe(accounts, 9),
            global_params=_get_account_safe(accounts, 10),
            sol_vault=_get_account_safe(accounts, 11),
            mayhem_state=_get_account_safe(accounts, 12),
            mayhem_token_vault=_get_account_safe(accounts, 13),
            event_authority=_get_account_safe(accounts, 14),
            program=_get_account_safe(accounts, 15),
            creator=creator,
            timestamp=0,
            virtual_token_reserves=0,
            virtual_sol_reserves=0,
            real_token_reserves=0,
            token_total_supply=0,
            is_mayhem_mode=False,
            is_cashback_enabled=False,
            observed_fee_recipient="",
        ),
    )


def parse_pumpswap_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 PumpSwap 指令"""
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if discriminator == _DISC_PUMPSWAP_BUY:
        return legacy_dict_to_dex_event({"PumpSwapBuy": {"metadata": meta}})
    if discriminator == _DISC_PUMPSWAP_SELL:
        return legacy_dict_to_dex_event({"PumpSwapSell": {"metadata": meta}})

    return None


def parse_meteora_damm_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 Meteora DAMM V2 指令"""
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if discriminator in (_DISC_DAMM_SWAP, _DISC_DAMM_SWAP2):
        return legacy_dict_to_dex_event({"MeteoraDammV2Swap": {"metadata": meta}})
    if discriminator == _DISC_DAMM_ADD_LIQ:
        return legacy_dict_to_dex_event({"MeteoraDammV2AddLiquidity": {"metadata": meta}})
    if discriminator == _DISC_DAMM_REM_LIQ:
        return legacy_dict_to_dex_event({"MeteoraDammV2RemoveLiquidity": {"metadata": meta}})
    if discriminator == _DISC_DAMM_CREATE:
        return legacy_dict_to_dex_event({"MeteoraDammV2CreatePosition": {"metadata": meta}})
    if discriminator == _DISC_DAMM_CLOSE:
        return legacy_dict_to_dex_event({"MeteoraDammV2ClosePosition": {"metadata": meta}})
    if discriminator == _DISC_DAMM_INIT:
        return legacy_dict_to_dex_event({"MeteoraDammV2InitializePool": {"metadata": meta}})

    return None


def parse_raydium_clmm_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 Raydium CLMM 指令"""
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if discriminator == _DISC_CLMM_SWAP:
        return legacy_dict_to_dex_event({"RaydiumClmmSwap": {
            "metadata": meta,
            "pool_state": _get_account_safe(accounts, 2),
            "sender": _get_account_safe(accounts, 0),
            "token_account_0": Z, "token_account_1": Z,
            "amount_0": 0, "amount_1": 0, "zero_for_one": False,
            "sqrt_price_x64": "0", "liquidity": "0",
            "transfer_fee_0": 0, "transfer_fee_1": 0, "tick": 0,
        }})
    if discriminator == _DISC_CLMM_INC_LIQ:
        return legacy_dict_to_dex_event({"RaydiumClmmIncreaseLiquidity": {
            "metadata": meta,
            "pool": _get_account_safe(accounts, 3),
            "position_nft_mint": Z,
            "user": _get_account_safe(accounts, 0),
            "liquidity": "0", "amount0_max": 0, "amount1_max": 0,
        }})
    if discriminator == _DISC_CLMM_DEC_LIQ:
        return legacy_dict_to_dex_event({"RaydiumClmmDecreaseLiquidity": {
            "metadata": meta,
            "pool": _get_account_safe(accounts, 3),
            "position_nft_mint": Z,
            "user": _get_account_safe(accounts, 0),
            "liquidity": "0", "amount0_min": 0, "amount1_min": 0,
        }})
    if discriminator == _DISC_CLMM_CREATE:
        return legacy_dict_to_dex_event({"RaydiumClmmCreatePool": {
            "metadata": meta,
            "pool": _get_account_safe(accounts, 4),
            "creator": _get_account_safe(accounts, 0),
            "token_0_mint": Z, "token_1_mint": Z,
            "tick_spacing": 0, "fee_rate": 0, "sqrt_price_x64": "0", "open_time": 0,
        }})

    return None


def parse_raydium_cpmm_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 Raydium CPMM 指令"""
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if discriminator == _DISC_CPMM_SWAP:
        return legacy_dict_to_dex_event({"RaydiumCpmmSwap": {
            "metadata": meta,
            "pool_id": _get_account_safe(accounts, 2),
            "input_amount": 0, "output_amount": 0,
            "input_vault_before": 0, "output_vault_before": 0,
            "input_transfer_fee": 0, "output_transfer_fee": 0,
            "base_input": True,
        }})
    if discriminator == _DISC_CPMM_DEP:
        return legacy_dict_to_dex_event({"RaydiumCpmmDeposit": {
            "metadata": meta,
            "pool": _get_account_safe(accounts, 2),
            "user": _get_account_safe(accounts, 0),
            "lp_token_amount": 0, "token0_amount": 0, "token1_amount": 0,
        }})
    if discriminator == _DISC_CPMM_WIT:
        return legacy_dict_to_dex_event({"RaydiumCpmmWithdraw": {
            "metadata": meta,
            "pool": _get_account_safe(accounts, 2),
            "user": _get_account_safe(accounts, 0),
            "lp_token_amount": 0, "token0_amount": 0, "token1_amount": 0,
        }})

    return None


def parse_raydium_amm_v4_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 Raydium AMM V4 指令（单字节 discriminator）"""
    if len(data) < 1:
        return None

    instr_type = data[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if instr_type in (9, 11):  # SwapBaseIn / SwapBaseOut
        return legacy_dict_to_dex_event({"RaydiumAmmV4Swap": {
            "metadata": meta,
            "amm": _get_account_safe(accounts, 1),
            "user_source_owner": _get_account_safe(accounts, 17),
            "amount_in": 0, "minimum_amount_out": 0,
            "max_amount_in": 0, "amount_out": 0,
            "token_program": Z, "amm_authority": Z, "amm_open_orders": Z,
            "pool_coin_token_account": Z, "pool_pc_token_account": Z,
            "serum_program": Z, "serum_market": Z, "serum_bids": Z,
            "serum_asks": Z, "serum_event_queue": Z,
            "serum_coin_vault_account": Z, "serum_pc_vault_account": Z,
            "serum_vault_signer": Z,
            "user_source_token_account": Z,
            "user_destination_token_account": Z,
        }})

    return None


def parse_orca_whirlpool_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 Orca Whirlpool 指令"""
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if discriminator == _DISC_ORCA_SWAP:
        return legacy_dict_to_dex_event({"OrcaWhirlpoolSwap": {
            "metadata": meta,
            "whirlpool": _get_account_safe(accounts, 2),
            "a_to_b": True,
            "pre_sqrt_price": "0", "post_sqrt_price": "0",
            "input_amount": 0, "output_amount": 0,
            "input_transfer_fee": 0, "output_transfer_fee": 0,
            "lp_fee": 0, "protocol_fee": 0,
        }})
    if discriminator == _DISC_ORCA_INC_LIQ:
        return legacy_dict_to_dex_event({"OrcaWhirlpoolLiquidityIncreased": {
            "metadata": meta,
            "whirlpool": _get_account_safe(accounts, 1),
            "position": _get_account_safe(accounts, 3),
            "tick_lower_index": 0, "tick_upper_index": 0,
            "liquidity": "0",
            "token_a_amount": 0, "token_b_amount": 0,
            "token_a_transfer_fee": 0, "token_b_transfer_fee": 0,
        }})
    if discriminator == _DISC_ORCA_DEC_LIQ:
        return legacy_dict_to_dex_event({"OrcaWhirlpoolLiquidityDecreased": {
            "metadata": meta,
            "whirlpool": _get_account_safe(accounts, 1),
            "position": _get_account_safe(accounts, 3),
            "tick_lower_index": 0, "tick_upper_index": 0,
            "liquidity": "0",
            "token_a_amount": 0, "token_b_amount": 0,
            "token_a_transfer_fee": 0, "token_b_transfer_fee": 0,
        }})

    return None


def parse_bonk_instruction(
    data: bytes,
    accounts: List[str],
    signature: str,
    slot: int,
    tx_index: int,
    block_time_us: Optional[int],
    grpc_recv_us: int,
) -> Optional[DexEvent]:
    """解析 Bonk (Raydium Launchpad) 指令"""
    if len(data) < 8:
        return None

    discriminator = struct.unpack_from("<Q", data, 0)[0]
    meta = _make_meta(signature, slot, tx_index, block_time_us, grpc_recv_us)

    if discriminator == _DISC_BONK_TRADE:
        return legacy_dict_to_dex_event({"BonkTrade": {
            "metadata": meta,
            "pool_state": _get_account_safe(accounts, 1),
            "user": _get_account_safe(accounts, 0),
            "amount_in": 0, "amount_out": 0,
            "is_buy": True, "trade_direction": "Buy", "exact_in": True,
        }})
    if discriminator == _DISC_BONK_POOL_CREATE:
        return legacy_dict_to_dex_event({"BonkPoolCreate": {
            "metadata": meta,
            "base_mint_param": {"symbol": "BONK", "name": "Bonk Pool", "uri": "https://bonk.com", "decimals": 5},
            "pool_state": _get_account_safe(accounts, 1),
            "creator": _get_account_safe(accounts, 8),
        }})

    return None


# --- 过滤器辅助函数 ---

def _filter_includes_pumpfun(filter: EventTypeFilter) -> bool:
    pumpfun_types = [
        EventType.PUMP_FUN_TRADE, EventType.PUMP_FUN_BUY, EventType.PUMP_FUN_SELL,
        EventType.PUMP_FUN_BUY_EXACT_SOL_IN, EventType.PUMP_FUN_CREATE,
        EventType.PUMP_FUN_CREATE_V2, EventType.PUMP_FUN_COMPLETE, EventType.PUMP_FUN_MIGRATE,
    ]
    return any(filter.should_include(t) for t in pumpfun_types)


def _filter_includes_pumpswap(filter: EventTypeFilter) -> bool:
    pumpswap_types = [
        EventType.PUMP_SWAP_BUY, EventType.PUMP_SWAP_SELL,
        EventType.PUMP_SWAP_CREATE_POOL, EventType.PUMP_SWAP_LIQUIDITY_ADDED,
        EventType.PUMP_SWAP_LIQUIDITY_REMOVED,
    ]
    return any(filter.should_include(t) for t in pumpswap_types)


def _filter_includes_meteora_damm_v2(filter: EventTypeFilter) -> bool:
    meteora_types = [
        EventType.METEORA_DAMM_V2_SWAP, EventType.METEORA_DAMM_V2_ADD_LIQUIDITY,
        EventType.METEORA_DAMM_V2_CREATE_POSITION, EventType.METEORA_DAMM_V2_CLOSE_POSITION,
        EventType.METEORA_DAMM_V2_INITIALIZE_POOL, EventType.METEORA_DAMM_V2_REMOVE_LIQUIDITY,
    ]
    return any(filter.should_include(t) for t in meteora_types)


def _filter_includes_raydium_clmm(filter: EventTypeFilter) -> bool:
    types = [
        EventType.RAYDIUM_CLMM_SWAP, EventType.RAYDIUM_CLMM_INCREASE_LIQUIDITY,
        EventType.RAYDIUM_CLMM_DECREASE_LIQUIDITY, EventType.RAYDIUM_CLMM_CREATE_POOL,
        EventType.RAYDIUM_CLMM_OPEN_POSITION, EventType.RAYDIUM_CLMM_CLOSE_POSITION,
        EventType.RAYDIUM_CLMM_COLLECT_FEE,
    ]
    return any(filter.should_include(t) for t in types)


def _filter_includes_raydium_cpmm(filter: EventTypeFilter) -> bool:
    types = [
        EventType.RAYDIUM_CPMM_SWAP, EventType.RAYDIUM_CPMM_DEPOSIT,
        EventType.RAYDIUM_CPMM_WITHDRAW, EventType.RAYDIUM_CPMM_INITIALIZE,
    ]
    return any(filter.should_include(t) for t in types)


def _filter_includes_raydium_amm_v4(filter: EventTypeFilter) -> bool:
    types = [
        EventType.RAYDIUM_AMM_V4_SWAP, EventType.RAYDIUM_AMM_V4_DEPOSIT,
        EventType.RAYDIUM_AMM_V4_WITHDRAW,
    ]
    return any(filter.should_include(t) for t in types)


def _filter_includes_orca_whirlpool(filter: EventTypeFilter) -> bool:
    types = [
        EventType.ORCA_WHIRLPOOL_SWAP, EventType.ORCA_WHIRLPOOL_LIQUIDITY_INCREASED,
        EventType.ORCA_WHIRLPOOL_LIQUIDITY_DECREASED, EventType.ORCA_WHIRLPOOL_POOL_INITIALIZED,
    ]
    return any(filter.should_include(t) for t in types)


def _filter_includes_bonk(filter: EventTypeFilter) -> bool:
    types = [
        EventType.BONK_TRADE, EventType.BONK_POOL_CREATE, EventType.BONK_MIGRATE_AMM,
    ]
    return any(filter.should_include(t) for t in types)


__all__ = [
    "parse_instruction_unified",
    "parse_pumpfun_instruction",
    "parse_pumpswap_instruction",
    "parse_meteora_damm_instruction",
    "parse_raydium_clmm_instruction",
    "parse_raydium_cpmm_instruction",
    "parse_raydium_amm_v4_instruction",
    "parse_orca_whirlpool_instruction",
    "parse_bonk_instruction",
]
