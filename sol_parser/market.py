"""Market math helpers shared by non-Pump DEX examples."""

from __future__ import annotations

from typing import Literal, Optional, Union

NumericAmount = Union[int, float, str]
NormalizedTradeSide = Literal["Buy", "Sell"]


def _amount_to_float(value: NumericAmount) -> float:
    if isinstance(value, str) and value.strip() == "":
        raise ValueError("amount must not be empty")
    return float(value)


def sqrt_price_x64_to_price(
    sqrt_price_x64: NumericAmount,
    base_decimals: int,
    quote_decimals: int,
) -> float:
    """Convert Q64.64 sqrt price into quote-token units per one base token."""
    sqrt = _amount_to_float(sqrt_price_x64) / 2**64
    return sqrt * sqrt * 10 ** (base_decimals - quote_decimals)


def vault_price_from_balances(
    base_raw: NumericAmount,
    quote_raw: NumericAmount,
    base_decimals: int,
    quote_decimals: int,
) -> Optional[float]:
    """Compute quote-token price per one base token from raw vault balances."""
    base = _amount_to_float(base_raw)
    if base == 0:
        return None
    return (_amount_to_float(quote_raw) / base) * 10 ** (base_decimals - quote_decimals)


def normalize_buy_sell_from_token_delta(token_delta: NumericAmount) -> Optional[NormalizedTradeSide]:
    """Positive watched-token delta means Buy; negative means Sell."""
    delta = _amount_to_float(token_delta)
    if delta > 0:
        return "Buy"
    if delta < 0:
        return "Sell"
    return None


def normalize_buy_sell_from_input_mint(
    input_mint: str,
    base_mint: str,
    quote_mint: str,
) -> Optional[NormalizedTradeSide]:
    """If input is quote, the user buys base. If input is base, the user sells base."""
    if base_mint == quote_mint:
        return None
    if input_mint == quote_mint:
        return "Buy"
    if input_mint == base_mint:
        return "Sell"
    return None
