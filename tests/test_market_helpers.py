from sol_parser.market import (
    normalize_buy_sell_from_input_mint,
    normalize_buy_sell_from_token_delta,
    sqrt_price_x64_to_price,
    vault_price_from_balances,
)


def test_market_helpers() -> None:
    q64 = 1 << 64
    assert sqrt_price_x64_to_price(q64, 6, 6) == 1.0
    assert sqrt_price_x64_to_price(q64, 9, 6) == 1000.0
    assert vault_price_from_balances(1_000_000_000, 2_000_000, 9, 6) == 2.0
    assert vault_price_from_balances(0, 2_000_000, 6, 6) is None
    assert normalize_buy_sell_from_token_delta(1) == "Buy"
    assert normalize_buy_sell_from_token_delta(-1) == "Sell"
    assert normalize_buy_sell_from_token_delta(0) is None
    assert normalize_buy_sell_from_input_mint("USDC", "SOL", "USDC") == "Buy"
    assert normalize_buy_sell_from_input_mint("SOL", "SOL", "USDC") == "Sell"
