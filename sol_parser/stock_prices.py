"""Opt-in reported execution prices; never fetches accounts or computes live quotes."""

from copy import deepcopy
from dataclasses import dataclass
import math
import base58
from .stock_catalog import STOCK_DEX_PROGRAMS
from .trade_source import TradeParseStatus

STOCK_WSOL = "So11111111111111111111111111111111111111112"
STOCK_USDC = "EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v"
DEFAULT_STOCK_SOL_USDC_POOL = "Czfq3xZZDmsdGdUyrNLtRhGc47cXcZtLG4crryfu44zE"


@dataclass
class StockTokenPriceEvent:
    metadata: object
    mint: str
    symbol: str
    pool: str
    dex_type: str
    quote_mint: str
    price_in_quote: float
    price_sol: float | None
    price_usdc: float | None
    stock_amount_raw: int
    quote_amount_raw: int
    sol_usdc_reference: dict | None
    liquidity: dict | None
    basis: str = "ReportedSwapAmounts"


def _valid_key(key):
    try:
        raw = base58.b58decode(key)
        return len(raw) == 32 and any(raw)
    except (ValueError, TypeError):
        return False


def _executed_swap(event):
    d = event.data
    if getattr(d, "parse_status", None) != TradeParseStatus.EXECUTION_CONFIRMED:
        return None
    name = event.type.value
    if (
        name == "RaydiumCpmmSwap"
        and d.input_vault_before > 0
        and d.output_vault_before > 0
    ):
        return (
            d.pool_id,
            "raydium_cpmm",
            d.input_mint,
            d.output_mint,
            d.input_amount,
            d.output_amount,
        )
    if name == "RaydiumClmmSwap" and int(d.sqrt_price_x64 or 0) > 0:
        a, b = (d.amount_0, d.amount_1) if d.zero_for_one else (d.amount_1, d.amount_0)
        return d.pool_state, "raydium_clmm", d.input_mint, d.output_mint, a, b
    if name == "OrcaWhirlpoolSwap" and int(d.post_sqrt_price or 0) > 0:
        a, b = (
            (d.token_mint_a, d.token_mint_b)
            if d.a_to_b
            else (d.token_mint_b, d.token_mint_a)
        )
        return d.whirlpool, "orca_whirlpool", a, b, d.input_amount, d.output_amount
    if name == "MeteoraDlmmSwap" and d.event_version in (1, 2):
        a, b = (
            (d.token_x_mint, d.token_y_mint)
            if d.swap_for_y
            else (d.token_y_mint, d.token_x_mint)
        )
        return d.pool, "meteora_dlmm", a, b, d.amount_in, d.amount_out
    return None


class StockPriceTracker:
    def __init__(
        self,
        catalog=None,
        *,
        sol_usdc_pool=DEFAULT_STOCK_SOL_USDC_POOL,
        sol_usdc_dex="orca_whirlpool",
        max_age_us=30_000_000,
        max_slot_lag=75,
    ):
        if (
            not _valid_key(sol_usdc_pool)
            or sol_usdc_dex not in STOCK_DEX_PROGRAMS
            or type(max_age_us) is not int
            or max_age_us <= 0
            or type(max_slot_lag) is not int
            or max_slot_lag < 0
        ):
            raise ValueError("Invalid stock reference or freshness")
        self._reference_pool, self._reference_dex = sol_usdc_pool, sol_usdc_dex
        self._max_age, self._max_slots = max_age_us, max_slot_lag
        self._tokens, self._pools = {}, {}
        for token in (catalog or {}).get("tokens", ()):
            mint, decimals = token["mint"], token["decimals"]
            if (
                not _valid_key(mint)
                or mint in (STOCK_WSOL, STOCK_USDC)
                or mint in self._tokens
                or type(decimals) is not int
                or not 0 <= decimals <= 18
            ):
                raise ValueError("Invalid or duplicate stock token")
            self._tokens[mint] = dict(token)
        for pool in (catalog or {}).get("pools", ()):
            if (
                pool["mint"] not in self._tokens
                or not _valid_key(pool["pool"])
                or pool["pool"] in self._pools
                or pool["pool"] == sol_usdc_pool
                or pool["quote_mint"] not in (STOCK_WSOL, STOCK_USDC)
                or pool["dex_type"] not in STOCK_DEX_PROGRAMS
            ):
                raise ValueError("Invalid or duplicate stock pool")
            scale = 10.0 ** (
                self._tokens[pool["mint"]]["decimals"]
                - (9 if pool["quote_mint"] == STOCK_WSOL else 6)
            )
            self._pools[pool["pool"]] = (deepcopy(pool), scale)
        self.reset()

    def reset(self):
        """Required after disconnect, queue loss or selected-fork changes."""
        self._reference, self._positions, self._liquidity = None, {}, {}

    def update_liquidity(self, snapshot):
        depths = [snapshot.get("buy_depth_usdc"), snapshot.get("sell_depth_usdc")]
        impact = snapshot.get("depth_max_price_impact_bps")
        if (
            snapshot["pool"] not in self._pools
            or snapshot["slot"] < 0
            or snapshot["observed_us"] <= 0
            or not snapshot["source"].strip()
            or any(
                x is not None and (not math.isfinite(x) or x < 0)
                for x in [snapshot.get("tvl_usdc"), *depths]
            )
            or (any(x is not None for x in depths) and impact is None)
            or (
                impact is not None
                and (type(impact) is not int or not 0 <= impact < 10000)
            )
        ):
            raise ValueError("Invalid liquidity snapshot")
        old = self._liquidity.get(snapshot["pool"])
        if old and (
            snapshot["slot"] < old["slot"]
            or snapshot["observed_us"] < old["observed_us"]
        ):
            raise ValueError("Out-of-order liquidity")
        self._liquidity[snapshot["pool"]] = deepcopy(snapshot)

    def _fresh(self, time, slot, meta, now):
        return (
            0 < time <= now
            and now - time <= self._max_age
            and slot <= meta.slot
            and meta.slot - slot <= self._max_slots
        )

    def process(self, event, now_us):
        if not self._pools:
            return None
        swap = _executed_swap(event)
        if swap is None:
            return None
        pool_id, dex, source, target, amount_in, amount_out = swap
        meta = event.data.metadata
        if (
            amount_in <= 0
            or amount_out <= 0
            or not self._fresh(meta.grpc_recv_us, meta.slot, meta, now_us)
        ):
            return None
        position = (meta.slot, meta.tx_index)
        if self._positions.get(pool_id, position) > position:
            return None
        if pool_id == self._reference_pool and dex == self._reference_dex:
            if (source, target) == (STOCK_WSOL, STOCK_USDC):
                price = amount_out / amount_in * 1000
            elif (source, target) == (STOCK_USDC, STOCK_WSOL):
                price = amount_in / amount_out * 1000
            else:
                return None
            self._reference = dict(
                pool=pool_id, usdc_per_sol=price, metadata=deepcopy(meta)
            )
            self._positions[pool_id] = position
            return None
        tracked = self._pools.get(pool_id)
        if tracked is None or tracked[0]["dex_type"] != dex:
            return None
        pool, scale = tracked
        if (source, target) == (pool["mint"], pool["quote_mint"]):
            stock, quote = amount_in, amount_out
        elif (target, source) == (pool["mint"], pool["quote_mint"]):
            stock, quote = amount_out, amount_in
        else:
            return None
        price = quote / stock * scale
        if not math.isfinite(price) or price <= 0:
            return None
        reference = self._reference
        if reference:
            m = reference["metadata"]
            if (m.slot, m.tx_index) >= position or not self._fresh(
                m.grpc_recv_us, m.slot, meta, now_us
            ):
                reference = None
        liquidity = self._liquidity.get(pool_id)
        if liquidity and not self._fresh(
            liquidity["observed_us"], liquidity["slot"], meta, now_us
        ):
            liquidity = None
        sol_quote = pool["quote_mint"] == STOCK_WSOL
        self._positions[pool_id] = position
        return StockTokenPriceEvent(
            deepcopy(meta),
            pool["mint"],
            self._tokens[pool["mint"]]["symbol"],
            pool_id,
            dex,
            pool["quote_mint"],
            price,
            (
                price
                if sol_quote
                else price / reference["usdc_per_sol"] if reference else None
            ),
            (
                price
                if not sol_quote
                else price * reference["usdc_per_sol"] if reference else None
            ),
            stock,
            quote,
            deepcopy(reference),
            deepcopy(liquidity),
        )
