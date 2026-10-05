import struct
import pytest
from sol_parser.instructions import parse_raydium_amm_v4_instruction

ZERO = "11111111111111111111111111111111"


@pytest.mark.parametrize("tag", [16, 17])
def test_v2_eight_account_event(tag):
    keys = [f"account-{i}" for i in range(8)]
    e = parse_raydium_amm_v4_instruction(
        bytes([tag]) + struct.pack("<QQ", 1001, 500),
        keys,
        "signature",
        123,
        4,
        567,
        890,
    )
    p = e.data
    assert (
        p.amm == keys[1]
        and p.pool_coin_token_account == keys[3]
        and p.pool_pc_token_account == keys[4]
    )
    assert (
        p.user_source_token_account == keys[5]
        and p.user_destination_token_account == keys[6]
        and p.user_source_owner == keys[7]
    )
    assert (
        p.amm_open_orders == ZERO and p.serum_program == ZERO and p.serum_market == ZERO
    )
    assert (p.amount_in, p.minimum_amount_out, p.max_amount_in, p.amount_out) == (
        (1001, 500, 0, 0) if tag == 16 else (0, 0, 1001, 500)
    )
    assert (
        parse_raydium_amm_v4_instruction(
            bytes([tag]) + struct.pack("<QQ", 1, 2), keys[:7], "s", 1, 0, None, 0
        )
        is None
    )
    assert (
        parse_raydium_amm_v4_instruction(
            bytes([tag]) + bytes(15), keys, "s", 1, 0, None, 0
        )
        is None
    )


@pytest.mark.parametrize("mode", ["single", "anchored", "ambiguous"])
def test_rpc_log_context_is_v2_and_unambiguous(mode):
    from types import SimpleNamespace
    import base58
    from sol_parser.account_dispatcher import fill_accounts_with_owned_keys
    from sol_parser.account_fillers.raydium import fill_amm_v4_swap_accounts

    keys = [bytes([i]) * 32 for i in range(1, 17)]
    first = list(range(8))
    second = list(range(8, 16))
    tx = SimpleNamespace(
        message=SimpleNamespace(
            account_keys=keys,
            instructions=[
                SimpleNamespace(accounts=bytes(first)),
                SimpleNamespace(accounts=bytes(second)),
            ],
        )
    )
    meta = SimpleNamespace(
        loaded_writable_addresses=[],
        loaded_readonly_addresses=[],
        inner_instructions=[],
    )
    # Start with a decoded event but remove context as in ray_log payloads.
    event = parse_raydium_amm_v4_instruction(
        bytes([16]) + struct.pack("<QQ", 1, 2), [ZERO] * 8, "s", 1, 0, None, 0
    )
    if mode == "anchored":
        event.data.amm = base58.b58encode(keys[9]).decode()
    inv = [(0, -1)] if mode == "single" else [(0, -1), (1, -1)]
    fill_accounts_with_owned_keys(
        event,
        meta,
        tx,
        {base58.b58decode("675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"): inv},
    )
    if mode == "ambiguous":
        assert event.data.amm == ZERO and event.data.user_source_owner == ZERO
    else:
        offset = 0 if mode == "single" else 8
        assert (
            event.data.user_source_owner == base58.b58encode(keys[offset + 7]).decode()
        )
        assert (
            event.data.pool_coin_token_account
            == base58.b58encode(keys[offset + 3]).decode()
        )
