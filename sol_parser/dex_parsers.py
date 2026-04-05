"""与 `sol-parser-sdk-golang/solparser` matcher 对齐的程序数据解析（Program data 行）。

由小端 u128 承载的语义字段（Meteora DAMM v2、Raydium CLMM、Orca Whirlpool、Meteora DLMM Swap 的 `fee_bps` 等）
在 Python 结果里为 **十进制字符串**，与 TS `bigint` 十进制及 Go `u128LEDecimalString` 一致。
`python3 -m sol_parser.check_migration` 会额外跑 `u128_parity`（标量 + Orca 合成用例）。
"""

from __future__ import annotations

import struct
from typing import Any, Dict, List, Optional

import base58

DexEvent = Dict[str, Any]
Z = "11111111111111111111111111111111"


def _u64le(b: bytes, o: int) -> int:
    return struct.unpack_from("<Q", b, o)[0]


def _i64le(b: bytes, o: int) -> int:
    return struct.unpack_from("<q", b, o)[0]


def _i32le(b: bytes, o: int) -> int:
    return struct.unpack_from("<i", b, o)[0]


def _u32le(b: bytes, o: int) -> int:
    return struct.unpack_from("<I", b, o)[0]


def _u16le(b: bytes, o: int) -> int:
    return struct.unpack_from("<H", b, o)[0]


def _u8(b: bytes, o: int) -> int:
    return b[o]


def _pub(b: bytes, o: int) -> str:
    return base58.b58encode(b[o : o + 32]).decode()


def _bool(b: bytes, o: int) -> bool:
    return b[o] == 1


def _u128le_int(b: bytes, o: int) -> int:
    return int.from_bytes(b[o : o + 16], "little")


def _borsh_str(b: bytes, o: int) -> tuple[str, int]:
    (n,) = struct.unpack_from("<I", b, o)
    o += 4
    return b[o : o + n].decode("utf-8", errors="replace"), o + n


def _disc8(bs: bytes) -> int:
    return struct.unpack("<Q", bs)[0]


def _d(*xs: int) -> int:
    return struct.unpack("<Q", bytes(xs))[0]


def _u64_at(b: bytes, o: List[int]) -> int:
    v = _u64le(b, o[0])
    o[0] += 8
    return v


# --- PumpFun ---

PUMP_TRADE = _d(189, 219, 127, 211, 78, 230, 97, 238)
PUMP_CREATE = _d(27, 114, 169, 77, 222, 235, 99, 118)
PUMP_MIGRATE = _d(189, 233, 93, 185, 92, 148, 234, 148)


def parse_trade_from_data(data: bytes, meta: dict, is_created_buy: bool) -> Optional[DexEvent]:
    if len(data) < 200:
        return None
    o = 0
    mint = _pub(data, o)
    o += 32
    sol_amount = _u64le(data, o)
    o += 8
    token_amount = _u64le(data, o)
    o += 8
    is_buy = _bool(data, o)
    o += 1
    user = _pub(data, o)
    o += 32
    ts = _i64le(data, o)
    o += 8
    vsol = _u64le(data, o)
    o += 8
    vtok = _u64le(data, o)
    o += 8
    rsol = _u64le(data, o)
    o += 8
    rtok = _u64le(data, o)
    o += 8
    fee_rec = _pub(data, o)
    o += 32
    fee_bps = _u64le(data, o)
    o += 8
    fee = _u64le(data, o)
    o += 8
    creator = _pub(data, o)
    o += 32
    cfbps = _u64le(data, o)
    o += 8
    cfee = _u64le(data, o)
    o += 8
    tv = _bool(data, o) if o < len(data) else False
    o += 1
    tuc = _u64le(data, o) if o + 8 <= len(data) else 0
    o += 8
    tcc = _u64le(data, o) if o + 8 <= len(data) else 0
    o += 8
    csv = _u64le(data, o) if o + 8 <= len(data) else 0
    o += 8
    lut = _i64le(data, o) if o + 8 <= len(data) else 0
    o += 8
    ix_name = ""
    if o + 4 <= len(data):
        ix_name, o = _borsh_str(data, o)
    mm = _bool(data, o) if o < len(data) else False
    o += 1
    cb_bps = _u64le(data, o) if o + 8 <= len(data) else 0
    o += 8
    cb = _u64le(data, o) if o + 8 <= len(data) else 0
    trade = {
        "metadata": meta,
        "mint": mint,
        "sol_amount": sol_amount,
        "token_amount": token_amount,
        "is_buy": is_buy,
        "is_created_buy": is_created_buy,
        "user": user,
        "timestamp": ts,
        "virtual_sol_reserves": vsol,
        "virtual_token_reserves": vtok,
        "real_sol_reserves": rsol,
        "real_token_reserves": rtok,
        "fee_recipient": fee_rec,
        "fee_basis_points": fee_bps,
        "fee": fee,
        "creator": creator,
        "creator_fee_basis_points": cfbps,
        "creator_fee": cfee,
        "track_volume": tv,
        "total_unclaimed_tokens": tuc,
        "total_claimed_tokens": tcc,
        "current_sol_volume": csv,
        "last_update_timestamp": lut,
        "ix_name": ix_name,
        "mayhem_mode": mm,
        "cashback_fee_basis_points": cb_bps,
        "cashback": cb,
        "is_cashback_coin": cb_bps > 0,
        "bonding_curve": Z,
        "associated_bonding_curve": Z,
        "token_program": Z,
        "creator_vault": Z,
    }
    if ix_name == "buy":
        return {"PumpFunBuy": trade}
    if ix_name == "sell":
        return {"PumpFunSell": trade}
    if ix_name == "buy_exact_sol_in":
        return {"PumpFunBuyExactSolIn": trade}
    return {"PumpFunTrade": trade}


def parse_create_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    o = 0
    try:
        name, o = _borsh_str(data, o)
        sym, o = _borsh_str(data, o)
        uri, o = _borsh_str(data, o)
    except Exception:
        return None
    if len(data) < o + 32 * 4 + 8 * 5 + 32 + 1:
        return None
    mint = _pub(data, o)
    o += 32
    bc = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    creator = _pub(data, o)
    o += 32
    ts = _i64le(data, o)
    o += 8
    vtr = _u64le(data, o)
    o += 8
    vsol = _u64le(data, o)
    o += 8
    rtr = _u64le(data, o)
    o += 8
    tts = _u64le(data, o)
    o += 8
    tp = _pub(data, o) if o + 32 <= len(data) else Z
    o += 32
    mm = _bool(data, o) if o < len(data) else False
    o += 1
    ice = _bool(data, o) if o < len(data) else False
    ev = {
        "metadata": meta,
        "name": name,
        "symbol": sym,
        "uri": uri,
        "mint": mint,
        "bonding_curve": bc,
        "user": user,
        "creator": creator,
        "timestamp": ts,
        "virtual_token_reserves": vtr,
        "virtual_sol_reserves": vsol,
        "real_token_reserves": rtr,
        "token_total_supply": tts,
        "token_program": tp,
        "is_mayhem_mode": mm,
        "is_cashback_enabled": ice,
    }
    return {"PumpFunCreate": ev}


def parse_migrate_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8 + 8 + 32 + 8 + 32:
        return None
    o = 0
    user = _pub(data, o)
    o += 32
    mint = _pub(data, o)
    o += 32
    ma = _u64le(data, o)
    o += 8
    sa = _u64le(data, o)
    o += 8
    pmf = _u64le(data, o)
    o += 8
    bc = _pub(data, o)
    o += 32
    ts = _i64le(data, o)
    o += 8
    pool = _pub(data, o)
    return {
        "PumpFunMigrate": {
            "metadata": meta,
            "user": user,
            "mint": mint,
            "mint_amount": ma,
            "sol_amount": sa,
            "pool_migration_fee": pmf,
            "bonding_curve": bc,
            "timestamp": ts,
            "pool": pool,
        }
    }


# --- Raydium CLMM ---


def parse_clmm_swap_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8 + 16 + 1:
        return None
    o = 0
    ps = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32 + 8 + 8
    sqrt = str(_u128le_int(data, o))
    o += 16
    zfo = _bool(data, o)
    return {
        "RaydiumClmmSwap": {
            "metadata": meta,
            "pool_state": ps,
            "sender": user,
            "token_account_0": Z,
            "token_account_1": Z,
            "amount_0": 0,
            "amount_1": 0,
            "zero_for_one": zfo,
            "sqrt_price_x64": sqrt,
            "liquidity": "0",
            "transfer_fee_0": 0,
            "transfer_fee_1": 0,
            "tick": 0,
        }
    }


def parse_clmm_inc_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 16 + 8 + 8:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    liq = str(_u128le_int(data, o))
    o += 16
    a0 = _u64le(data, o)
    o += 8
    a1 = _u64le(data, o)
    return {
        "RaydiumClmmIncreaseLiquidity": {
            "metadata": meta,
            "pool": pool,
            "position_nft_mint": Z,
            "user": user,
            "liquidity": liq,
            "amount0_max": a0,
            "amount1_max": a1,
        }
    }


def parse_clmm_dec_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 16 + 8 + 8:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    liq = str(_u128le_int(data, o))
    o += 16
    a0 = _u64le(data, o)
    o += 8
    a1 = _u64le(data, o)
    return {
        "RaydiumClmmDecreaseLiquidity": {
            "metadata": meta,
            "pool": pool,
            "position_nft_mint": Z,
            "user": user,
            "liquidity": liq,
            "amount0_min": a0,
            "amount1_min": a1,
        }
    }


def parse_clmm_create_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 16 + 8:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    cr = _pub(data, o)
    o += 32
    sqrt = str(_u128le_int(data, o))
    o += 16
    ot = _u64le(data, o)
    return {
        "RaydiumClmmCreatePool": {
            "metadata": meta,
            "pool": pool,
            "creator": cr,
            "token_0_mint": Z,
            "token_1_mint": Z,
            "tick_spacing": 0,
            "fee_rate": 0,
            "sqrt_price_x64": sqrt,
            "open_time": ot,
        }
    }


def parse_clmm_collect_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8:
        return None
    o = 0
    ps = _pub(data, o)
    o += 32
    pn = _pub(data, o)
    o += 32
    a0 = _u64le(data, o)
    o += 8
    a1 = _u64le(data, o)
    return {
        "RaydiumClmmCollectFee": {
            "metadata": meta,
            "pool_state": ps,
            "position_nft_mint": pn,
            "amount_0": a0,
            "amount_1": a1,
        }
    }


# --- Raydium AMM ---


def _amm_swap_ev(amm: str, user: str, ai: int, mo: int, mai: int, ao: int) -> dict:
    return {
        "metadata": None,
        "amm": amm,
        "user_source_owner": user,
        "amount_in": ai,
        "minimum_amount_out": mo,
        "max_amount_in": mai,
        "amount_out": ao,
        "token_program": Z,
        "amm_authority": Z,
        "amm_open_orders": Z,
        "pool_coin_token_account": Z,
        "pool_pc_token_account": Z,
        "serum_program": Z,
        "serum_market": Z,
        "serum_bids": Z,
        "serum_asks": Z,
        "serum_event_queue": Z,
        "serum_coin_vault_account": Z,
        "serum_pc_vault_account": Z,
        "serum_vault_signer": Z,
        "user_source_token_account": Z,
        "user_destination_token_account": Z,
    }


def parse_amm_swap_in_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8:
        return None
    o = 0
    amm = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    ai = _u64le(data, o)
    o += 8
    mo = _u64le(data, o)
    ev = _amm_swap_ev(amm, user, ai, mo, 0, 0)
    ev["metadata"] = meta
    return {"RaydiumAmmV4Swap": ev}


def parse_amm_swap_out_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8:
        return None
    o = 0
    amm = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    mai = _u64le(data, o)
    o += 8
    ao = _u64le(data, o)
    ev = _amm_swap_ev(amm, user, 0, 0, mai, ao)
    ev["metadata"] = meta
    return {"RaydiumAmmV4Swap": ev}


def parse_amm_deposit_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8 + 8:
        return None
    o = 0
    amm = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    mc = _u64le(data, o)
    o += 8
    mp = _u64le(data, o)
    o += 8
    bs = _u64le(data, o)
    return {
        "RaydiumAmmV4Deposit": {
            "metadata": meta,
            "amm": amm,
            "user_owner": user,
            "max_coin_amount": mc,
            "max_pc_amount": mp,
            "base_side": bs,
            "token_program": Z,
            "amm_authority": Z,
            "amm_open_orders": Z,
            "amm_target_orders": Z,
            "lp_mint_address": Z,
            "pool_coin_token_account": Z,
            "pool_pc_token_account": Z,
            "serum_market": Z,
            "user_coin_token_account": Z,
            "user_pc_token_account": Z,
            "user_lp_token_account": Z,
            "serum_event_queue": Z,
        }
    }


def parse_amm_withdraw_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8:
        return None
    o = 0
    amm = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    amt = _u64le(data, o)
    return {
        "RaydiumAmmV4Withdraw": {
            "metadata": meta,
            "amm": amm,
            "user_owner": user,
            "amount": amt,
            "token_program": Z,
            "amm_authority": Z,
            "amm_open_orders": Z,
            "amm_target_orders": Z,
            "lp_mint_address": Z,
            "pool_coin_token_account": Z,
            "pool_pc_token_account": Z,
            "pool_withdraw_queue": Z,
            "pool_temp_lp_token_account": Z,
            "serum_program": Z,
            "serum_market": Z,
            "serum_coin_vault_account": Z,
            "serum_pc_vault_account": Z,
            "serum_vault_signer": Z,
            "user_lp_token_account": Z,
            "user_coin_token_account": Z,
            "user_pc_token_account": Z,
            "serum_event_queue": Z,
            "serum_bids": Z,
            "serum_asks": Z,
        }
    }


def parse_amm_withdraw_pnl_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 64:
        return None
    o = 0
    amm = _pub(data, o)
    o += 32
    pnl_owner = _pub(data, o)
    return {
        "RaydiumAmmV4WithdrawPnl": {
            "metadata": meta,
            "token_program": Z,
            "amm": amm,
            "amm_config": Z,
            "amm_authority": Z,
            "amm_open_orders": Z,
            "pool_coin_token_account": Z,
            "pool_pc_token_account": Z,
            "coin_pnl_token_account": Z,
            "pc_pnl_token_account": Z,
            "pnl_owner": pnl_owner,
            "amm_target_orders": Z,
            "serum_program": Z,
            "serum_market": Z,
            "serum_event_queue": Z,
            "serum_coin_vault_account": Z,
            "serum_pc_vault_account": Z,
            "serum_vault_signer": Z,
        }
    }


def parse_amm_init2_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 1 + 8 + 8 + 8:
        return None
    o = 0
    amm = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    nonce = _u8(data, o)
    o += 1
    ot = _u64le(data, o)
    o += 8
    ipc = _u64le(data, o)
    o += 8
    ic = _u64le(data, o)
    return {
        "RaydiumAmmV4Initialize2": {
            "metadata": meta,
            "nonce": nonce,
            "open_time": ot,
            "init_pc_amount": ipc,
            "init_coin_amount": ic,
            "token_program": Z,
            "spl_associated_token_account": Z,
            "system_program": Z,
            "rent": Z,
            "amm": amm,
            "amm_authority": Z,
            "amm_open_orders": Z,
            "lp_mint": Z,
            "coin_mint": Z,
            "pc_mint": Z,
            "pool_coin_token_account": Z,
            "pool_pc_token_account": Z,
            "pool_withdraw_queue": Z,
            "amm_target_orders": Z,
            "pool_temp_lp": Z,
            "serum_program": Z,
            "serum_market": Z,
            "user_wallet": user,
            "user_token_coin": Z,
            "user_token_pc": Z,
            "user_lp_token_account": Z,
        }
    }


# --- Raydium CPMM ---


def parse_cpmm_swap_in_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8 + 8 + 1:
        return None
    o = 0
    pool = _pub(data, o)
    o += 64
    ai = _u64le(data, o)
    o += 16
    ao = _u64le(data, o)
    o += 8
    bi = _bool(data, o)
    return {
        "RaydiumCpmmSwap": {
            "metadata": meta,
            "pool_id": pool,
            "input_amount": ai,
            "output_amount": ao,
            "input_vault_before": 0,
            "output_vault_before": 0,
            "input_transfer_fee": 0,
            "output_transfer_fee": 0,
            "base_input": bi,
        }
    }


def parse_cpmm_swap_out_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8 + 8 + 1:
        return None
    o = 0
    pool = _pub(data, o)
    o += 64
    o += 8
    ao = _u64le(data, o)
    o += 8
    ai = _u64le(data, o)
    o += 8
    bo = _bool(data, o)
    return {
        "RaydiumCpmmSwap": {
            "metadata": meta,
            "pool_id": pool,
            "input_amount": ai,
            "output_amount": ao,
            "base_input": not bo,
            "input_vault_before": 0,
            "output_vault_before": 0,
            "input_transfer_fee": 0,
            "output_transfer_fee": 0,
        }
    }


def parse_cpmm_deposit_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8 + 8:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    lp = _u64le(data, o)
    o += 8
    t0 = _u64le(data, o)
    o += 8
    t1 = _u64le(data, o)
    return {
        "RaydiumCpmmDeposit": {
            "metadata": meta,
            "pool": pool,
            "user": user,
            "lp_token_amount": lp,
            "token0_amount": t0,
            "token1_amount": t1,
        }
    }


def parse_cpmm_withdraw_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8 + 8:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    lp = _u64le(data, o)
    o += 8
    t0 = _u64le(data, o)
    o += 8
    t1 = _u64le(data, o)
    return {
        "RaydiumCpmmWithdraw": {
            "metadata": meta,
            "pool": pool,
            "user": user,
            "lp_token_amount": lp,
            "token0_amount": t0,
            "token1_amount": t1,
        }
    }


# --- Orca ---


def parse_orca_traded_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 1 + 16 + 16 + 8 * 6:
        return None
    o = 0
    w = _pub(data, o)
    o += 32
    atb = _bool(data, o)
    o += 1
    pre = str(_u128le_int(data, o))
    o += 16
    post = str(_u128le_int(data, o))
    o += 16
    ia = _u64le(data, o)
    o += 8
    oa = _u64le(data, o)
    o += 8
    itf = _u64le(data, o)
    o += 8
    otf = _u64le(data, o)
    o += 8
    lpf = _u64le(data, o)
    o += 8
    pf = _u64le(data, o)
    return {
        "OrcaWhirlpoolSwap": {
            "metadata": meta,
            "whirlpool": w,
            "a_to_b": atb,
            "pre_sqrt_price": pre,
            "post_sqrt_price": post,
            "input_amount": ia,
            "output_amount": oa,
            "input_transfer_fee": itf,
            "output_transfer_fee": otf,
            "lp_fee": lpf,
            "protocol_fee": pf,
        }
    }


def parse_orca_liq_inc_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 4 + 4 + 16 + 8 * 4:
        return None
    o = 0
    w = _pub(data, o)
    o += 32
    p = _pub(data, o)
    o += 32
    tl = _i32le(data, o)
    o += 4
    tu = _i32le(data, o)
    o += 4
    liq = str(_u128le_int(data, o))
    o += 16
    ta = _u64le(data, o)
    o += 8
    tb = _u64le(data, o)
    o += 8
    taf = _u64le(data, o)
    o += 8
    tbf = _u64le(data, o)
    return {
        "OrcaWhirlpoolLiquidityIncreased": {
            "metadata": meta,
            "whirlpool": w,
            "position": p,
            "tick_lower_index": tl,
            "tick_upper_index": tu,
            "liquidity": liq,
            "token_a_amount": ta,
            "token_b_amount": tb,
            "token_a_transfer_fee": taf,
            "token_b_transfer_fee": tbf,
        }
    }


def parse_orca_liq_dec_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 4 + 4 + 16 + 8 * 4:
        return None
    o = 0
    w = _pub(data, o)
    o += 32
    p = _pub(data, o)
    o += 32
    tl = _i32le(data, o)
    o += 4
    tu = _i32le(data, o)
    o += 4
    liq = str(_u128le_int(data, o))
    o += 16
    ta = _u64le(data, o)
    o += 8
    tb = _u64le(data, o)
    o += 8
    taf = _u64le(data, o)
    o += 8
    tbf = _u64le(data, o)
    return {
        "OrcaWhirlpoolLiquidityDecreased": {
            "metadata": meta,
            "whirlpool": w,
            "position": p,
            "tick_lower_index": tl,
            "tick_upper_index": tu,
            "liquidity": liq,
            "token_a_amount": ta,
            "token_b_amount": tb,
            "token_a_transfer_fee": taf,
            "token_b_transfer_fee": tbf,
        }
    }


def parse_orca_pool_init_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 5 + 2 + 1 + 1 + 16:
        return None
    o = 0
    w = _pub(data, o)
    o += 32
    cfg = _pub(data, o)
    o += 32
    ma = _pub(data, o)
    o += 32
    mb = _pub(data, o)
    o += 32
    ts = _u16le(data, o)
    o += 2
    tpa = _pub(data, o)
    o += 32
    tpb = _pub(data, o)
    o += 32
    da = _u8(data, o)
    o += 1
    db = _u8(data, o)
    o += 1
    isp = str(_u128le_int(data, o))
    return {
        "OrcaWhirlpoolPoolInitialized": {
            "metadata": meta,
            "whirlpool": w,
            "whirlpools_config": cfg,
            "token_mint_a": ma,
            "token_mint_b": mb,
            "tick_spacing": ts,
            "token_program_a": tpa,
            "token_program_b": tpb,
            "decimals_a": da,
            "decimals_b": db,
            "initial_sqrt_price": isp,
        }
    }


# --- Meteora Pools ---


def parse_meteora_swap_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 8 * 5:
        return None
    ox = [0]
    return {
        "MeteoraPoolsSwap": {
            "metadata": meta,
            "in_amount": _u64_at(data, ox),
            "out_amount": _u64_at(data, ox),
            "trade_fee": _u64_at(data, ox),
            "admin_fee": _u64_at(data, ox),
            "host_fee": _u64_at(data, ox),
        }
    }


def parse_meteora_add_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 24:
        return None
    ox = [0]
    return {
        "MeteoraPoolsAddLiquidity": {
            "metadata": meta,
            "lp_mint_amount": _u64_at(data, ox),
            "token_a_amount": _u64_at(data, ox),
            "token_b_amount": _u64_at(data, ox),
        }
    }


def parse_meteora_remove_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 24:
        return None
    ox = [0]
    return {
        "MeteoraPoolsRemoveLiquidity": {
            "metadata": meta,
            "lp_unmint_amount": _u64_at(data, ox),
            "token_a_out_amount": _u64_at(data, ox),
            "token_b_out_amount": _u64_at(data, ox),
        }
    }


def parse_meteora_bootstrap_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 24 + 32:
        return None
    ox = [0]
    lp = _u64_at(data, ox)
    ta = _u64_at(data, ox)
    tb = _u64_at(data, ox)
    pl = _pub(data, ox[0])
    return {
        "MeteoraPoolsBootstrapLiquidity": {
            "metadata": meta,
            "lp_mint_amount": lp,
            "token_a_amount": ta,
            "token_b_amount": tb,
            "pool": pl,
        }
    }


def parse_meteora_pool_created_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 4 + 1:
        return None
    o = 0
    lm = _pub(data, o)
    o += 32
    ta = _pub(data, o)
    o += 32
    tb = _pub(data, o)
    o += 32
    pt = _u8(data, o)
    o += 1
    pl = _pub(data, o)
    return {
        "MeteoraPoolsPoolCreated": {
            "metadata": meta,
            "lp_mint": lm,
            "token_a_mint": ta,
            "token_b_mint": tb,
            "pool_type": pt,
            "pool": pl,
        }
    }


def parse_meteora_pools_set_pool_fees_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 8 + 8 + 8 + 8 + 32:
        return None
    o = 0
    tfn = _u64le(data, o)
    o += 8
    tfd = _u64le(data, o)
    o += 8
    ofn = _u64le(data, o)
    o += 8
    ofd = _u64le(data, o)
    o += 8
    pool = _pub(data, o)
    return {
        "MeteoraPoolsSetPoolFees": {
            "metadata": meta,
            "trade_fee_numerator": tfn,
            "trade_fee_denominator": tfd,
            "owner_trade_fee_numerator": ofn,
            "owner_trade_fee_denominator": ofd,
            "pool": pool,
        }
    }


# --- Meteora DAMM (Swap / Swap2 only，与 Go/TS 一致) ---

DAMM_SWAP = _d(27, 60, 21, 213, 138, 170, 187, 147)
DAMM_SWAP2 = _d(189, 66, 51, 168, 38, 80, 117, 153)
DAMM_CREATE_POSITION = _d(156, 15, 119, 198, 29, 181, 221, 55)
DAMM_CLOSE_POSITION = _d(20, 145, 144, 68, 143, 142, 214, 178)
DAMM_ADD_LIQUIDITY = _d(175, 242, 8, 157, 30, 247, 185, 169)
DAMM_REMOVE_LIQUIDITY = _d(87, 46, 88, 98, 175, 96, 34, 91)
DAMM_INIT_POOL = _d(228, 50, 246, 85, 203, 66, 134, 37)


def parse_meteora_damm_from_buf(buf: bytes, meta: dict) -> Optional[DexEvent]:
    if len(buf) < 8:
        return None
    d = _disc8(buf[:8])
    data = buf[8:]
    if d == DAMM_SWAP:
        return _parse_damm_swap(data, meta)
    if d == DAMM_SWAP2:
        return _parse_damm_swap2(data, meta)
    if d == DAMM_CREATE_POSITION:
        return _parse_damm_create_position(data, meta)
    if d == DAMM_CLOSE_POSITION:
        return _parse_damm_close_position(data, meta)
    if d == DAMM_ADD_LIQUIDITY:
        return _parse_damm_add_liquidity(data, meta)
    if d == DAMM_REMOVE_LIQUIDITY:
        return _parse_damm_remove_liquidity(data, meta)
    if d == DAMM_INIT_POOL:
        return _parse_damm_initialize_pool(data, meta)
    return None


def _parse_damm_swap(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 1 + 1 + 8 * 8 + 16 + 8 * 4:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32 + 32
    td = _u8(data, o)
    o += 1
    hr = _bool(data, o)
    o += 1
    ai = _u64le(data, o)
    o += 8
    mo = _u64le(data, o)
    o += 8
    aai = _u64le(data, o)
    o += 8
    oa = _u64le(data, o)
    o += 8
    nsp = str(_u128le_int(data, o))
    o += 16
    lpf = _u64le(data, o)
    o += 8
    pf = _u64le(data, o)
    o += 8
    rf = _u64le(data, o)
    o += 8
    o += 8
    ct = _u64le(data, o)
    return {
        "MeteoraDammV2Swap": {
            "metadata": meta,
            "pool": pool,
            "trade_direction": td,
            "has_referral": hr,
            "amount_in": ai,
            "minimum_amount_out": mo,
            "output_amount": oa,
            "next_sqrt_price": nsp,
            "lp_fee": lpf,
            "protocol_fee": pf,
            "partner_fee": 0,
            "referral_fee": rf,
            "actual_amount_in": aai,
            "current_timestamp": ct,
            "token_a_vault": Z,
            "token_b_vault": Z,
            "token_a_mint": Z,
            "token_b_mint": Z,
            "token_a_program": Z,
            "token_b_program": Z,
        }
    }


def _parse_damm_swap2(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 1 + 1 + 1 + 8 * 2 + 1 + 8 * 6 + 16 + 8 * 4 + 8 * 3:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    td = _u8(data, o)
    o += 1
    o += 1
    hr = _bool(data, o)
    o += 1
    a0 = _u64le(data, o)
    o += 8
    a1 = _u64le(data, o)
    o += 8
    sm = _u8(data, o)
    o += 1
    ifi = _u64le(data, o)
    o += 8
    o += 16
    oa = _u64le(data, o)
    o += 8
    nsp = str(_u128le_int(data, o))
    o += 16
    lpf = _u64le(data, o)
    o += 8
    pf = _u64le(data, o)
    o += 8
    rf = _u64le(data, o)
    o += 8
    o += 8
    o += 8
    ct = _u64le(data, o)
    ai, mo = (a0, a1) if sm == 0 else (a1, a0)
    return {
        "MeteoraDammV2Swap": {
            "metadata": meta,
            "pool": pool,
            "trade_direction": td,
            "has_referral": hr,
            "amount_in": ai,
            "minimum_amount_out": mo,
            "output_amount": oa,
            "next_sqrt_price": nsp,
            "lp_fee": lpf,
            "protocol_fee": pf,
            "partner_fee": 0,
            "referral_fee": rf,
            "actual_amount_in": ifi,
            "current_timestamp": ct,
            "token_a_vault": Z,
            "token_b_vault": Z,
            "token_a_mint": Z,
            "token_b_mint": Z,
            "token_a_program": Z,
            "token_b_program": Z,
        }
    }


def _parse_damm_create_position(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 4:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    owner = _pub(data, o)
    o += 32
    position = _pub(data, o)
    o += 32
    nft = _pub(data, o)
    return {
        "MeteoraDammV2CreatePosition": {
            "metadata": meta,
            "pool": pool,
            "owner": owner,
            "position": position,
            "position_nft_mint": nft,
        }
    }


def _parse_damm_close_position(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 4:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    owner = _pub(data, o)
    o += 32
    position = _pub(data, o)
    o += 32
    nft = _pub(data, o)
    return {
        "MeteoraDammV2ClosePosition": {
            "metadata": meta,
            "pool": pool,
            "owner": owner,
            "position": position,
            "position_nft_mint": nft,
        }
    }


def _parse_damm_add_liquidity(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 3 + 16 + 8 * 6:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    position = _pub(data, o)
    o += 32
    owner = _pub(data, o)
    o += 32
    ld = str(_u128le_int(data, o))
    o += 16
    tat = _u64le(data, o)
    o += 8
    tbt = _u64le(data, o)
    o += 8
    ta = _u64le(data, o)
    o += 8
    tb = _u64le(data, o)
    o += 8
    tota = _u64le(data, o)
    o += 8
    totb = _u64le(data, o)
    return {
        "MeteoraDammV2AddLiquidity": {
            "metadata": meta,
            "pool": pool,
            "position": position,
            "owner": owner,
            "liquidity_delta": ld,
            "token_a_amount_threshold": tat,
            "token_b_amount_threshold": tbt,
            "token_a_amount": ta,
            "token_b_amount": tb,
            "total_amount_a": tota,
            "total_amount_b": totb,
        }
    }


def _parse_damm_dynamic_fee(data: bytes, o: int) -> Optional[tuple[dict, int]]:
    if o + 32 > len(data):
        return None
    bs = _u16le(data, o)
    o += 2
    bu = _u128le_int(data, o)
    o += 16
    fp = _u16le(data, o)
    o += 2
    dp = _u16le(data, o)
    o += 2
    rf = _u16le(data, o)
    o += 2
    mva = _u32le(data, o)
    o += 4
    vfc = _u32le(data, o)
    o += 4
    return (
        {
            "bin_step": bs,
            "bin_step_u128": str(bu),
            "filter_period": fp,
            "decay_period": dp,
            "reduction_factor": rf,
            "max_volatility_accumulator": mva,
            "variable_fee_control": vfc,
        },
        o,
    )


def _parse_damm_pool_fees(data: bytes, start: int) -> Optional[tuple[dict, int]]:
    if start + 30 > len(data):
        return None
    o = start
    base_hex = data[o : o + 27].hex()
    o += 27
    cfb = _u16le(data, o)
    o += 2
    pad = _u8(data, o)
    o += 1
    tag = _u8(data, o)
    o += 1
    dyn = None
    if tag == 1:
        inner = _parse_damm_dynamic_fee(data, o)
        if not inner:
            return None
        dyn, o = inner
    elif tag != 0:
        return None
    return (
        {
            "base_fee_data": base_hex,
            "compounding_fee_bps": cfb,
            "padding": pad,
            "dynamic_fee": dyn,
        },
        o,
    )


def _parse_damm_initialize_pool(data: bytes, meta: dict) -> Optional[DexEvent]:
    min_after_pub = 31 + 109
    if len(data) < 32 * 6 + min_after_pub:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    tam = _pub(data, o)
    o += 32
    tbm = _pub(data, o)
    o += 32
    creator = _pub(data, o)
    o += 32
    payer = _pub(data, o)
    o += 32
    av = _pub(data, o)
    o += 32
    pfp = _parse_damm_pool_fees(data, o)
    if not pfp:
        return None
    fees, o = pfp
    if o + 109 > len(data):
        return None
    smin = str(_u128le_int(data, o))
    o += 16
    smax = str(_u128le_int(data, o))
    o += 16
    act = _u8(data, o)
    o += 1
    cfm = _u8(data, o)
    o += 1
    liq = str(_u128le_int(data, o))
    o += 16
    sqrt_p = str(_u128le_int(data, o))
    o += 16
    ap = _u64le(data, o)
    o += 8
    taf = _u8(data, o)
    o += 1
    tbf = _u8(data, o)
    o += 1
    tau = _u64le(data, o)
    o += 8
    tbu = _u64le(data, o)
    o += 8
    tota = _u64le(data, o)
    o += 8
    totb = _u64le(data, o)
    o += 8
    pt = _u8(data, o)
    return {
        "MeteoraDammV2InitializePool": {
            "metadata": meta,
            "pool": pool,
            "token_a_mint": tam,
            "token_b_mint": tbm,
            "creator": creator,
            "payer": payer,
            "alpha_vault": av,
            "pool_fees": fees,
            "sqrt_min_price": smin,
            "sqrt_max_price": smax,
            "activation_type": act,
            "collect_fee_mode": cfm,
            "liquidity": liq,
            "sqrt_price": sqrt_p,
            "activation_point": ap,
            "token_a_flag": taf,
            "token_b_flag": tbf,
            "token_a_amount": tau,
            "token_b_amount": tbu,
            "total_amount_a": tota,
            "total_amount_b": totb,
            "pool_type": pt,
        }
    }


def _parse_damm_remove_liquidity(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 * 3 + 16 + 8 * 4:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    position = _pub(data, o)
    o += 32
    owner = _pub(data, o)
    o += 32
    ld = str(_u128le_int(data, o))
    o += 16
    tat = _u64le(data, o)
    o += 8
    tbt = _u64le(data, o)
    o += 8
    ta = _u64le(data, o)
    o += 8
    tb = _u64le(data, o)
    return {
        "MeteoraDammV2RemoveLiquidity": {
            "metadata": meta,
            "pool": pool,
            "position": position,
            "owner": owner,
            "liquidity_delta": ld,
            "token_a_amount_threshold": tat,
            "token_b_amount_threshold": tbt,
            "token_a_amount": ta,
            "token_b_amount": tb,
        }
    }


# --- Bonk ---

DISC_BONK_TRADE = _d(2, 3, 4, 5, 6, 7, 8, 9)
DISC_BONK_POOL_CREATE = _d(1, 2, 3, 4, 5, 6, 7, 8)
DISC_BONK_MIGRATE_AMM = _d(3, 4, 5, 6, 7, 8, 9, 10)


def parse_bonk_from_discriminator(disc: int, data: bytes, meta: dict) -> Optional[DexEvent]:
    if disc == DISC_BONK_TRADE:
        return _parse_bonk_trade(data, meta)
    if disc == DISC_BONK_POOL_CREATE:
        return _parse_bonk_pool_create(data, meta)
    if disc == DISC_BONK_MIGRATE_AMM:
        return _parse_bonk_migrate_amm(data, meta)
    return None


def _parse_bonk_trade(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 8 + 8 + 1 + 1:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    ai = _u64le(data, o)
    o += 8
    ao = _u64le(data, o)
    o += 8
    is_buy = _bool(data, o)
    o += 1
    ex_in = _bool(data, o)
    d = "Buy" if is_buy else "Sell"
    return {
        "BonkTrade": {
            "metadata": meta,
            "pool_state": pool,
            "user": user,
            "amount_in": ai,
            "amount_out": ao,
            "is_buy": is_buy,
            "trade_direction": d,
            "exact_in": ex_in,
        }
    }


def _parse_bonk_pool_create(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 32 + 32 + 8 + 8:
        return None
    o = 0
    pool = _pub(data, o)
    o += 32 + 32 + 32
    creator = _pub(data, o)
    return {
        "BonkPoolCreate": {
            "metadata": meta,
            "base_mint_param": {"symbol": "BONK", "name": "Bonk Pool", "uri": "https://bonk.com", "decimals": 5},
            "pool_state": pool,
            "creator": creator,
        }
    }


def _parse_bonk_migrate_amm(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 32 + 32 + 32 + 8:
        return None
    o = 0
    old_p = _pub(data, o)
    o += 32
    new_p = _pub(data, o)
    o += 32
    user = _pub(data, o)
    o += 32
    liq = _u64le(data, o)
    return {
        "BonkMigrateAmm": {
            "metadata": meta,
            "old_pool": old_p,
            "new_pool": new_p,
            "user": user,
            "liquidity_amount": liq,
        }
    }


# --- PumpSwap ---


def parse_ps_buy_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    min_len = 14 * 8 + 7 * 32 + 1 + 5 * 8 + 4
    if len(data) < min_len:
        return None
    o = 0

    def rd() -> int:
        nonlocal o
        v = _u64le(data, o)
        o += 8
        return v

    def ri() -> int:
        nonlocal o
        v = _i64le(data, o)
        o += 8
        return v

    def rp() -> str:
        nonlocal o
        s = _pub(data, o)
        o += 32
        return s

    ts = ri()
    ev: Dict[str, Any] = {
        "metadata": meta,
        "timestamp": ts,
        "base_amount_out": rd(),
        "max_quote_amount_in": rd(),
        "user_base_token_reserves": rd(),
        "user_quote_token_reserves": rd(),
        "pool_base_token_reserves": rd(),
        "pool_quote_token_reserves": rd(),
        "quote_amount_in": rd(),
        "lp_fee_basis_points": rd(),
        "lp_fee": rd(),
        "protocol_fee_basis_points": rd(),
        "protocol_fee": rd(),
        "quote_amount_in_with_lp_fee": rd(),
        "user_quote_amount_in": rd(),
        "pool": rp(),
        "user": rp(),
        "user_base_token_account": rp(),
        "user_quote_token_account": rp(),
        "protocol_fee_recipient": rp(),
        "protocol_fee_recipient_token_account": rp(),
        "coin_creator": rp(),
        "coin_creator_fee_basis_points": rd(),
        "coin_creator_fee": rd(),
    }
    tv = _bool(data, o)
    o += 1
    ev["track_volume"] = tv
    ev["total_unclaimed_tokens"] = rd()
    ev["total_claimed_tokens"] = rd()
    ev["current_sol_volume"] = rd()
    ev["last_update_timestamp"] = ri()
    ev["min_base_amount_out"] = rd()
    ix = ""
    if o + 4 <= len(data):
        ln = _u32le(data, o)
        o += 4
        if o + ln <= len(data):
            ix = data[o : o + ln].decode("utf-8", errors="replace")
    ev["ix_name"] = ix
    # Mayhem mode and cashback fields
    mm = False
    if o < len(data):
        mm = _bool(data, o)
        o += 1
    cb_bps = 0
    cb = 0
    if o + 16 <= len(data):
        cb_bps = _u64le(data, o)
        o += 8
        cb = _u64le(data, o)
    ev["mayhem_mode"] = mm
    ev["cashback_fee_basis_points"] = cb_bps
    ev["cashback"] = cb
    ev["is_cashback_coin"] = cb_bps > 0
    return {"PumpSwapBuy": ev}


def parse_ps_sell_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    req = 13 * 8 + 7 * 32
    if len(data) < req:
        return None
    o = 0

    def rd() -> int:
        nonlocal o
        v = _u64le(data, o)
        o += 8
        return v

    def ri() -> int:
        nonlocal o
        v = _i64le(data, o)
        o += 8
        return v

    def rp() -> str:
        nonlocal o
        s = _pub(data, o)
        o += 32
        return s

    ev: Dict[str, Any] = {
        "metadata": meta,
        "timestamp": ri(),
        "base_amount_in": rd(),
        "min_quote_amount_out": rd(),
        "user_base_token_reserves": rd(),
        "user_quote_token_reserves": rd(),
        "pool_base_token_reserves": rd(),
        "pool_quote_token_reserves": rd(),
        "quote_amount_out": rd(),
        "lp_fee_basis_points": rd(),
        "lp_fee": rd(),
        "protocol_fee_basis_points": rd(),
        "protocol_fee": rd(),
        "quote_amount_out_without_lp_fee": rd(),
        "user_quote_amount_out": rd(),
        "pool": rp(),
        "user": rp(),
        "user_base_token_account": rp(),
        "user_quote_token_account": rp(),
        "protocol_fee_recipient": rp(),
        "protocol_fee_recipient_token_account": rp(),
        "coin_creator": rp(),
        "coin_creator_fee_basis_points": rd(),
        "coin_creator_fee": rd(),
    }
    cash_bps, cash = 0, 0
    if len(data) >= 368:
        cash_bps = _u64le(data, 352)
        cash = _u64le(data, 360)
    ev["cashback_fee_basis_points"] = cash_bps
    ev["cashback"] = cash
    return {"PumpSwapSell": ev}


def parse_ps_create_pool_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    req = 8 + 2 + 32 * 6 + 2 + 8 * 7 + 1
    if len(data) < req:
        return None
    o = 0
    ts = _i64le(data, o)
    o += 8
    idx = _u16le(data, o)
    o += 2
    creator = _pub(data, o)
    o += 32
    bm = _pub(data, o)
    o += 32
    qm = _pub(data, o)
    o += 32
    bd = _u8(data, o)
    o += 1
    qd = _u8(data, o)
    o += 1

    def rd() -> int:
        nonlocal o
        v = _u64le(data, o)
        o += 8
        return v

    ev: Dict[str, Any] = {
        "metadata": meta,
        "timestamp": ts,
        "index": idx,
        "creator": creator,
        "base_mint": bm,
        "quote_mint": qm,
        "base_mint_decimals": bd,
        "quote_mint_decimals": qd,
        "base_amount_in": rd(),
        "quote_amount_in": rd(),
        "pool_base_amount": rd(),
        "pool_quote_amount": rd(),
        "minimum_liquidity": rd(),
        "initial_liquidity": rd(),
        "lp_token_amount_out": rd(),
    }
    pb = _u8(data, o)
    o += 1
    pool = _pub(data, o)
    o += 32
    lp = _pub(data, o)
    o += 32
    uba = _pub(data, o)
    o += 32
    uqa = _pub(data, o)
    o += 32
    cc = _pub(data, o)
    ev["pool_bump"] = pb
    ev["pool"] = pool
    ev["lp_mint"] = lp
    ev["user_base_token_account"] = uba
    ev["user_quote_token_account"] = uqa
    ev["coin_creator"] = cc
    ev["is_mayhem_mode"] = len(data) > 325 and _bool(data, 325)
    return {"PumpSwapCreatePool": ev}


def parse_ps_add_liq_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 10 * 8 + 5 * 32:
        return None
    o = 0

    def rd() -> int:
        nonlocal o
        v = _u64le(data, o)
        o += 8
        return v

    def ri() -> int:
        nonlocal o
        v = _i64le(data, o)
        o += 8
        return v

    def rp() -> str:
        nonlocal o
        s = _pub(data, o)
        o += 32
        return s

    return {
        "PumpSwapLiquidityAdded": {
            "metadata": meta,
            "timestamp": ri(),
            "lp_token_amount_out": rd(),
            "max_base_amount_in": rd(),
            "max_quote_amount_in": rd(),
            "user_base_token_reserves": rd(),
            "user_quote_token_reserves": rd(),
            "pool_base_token_reserves": rd(),
            "pool_quote_token_reserves": rd(),
            "base_amount_in": rd(),
            "quote_amount_in": rd(),
            "lp_mint_supply": rd(),
            "pool": rp(),
            "user": rp(),
            "user_base_token_account": rp(),
            "user_quote_token_account": rp(),
            "user_pool_token_account": rp(),
        }
    }


def parse_ps_remove_liq_from_data(data: bytes, meta: dict) -> Optional[DexEvent]:
    if len(data) < 10 * 8 + 5 * 32:
        return None
    o = 0

    def rd() -> int:
        nonlocal o
        v = _u64le(data, o)
        o += 8
        return v

    def ri() -> int:
        nonlocal o
        v = _i64le(data, o)
        o += 8
        return v

    def rp() -> str:
        nonlocal o
        s = _pub(data, o)
        o += 32
        return s

    return {
        "PumpSwapLiquidityRemoved": {
            "metadata": meta,
            "timestamp": ri(),
            "lp_token_amount_in": rd(),
            "min_base_amount_out": rd(),
            "min_quote_amount_out": rd(),
            "user_base_token_reserves": rd(),
            "user_quote_token_reserves": rd(),
            "pool_base_token_reserves": rd(),
            "pool_quote_token_reserves": rd(),
            "base_amount_out": rd(),
            "quote_amount_out": rd(),
            "lp_mint_supply": rd(),
            "pool": rp(),
            "user": rp(),
            "user_base_token_account": rp(),
            "user_quote_token_account": rp(),
            "user_pool_token_account": rp(),
        }
    }


# --- Meteora DLMM ---

DLMM_SWAP = _d(143, 190, 90, 218, 196, 30, 51, 222)
DLMM_ADD_LIQ = _d(181, 157, 89, 67, 143, 182, 52, 72)
DLMM_REMOVE_LIQ = _d(80, 85, 209, 72, 24, 206, 35, 178)
DLMM_INIT_POOL = _d(95, 180, 10, 172, 84, 174, 232, 40)
DLMM_INIT_BIN = _d(11, 18, 155, 194, 33, 115, 238, 119)
DLMM_CREATE_POS = _d(123, 233, 11, 43, 146, 180, 97, 119)
DLMM_CLOSE_POS = _d(94, 168, 102, 45, 59, 122, 137, 54)
DLMM_CLAIM_FEE = _d(152, 70, 208, 111, 104, 91, 44, 1)


def parse_dlmm_from_program_data(buf: bytes, meta: dict) -> Optional[DexEvent]:
    if len(buf) < 8:
        return None
    d = _disc8(buf[:8])
    data = buf[8:]
    if d == DLMM_SWAP:
        if len(data) < 32 + 32 + 4 + 4 + 8 + 8 + 1 + 8 + 8 + 16 + 8:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        frm = _pub(data, o)
        o += 32
        sb = _i32le(data, o)
        o += 4
        eb = _i32le(data, o)
        o += 4
        ai = _u64le(data, o)
        o += 8
        ao = _u64le(data, o)
        o += 8
        sy = _bool(data, o)
        o += 1
        fee = _u64le(data, o)
        o += 8
        pf = _u64le(data, o)
        o += 8
        fbps = str(_u128le_int(data, o))
        o += 16
        hf = _u64le(data, o)
        return {
            "MeteoraDlmmSwap": {
                "metadata": meta,
                "pool": pool,
                "from": frm,
                "start_bin_id": sb,
                "end_bin_id": eb,
                "amount_in": ai,
                "amount_out": ao,
                "swap_for_y": sy,
                "fee": fee,
                "protocol_fee": pf,
                "fee_bps": fbps,
                "host_fee": hf,
            }
        }
    if d == DLMM_ADD_LIQ:
        if len(data) < 32 + 32 + 32 + 8 + 8 + 4:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        frm = _pub(data, o)
        o += 32
        pos = _pub(data, o)
        o += 32
        a0 = _u64le(data, o)
        o += 8
        a1 = _u64le(data, o)
        o += 8
        ab = _i32le(data, o)
        return {
            "MeteoraDlmmAddLiquidity": {
                "metadata": meta,
                "pool": pool,
                "from": frm,
                "position": pos,
                "amounts": [a0, a1],
                "active_bin_id": ab,
            }
        }
    if d == DLMM_REMOVE_LIQ:
        if len(data) < 32 + 32 + 32 + 8 + 8 + 4:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        frm = _pub(data, o)
        o += 32
        pos = _pub(data, o)
        o += 32
        a0 = _u64le(data, o)
        o += 8
        a1 = _u64le(data, o)
        o += 8
        ab = _i32le(data, o)
        return {
            "MeteoraDlmmRemoveLiquidity": {
                "metadata": meta,
                "pool": pool,
                "from": frm,
                "position": pos,
                "amounts": [a0, a1],
                "active_bin_id": ab,
            }
        }
    if d == DLMM_INIT_POOL:
        if len(data) < 32 + 32 + 4 + 2:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        creator = _pub(data, o)
        o += 32
        ab = _i32le(data, o)
        o += 4
        bs = _u16le(data, o)
        return {
            "MeteoraDlmmInitializePool": {
                "metadata": meta,
                "pool": pool,
                "creator": creator,
                "active_bin_id": ab,
                "bin_step": bs,
            }
        }
    if d == DLMM_INIT_BIN:
        if len(data) < 32 + 32 + 8:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        ba = _pub(data, o)
        o += 32
        idx = _u64le(data, o)
        return {
            "MeteoraDlmmInitializeBinArray": {
                "metadata": meta,
                "pool": pool,
                "bin_array": ba,
                "index": idx,
            }
        }
    if d == DLMM_CREATE_POS:
        if len(data) < 32 + 32 + 32 + 4 + 4:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        pos = _pub(data, o)
        o += 32
        owner = _pub(data, o)
        o += 32
        lb = _i32le(data, o)
        o += 4
        w = _u32le(data, o)
        return {
            "MeteoraDlmmCreatePosition": {
                "metadata": meta,
                "pool": pool,
                "position": pos,
                "owner": owner,
                "lower_bin_id": lb,
                "width": w,
            }
        }
    if d == DLMM_CLOSE_POS:
        if len(data) < 32 + 32 + 32:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        pos = _pub(data, o)
        o += 32
        owner = _pub(data, o)
        return {
            "MeteoraDlmmClosePosition": {
                "metadata": meta,
                "pool": pool,
                "position": pos,
                "owner": owner,
            }
        }
    if d == DLMM_CLAIM_FEE:
        if len(data) < 32 + 32 + 32 + 8 + 8:
            return None
        o = 0
        pool = _pub(data, o)
        o += 32
        pos = _pub(data, o)
        o += 32
        owner = _pub(data, o)
        o += 32
        fx = _u64le(data, o)
        o += 8
        fy = _u64le(data, o)
        return {
            "MeteoraDlmmClaimFee": {
                "metadata": meta,
                "pool": pool,
                "position": pos,
                "owner": owner,
                "fee_x": fx,
                "fee_y": fy,
            }
        }
    return None


# --- 主调度（与 Go matcher 分支顺序一致） ---

def dispatch_program_data(
    disc: int,
    data: bytes,
    buf: bytes,
    meta: dict,
    is_created_buy: bool,
) -> Optional[DexEvent]:
    if disc == PUMP_TRADE:
        return parse_trade_from_data(data, meta, is_created_buy)
    if disc == _d(248, 198, 158, 145, 225, 117, 135, 200):
        return parse_clmm_swap_from_data(data, meta)
    if disc == _d(0, 0, 0, 0, 0, 0, 0, 9):
        return parse_amm_swap_in_from_data(data, meta)
    if disc == _d(103, 244, 82, 31, 44, 245, 119, 119):
        return parse_ps_buy_from_data(data, meta)
    if disc == _d(62, 47, 55, 10, 165, 3, 220, 42):
        return parse_ps_sell_from_data(data, meta)
    if disc == PUMP_CREATE:
        return parse_create_from_data(data, meta)
    if disc == PUMP_MIGRATE:
        return parse_migrate_from_data(data, meta)
    if disc == _d(177, 49, 12, 210, 160, 118, 167, 116):
        return parse_ps_create_pool_from_data(data, meta)
    if disc == _d(120, 248, 61, 83, 31, 142, 107, 144):
        return parse_ps_add_liq_from_data(data, meta)
    if disc == _d(22, 9, 133, 26, 160, 44, 71, 192):
        return parse_ps_remove_liq_from_data(data, meta)
    if disc == _d(133, 29, 89, 223, 69, 238, 176, 10):
        return parse_clmm_inc_from_data(data, meta)
    if disc == _d(160, 38, 208, 111, 104, 91, 44, 1):
        return parse_clmm_dec_from_data(data, meta)
    if disc == _d(233, 146, 209, 142, 207, 104, 64, 188):
        return parse_clmm_create_from_data(data, meta)
    if disc == _d(164, 152, 207, 99, 187, 104, 171, 119):
        return parse_clmm_collect_from_data(data, meta)
    if disc == _d(143, 190, 90, 218, 196, 30, 51, 222):
        return parse_cpmm_swap_in_from_data(data, meta)
    if disc == _d(55, 217, 98, 86, 163, 74, 180, 173):
        return parse_cpmm_swap_out_from_data(data, meta)
    if disc == _d(242, 35, 198, 137, 82, 225, 242, 182):
        return parse_cpmm_deposit_from_data(data, meta)
    if disc == _d(183, 18, 70, 156, 148, 109, 161, 34):
        return parse_cpmm_withdraw_from_data(data, meta)
    if disc == _d(0, 0, 0, 0, 0, 0, 0, 11):
        return parse_amm_swap_out_from_data(data, meta)
    if disc == _d(0, 0, 0, 0, 0, 0, 0, 3):
        return parse_amm_deposit_from_data(data, meta)
    if disc == _d(0, 0, 0, 0, 0, 0, 0, 4):
        return parse_amm_withdraw_from_data(data, meta)
    if disc == _d(0, 0, 0, 0, 0, 0, 0, 7):
        return parse_amm_withdraw_pnl_from_data(data, meta)
    if disc == _d(0, 0, 0, 0, 0, 0, 0, 1):
        return parse_amm_init2_from_data(data, meta)
    if disc == _d(225, 202, 73, 175, 147, 43, 160, 150):
        return parse_orca_traded_from_data(data, meta)
    if disc == _d(30, 7, 144, 181, 102, 254, 155, 161):
        return parse_orca_liq_inc_from_data(data, meta)
    if disc == _d(166, 1, 36, 71, 112, 202, 181, 171):
        return parse_orca_liq_dec_from_data(data, meta)
    if disc == _d(100, 118, 173, 87, 12, 198, 254, 229):
        return parse_orca_pool_init_from_data(data, meta)
    if disc == _d(81, 108, 227, 190, 205, 208, 10, 196):
        return parse_meteora_swap_from_data(data, meta)
    if disc == _d(31, 94, 125, 90, 227, 52, 61, 186):
        return parse_meteora_add_from_data(data, meta)
    if disc == _d(116, 244, 97, 232, 103, 31, 152, 58):
        return parse_meteora_remove_from_data(data, meta)
    if disc == _d(121, 127, 38, 136, 92, 55, 14, 247):
        return parse_meteora_bootstrap_from_data(data, meta)
    if disc == _d(202, 44, 41, 88, 104, 220, 157, 82):
        return parse_meteora_pool_created_from_data(data, meta)
    if disc == _d(245, 26, 198, 164, 88, 18, 75, 9):
        return parse_meteora_pools_set_pool_fees_from_data(data, meta)
    if disc in (
        DAMM_SWAP,
        DAMM_SWAP2,
        _d(175, 242, 8, 157, 30, 247, 185, 169),
        _d(87, 46, 88, 98, 175, 96, 34, 91),
        _d(228, 50, 246, 85, 203, 66, 134, 37),
        _d(156, 15, 119, 198, 29, 181, 221, 55),
        _d(20, 145, 144, 68, 143, 142, 214, 178),
    ):
        return parse_meteora_damm_from_buf(buf, meta)
    bonk = parse_bonk_from_discriminator(disc, data, meta)
    if bonk:
        return bonk
    return parse_dlmm_from_program_data(buf, meta)
