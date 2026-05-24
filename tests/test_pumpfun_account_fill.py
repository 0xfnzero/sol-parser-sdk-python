from sol_parser.account_fillers.pumpfun import fill_trade_accounts
from sol_parser.event_types import PumpFunTradeEvent

Z = "11111111111111111111111111111111"


def getter(overrides):
    return lambda idx: overrides.get(idx, Z)


def test_fill_trade_accounts_uses_v2_indexes_for_short_buy_exact_quote_in():
    trade = PumpFunTradeEvent(
        ix_name="buy_exact_quote_in",
        is_buy=True,
        mint="mint",
        quote_mint=Z,
        token_program=Z,
        fee_recipient=Z,
        bonding_curve=Z,
        associated_bonding_curve=Z,
        user=Z,
        creator_vault=Z,
    )

    fill_trade_accounts(
        trade,
        getter(
            {
                1: "mint",
                2: "usdc",
                3: "token_program_2022",
                6: "fee",
                9: "legacy_creator_vault",
                10: "bonding_curve",
                11: "associated_bonding_curve",
                13: "user",
                16: "creator_vault",
            }
        ),
    )

    assert trade.quote_mint == "usdc"
    assert trade.token_program == "token_program_2022"
    assert trade.fee_recipient == "fee"
    assert trade.bonding_curve == "bonding_curve"
    assert trade.associated_bonding_curve == "associated_bonding_curve"
    assert trade.user == "user"
    assert trade.creator_vault == "creator_vault"


def test_fill_trade_accounts_keeps_legacy_indexes_for_legacy_short_buy_exact_quote_in():
    trade = PumpFunTradeEvent(
        ix_name="buy_exact_quote_in",
        is_buy=True,
        mint="mint",
        token_program=Z,
        creator_vault=Z,
    )

    fill_trade_accounts(
        trade,
        getter(
            {
                2: "mint",
                8: "spl_token",
                9: "legacy_creator_vault",
            }
        ),
    )

    assert trade.token_program == "spl_token"
    assert trade.creator_vault == "legacy_creator_vault"
