import base64
from pathlib import Path
import json
import pytest
import base58
from sol_parser import (
    analyze_rpc_transaction_routes,
    decode_wire_transaction,
    StonkFunGraduatedPool,
    StonkFunPoolRegistry,
)
from sol_parser.transaction_route import STANDARD, REWARD, WSOL, TOKEN, ZERO
from sol_parser.grpc_types import EventMetadata
from sol_parser.accounts import AccountData
from sol_parser.liquidity_snapshot import parse_liquidity_account

GOLDEN = json.loads(
    (Path(__file__).parent / "fixtures" / "stonkfun_routes_0_7_7.json").read_text()
)
AMOUNTS = {
    "specified_amount",
    "other_amount_threshold",
    "actual_input_amount",
    "actual_output_amount",
    "amount",
    "withheld_fee",
    "lamports",
}


def canonical(value, key=""):
    if isinstance(value, dict):
        return {k: canonical(v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [canonical(v) for v in value]
    if isinstance(value, int) and not isinstance(value, bool) and key in AMOUNTS:
        return str(value)
    return value


@pytest.mark.parametrize("case", GOLDEN["cases"], ids=lambda c: c["name"])
def test_route_matches_released_rust(case):
    assert (
        canonical(analyze_rpc_transaction_routes(case["transaction"]).to_dict())
        == case["expected"]
    )


@pytest.mark.parametrize("case", GOLDEN["cases"], ids=lambda c: c["name"])
def test_native_wire_decoding_preserves_route_and_rejects_truncation(case):
    tx = case["transaction"]
    wire = base64.b64decode(tx["transaction"][0])
    decoded, length = decode_wire_transaction(wire)
    assert length == len(wire)
    assert decoded["version"] == tx["version"]
    assert (
        analyze_rpc_transaction_routes({**tx, "transaction": decoded}).to_dict()
        == analyze_rpc_transaction_routes(tx).to_dict()
    )
    for offset in [0, 1, len(wire) // 2, len(wire) - 1]:
        with pytest.raises(ValueError):
            decode_wire_transaction(wire[:offset])
    with pytest.raises(ValueError):
        decode_wire_transaction(wire + b"\x00")


def test_registry_batch_conflicts_are_atomic_and_persistence_is_validated():
    keys = [base58.b58encode(bytes([i]) * 32).decode() for i in range(1, 7)]
    sig = base58.b58encode(bytes([1]) * 64).decode()
    entry = StonkFunGraduatedPool(*keys[:4], STANDARD, sig, 123)
    registry = StonkFunPoolRegistry()
    assert registry.observe_migrations([entry], False) == 0
    assert registry.observe_migrations([entry, entry], True) == 1
    assert registry.observe_migrations([entry], True) == 0
    before = registry.to_dict()
    bad = StonkFunGraduatedPool(
        entry.curve_pool, entry.pool, entry.base_mint, keys[5], STANDARD, sig, 123
    )
    with pytest.raises(ValueError):
        registry.observe_migrations([bad], True)
    assert registry.to_dict() == before
    assert StonkFunPoolRegistry.from_dict(before).to_dict() == before
    with pytest.raises(ValueError):
        StonkFunPoolRegistry.from_dict({"pools": before["pools"] * 2})


def test_dynamic_ticks_check_bitmap_tags_and_owner():
    data = bytearray(148)
    data[:8] = bytes([17, 216, 246, 142, 225, 199, 218, 56])
    data[12:44] = bytes([2]) * 32
    owner = "whirLbMiicVdio4qvUfM5KAg6Ct8VwpYzGff3uctyCc"
    account = AccountData(ZERO, False, 1, owner, 0, bytes(data))
    assert parse_liquidity_account(account, EventMetadata()) is not None
    data[60] = 1
    account.data = bytes(data)
    assert parse_liquidity_account(account, EventMetadata()) is None
    account.data = bytes(148)
    account.owner = TOKEN
    assert parse_liquidity_account(account, EventMetadata()) is None


def test_native_actions_are_evidence_even_for_failed_transactions():
    enc = lambda d: base58.b58encode(bytes(d)).decode()
    keys = [ZERO, TOKEN, enc([2] * 32), enc([3] * 32), WSOL]
    tx = {
        "meta": {"err": {"InstructionError": [1, "error"]}},
        "transaction": {
            "signatures": [],
            "message": {
                "accountKeys": keys,
                "instructions": [
                    {
                        "programIdIndex": 1,
                        "accounts": [3, 4],
                        "data": enc([18] + [2] * 32),
                    },
                    {
                        "programIdIndex": 0,
                        "accounts": [2, 3],
                        "data": enc([2, 0, 0, 0] + list((123).to_bytes(8, "little"))),
                    },
                    {"programIdIndex": 1, "accounts": [3], "data": enc([17])},
                    {"programIdIndex": 1, "accounts": [3, 2, 2], "data": enc([9])},
                ],
            },
        },
    }
    route = analyze_rpc_transaction_routes(tx)
    assert not route.succeeded and len(route.native_token_actions) == 3
    tx["transaction"]["message"]["accountKeys"][4] = keys[2]
    assert not analyze_rpc_transaction_routes(tx).native_token_actions
