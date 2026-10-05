from types import SimpleNamespace
import base58
from sol_parser.account_dispatcher import fill_accounts_with_owned_keys
from sol_parser.dex_parsers import _parse_raydium_launchlab_trade

PROGRAM = "LanMV9sAd7wArD4vJFi2qDdfnVhFxYSUg6eADduJ3uj"
ZERO = "11111111111111111111111111111111"


def case(same_pool=False):
    keys = [bytes([i]) * 32 for i in range(1, 37)]
    first = list(range(18))
    second = list(range(18, 36))
    if same_pool:
        second[4] = first[4]
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
    data = bytearray(139)
    data[:32] = keys[second[4]]
    data[138] = 1
    event = _parse_raydium_launchlab_trade(
        bytes(data),
        {
            "signature": "sig",
            "slot": 1,
            "tx_index": 0,
            "block_time_us": 0,
            "grpc_recv_us": 0,
        },
    )
    fill_accounts_with_owned_keys(
        event, meta, tx, {base58.b58decode(PROGRAM): [(0, -1), (1, -1)]}
    )
    return (
        event,
        base58.b58encode(keys[second[9]]).decode(),
        base58.b58encode(keys[second[0]]).decode(),
    )


def test_filler_anchors_to_event_pool_in_multi_pool_transaction():
    event, mint, user = case()
    assert event.data.base_mint == mint and event.data.user == user


def test_filler_does_not_guess_wallet_for_ambiguous_same_pool_invocations():
    event, _, _ = case(True)
    assert event.data.user == ZERO
    assert event.data.platform_config in ("", ZERO)
