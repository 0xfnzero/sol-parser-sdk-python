"""Genuine signed wire verification and cached execution-metadata replay; no RPC."""
import base64
import copy
import json
from pathlib import Path
import base58
import pytest
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sol_parser import decode_wire_transaction, analyze_simulation_routes
CASES = json.loads((Path(__file__).parent / "fixtures/signed_replay_20261009.json").read_text())["cases"]

@pytest.mark.parametrize("case", CASES, ids=lambda c: c["name"])
def test_signed_wire_and_metadata_replay(case):
    wire = base64.b64decode(case["wire"])
    tx, consumed = decode_wire_transaction(wire)
    count = case["expected"]["signature_count"]
    # All fixtures use a one-byte canonical signature count (1 or 2).
    assert wire[0] == count < 128
    assert consumed == len(wire)
    assert len(tx["signatures"]) == count
    assert tx["signatures"][0] == case["expected"]["signature"]
    assert len(tx["message"]["instructions"]) == case["expected"]["instruction_count"]
    assert tx["version"] == case["expected"]["version"]
    message = wire[1 + count * 64:]
    for i in range(count):
        key = Ed25519PublicKey.from_public_bytes(base58.b58decode(tx["message"]["accountKeys"][i]))
        signature = wire[1 + i * 64:1 + (i + 1) * 64]
        assert base58.b58encode(signature).decode() == tx["signatures"][i]
        key.verify(signature, message)
        with pytest.raises(InvalidSignature):
            key.verify(bytes([signature[0] ^ 1]) + signature[1:], message)
        with pytest.raises(InvalidSignature):
            key.verify(signature, message[:-1] + bytes([message[-1] ^ 1]))
    for malformed in (wire[:-1], wire + b"\x00"):
        with pytest.raises(ValueError):
            decode_wire_transaction(malformed)
    route = analyze_simulation_routes(wire, {"result": {"value": case["rpc"]["meta"]}})
    assert route.signature == case["expected"]["signature"]
    assert route.succeeded
    assert len(route.legs) == (0 if case["name"] == "generated_legacy_two_signers" else 1)
    if route.legs:
        leg = route.legs[0]
        pumpfun = case["name"] == "pumpfun"
        assert leg.protocol == ("PumpFun" if pumpfun else "PumpSwap")
        assert leg.specified_amount == (30765521374696 if pumpfun else 10000000)
        assert leg.actual_input_amount == (None if pumpfun else 10000000)
        assert leg.actual_output_amount is None
        # Fault injection into metadata is not an executed failed transaction.
        meta = copy.deepcopy(case["rpc"]["meta"])
        meta["err"] = {"InstructionError": [0, "Custom"]}
        failed = analyze_simulation_routes(wire, {"result": {"value": meta}})
        assert not failed.succeeded
        assert all(l.actual_input_amount is None and l.actual_output_amount is None for l in failed.legs)

DEX_CASES = json.loads((Path(__file__).parent / "fixtures/signed_dex_replay_20261009.json").read_text())["cases"]

@pytest.mark.parametrize("case", DEX_CASES, ids=lambda c: c["name"])
def test_signed_multi_alt_cpi_and_real_failed_replay(case):
    wire = base64.b64decode(case["wire"])
    tx, consumed = decode_wire_transaction(wire)
    assert consumed == len(wire)
    assert len(tx["message"]["addressTableLookups"]) == case["expected"]["lookup_count"]
    count = len(tx["signatures"])
    assert wire[0] == count < 128
    message = wire[1 + 64 * count:]
    for i, signature in enumerate(tx["signatures"]):
        Ed25519PublicKey.from_public_bytes(base58.b58decode(tx["message"]["accountKeys"][i])).verify(base58.b58decode(signature), message)
    route = analyze_simulation_routes(wire, {"result": {"value": case["rpc"]["meta"]}})
    assert route.signature == tx["signatures"][0]
    assert route.succeeded is case["expected"]["succeeded"]
    assert len(route.legs) == len(case["expected"]["legs"])
    for leg, expected in zip(route.legs, case["expected"]["legs"]):
        assert (leg.protocol, leg.pool, leg.input_mint, leg.output_mint) == tuple(expected[k] for k in ("protocol", "pool", "input_mint", "output_mint"))
        assert leg.specified_amount == int(expected["specified_amount"])
        assert leg.actual_input_amount == (int(expected["specified_amount"]) if route.succeeded else None)
        assert leg.actual_output_amount == (int(expected["actual_output_amount"]) if expected["actual_output_amount"] is not None else None)
        if route.succeeded:
            assert leg.position.stack_height == 2
    if not route.succeeded:
        assert not route.transfers and not route.native_token_actions
    from sol_parser.rpc_parser import rpc_get_transaction_result_dict_to_response, parse_rpc_transaction
    rpc = copy.deepcopy(case["rpc"])
    rpc["transaction"] = tx  # RPC conversion consumes compiled JSON, not base64 tuples.
    events, error = parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(rpc), tx["signatures"][0], None, 0)
    assert error is None
    if not route.succeeded:
        assert not events
    else:
        assert all(event.data.metadata.signature == route.signature for event in events)
        assert len(events) == 3
        for event, expected in zip(events, case["expected"]["legs"]):
            body = event.data
            assert event.type.value == expected["protocol"] + "Swap"
            pool = next(getattr(body, field) for field in ("pool_id", "pool_state", "whirlpool", "pool") if hasattr(body, field))
            assert pool == expected["pool"]
            if expected["protocol"] == "RaydiumClmm":
                amounts = (body.amount_0, body.amount_1) if body.zero_for_one else (body.amount_1, body.amount_0)
            else:
                amounts = (getattr(body, "input_amount", getattr(body, "amount_in", None)), getattr(body, "output_amount", getattr(body, "amount_out", None)))
            assert amounts == (int(expected["specified_amount"]), int(expected["actual_output_amount"]))

BOUNDARIES = [case for filename in ("signed_wire_boundaries_20261009.json", "signed_alt_load_rejections_20261009.json") for case in json.loads((Path(__file__).parent / "fixtures" / filename).read_text())["cases"]]

@pytest.mark.parametrize("case", BOUNDARIES, ids=lambda c: c["name"])
def test_official_sanitizer_boundary_contract(case):
    wire = base64.b64decode(case["wire"])
    if not case["valid_structure"]:
        with pytest.raises(ValueError):
            decode_wire_transaction(wire)
    else:
        tx, consumed = decode_wire_transaction(wire)
        assert consumed == len(wire)
        valid = True
        for i, signature in enumerate(tx["signatures"]):
            key = Ed25519PublicKey.from_public_bytes(base58.b58decode(tx["message"]["accountKeys"][i]))
            try:
                key.verify(base58.b58decode(signature), wire[1 + 64 * len(tx["signatures"]):])
            except InvalidSignature:
                valid = False
        assert valid is case["valid_signature"]
        assert decode_wire_transaction(b"\x09" + wire + b"\x0a", 1, False)[1] == len(wire)


def test_signed_customizable_pool_public_parse_boundaries():
    from sol_parser.rpc_parser import rpc_get_transaction_result_dict_to_response, parse_rpc_transaction
    corpus = json.loads((Path(__file__).parent / 'fixtures/signed_clmm_boundaries_20261009.json').read_text())
    for case in corpus['cases']:
        wire = base64.b64decode(case['wire'])
        tx, consumed = decode_wire_transaction(wire)
        assert consumed == len(wire)
        Ed25519PublicKey.from_public_bytes(base58.b58decode(tx['message']['accountKeys'][0])).verify(wire[1:65], wire[65:])
        rpc = copy.deepcopy(case['rpc']); rpc['transaction'] = tx
        events, error = parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(rpc), tx['signatures'][0], None, 0)
        assert error is None
        assert len(events) == int(case['valid_instruction']), case['name']


@pytest.mark.parametrize('case', json.loads((Path(__file__).parent / 'fixtures/signed_cpmm_bank_20261009.json').read_text())['cases'], ids=lambda c: c['name'])
def test_captured_cpmm_signed_bank_fee_and_failure_replay(case, monkeypatch):
    import socket
    from sol_parser.rpc_parser import rpc_get_transaction_result_dict_to_response, parse_rpc_transaction
    def deny_network(*args, **kwargs):
        raise AssertionError('Parser hot path attempted network I/O')
    monkeypatch.setattr(socket.socket, 'connect', deny_network)
    monkeypatch.setattr(socket, 'create_connection', deny_network)
    wire = base64.b64decode(case['wire'])
    tx, n = decode_wire_transaction(wire)
    assert n == len(wire)
    Ed25519PublicKey.from_public_bytes(base58.b58decode(tx['message']['accountKeys'][0])).verify(wire[1:65], wire[65:])
    rpc = copy.deepcopy(case['rpc']); rpc['transaction'] = tx
    events, error = parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(rpc), tx['signatures'][0], None, 0)
    assert error is None and len(events) == int(case['succeeded'])
    route = analyze_simulation_routes(wire, {'result': {'value': rpc['meta']}})
    assert route.succeeded is case['succeeded'] and len(route.legs) == 1
    leg = route.legs[0]
    assert leg.protocol == 'RaydiumCpmm'
    if case['succeeded']:
        assert (events[0].data.input_amount, events[0].data.output_amount) == (case['vault_credit'], case['vault_debit'])
        assert leg.actual_input_amount == case['gross_input']
        # Plain Token-2022 TransferChecked CPI omits withheld fee: net credit stays unknown.
        assert leg.actual_output_amount == (None if case['name'] == 'fee-output' else case['net_output'])
        assert events[0].data.metadata.signature == tx['signatures'][0]
    else:
        assert leg.actual_input_amount is None and leg.actual_output_amount is None
        assert not route.transfers and not route.native_token_actions


@pytest.mark.parametrize('case', [case for filename in ('signed_multileg_bank_20261009.json', 'signed_identical_alt_bank_20261009.json') for case in json.loads((Path(__file__).parent / 'fixtures' / filename).read_text())['cases']], ids=lambda c: c['name'])
def test_same_pool_multileg_bank_invocation_settlement(case, monkeypatch):
    import socket
    from sol_parser.rpc_parser import rpc_get_transaction_result_dict_to_response, parse_rpc_transaction
    def deny(*args, **kwargs):
        raise AssertionError('parser must not use RPC')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    wire = base64.b64decode(case['wire'])
    tx, consumed = decode_wire_transaction(wire)
    assert consumed == len(wire)
    for i, signature in enumerate(tx['signatures']):
        Ed25519PublicKey.from_public_bytes(base58.b58decode(tx['message']['accountKeys'][i])).verify(base58.b58decode(signature), wire[1 + 64 * len(tx['signatures']):])

    if 'lookup_tables' in case:
        tables = {t['key']: t['addresses'] for t in case['lookup_tables']}
        for side in ('writable', 'readonly'):
            expected = [tables[t['accountKey']][i] for t in tx['message']['addressTableLookups'] for i in t[side + 'Indexes']]
            assert expected == case['rpc']['meta']['loadedAddresses'][side]

    # Metadata fault injection is not a bank execution; signed wire remains identical.
    if case.get('lookup_tables'):
        for side in ('writable', 'readonly'):
            for action in ('short', 'extra'):
                bad = copy.deepcopy(case['rpc']['meta'])
                if action == 'short': bad['loadedAddresses'][side].pop()
                else: bad['loadedAddresses'][side].append(bad['loadedAddresses'][side][0])
                with pytest.raises(ValueError):
                    analyze_simulation_routes(wire, {'result': {'value': bad}})
    rpc = copy.deepcopy(case['rpc']); rpc['transaction'] = tx
    events, error = parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(rpc), tx['signatures'][0], None, 0)
    assert error is None and len(events) == (2 if case['succeeded'] else 0)
    route = analyze_simulation_routes(wire, {'result': {'value': rpc['meta']}})
    assert route.succeeded is case['succeeded'] and len(route.legs) == 2
    assert route.legs[0].pool == route.legs[1].pool
    assert route.legs[0].trader == route.legs[1].trader
    if 'identity' in case:
        for leg in route.legs:
            assert all(getattr(leg, key) == value for key, value in case['identity'].items())
    for i, leg in enumerate(route.legs):
        assert leg.position.outer_index == i + 1
        assert leg.specified_amount == case['requested_gross_inputs'][i]
        if case['succeeded']:
            expected = case['legs'][i]
            assert leg.actual_input_amount == expected['gross_input']
            assert leg.actual_output_amount == (None if case['fee_output_legs'][i] else expected['net_output'])
            assert (events[i].data.input_amount, events[i].data.output_amount) == (expected['vault_credit'], expected['vault_debit'])
        else:
            assert leg.actual_input_amount is None and leg.actual_output_amount is None


@pytest.mark.parametrize('case', json.loads((Path(__file__).parent / 'fixtures/signed_nested_cpi_bank_20261009.json').read_text())['cases'], ids=lambda c: c['name'])
def test_actual_signed_nested_cpi_bank_failure_cannot_invent_settlement(case, monkeypatch):
    import socket
    from sol_parser.rpc_parser import rpc_get_transaction_result_dict_to_response, parse_rpc_transaction
    def deny(*args, **kwargs): raise AssertionError('parser must not use RPC')
    monkeypatch.setattr(socket.socket, 'connect', deny)
    wire = base64.b64decode(case['wire'])
    tx, consumed = decode_wire_transaction(wire)
    assert consumed == len(wire)
    for i, sig in enumerate(tx['signatures']):
        Ed25519PublicKey.from_public_bytes(base58.b58decode(tx['message']['accountKeys'][i])).verify(base58.b58decode(sig), wire[1 + 64 * len(tx['signatures']):])
    rpc = copy.deepcopy(case['rpc']); rpc['transaction'] = tx
    events, error = parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(rpc), tx['signatures'][0], None, 0)
    assert error is None and len(events) == int(case['succeeded'])
    route = analyze_simulation_routes(wire, {'result': {'value': rpc['meta']}})
    assert route.succeeded is case['succeeded'] and len(route.legs) == 1
    leg = route.legs[0]
    assert leg.position.stack_height == (2 if case['succeeded'] else 3) and leg.specified_amount == 10001
    if case['succeeded']:
        assert (leg.actual_input_amount, leg.actual_output_amount) == (10001, 468207)
        assert case['token_deltas'][leg.input_account] == -leg.actual_input_amount
        assert case['token_deltas'][leg.output_account] == leg.actual_output_amount
        assert (events[0].data.input_amount, events[0].data.output_amount) == (9800, 468207)
    else:
        assert leg.actual_input_amount is None and leg.actual_output_amount is None
        assert all(delta == 0 for delta in case['token_deltas'].values())
    assert any('Tokenkeg' in log and log.endswith(' success') for log in rpc['meta']['logMessages'])


def test_mixed_signed_framed_stream_legacy_v0_legacy_isolation():
    from sol_parser.rpc_parser import rpc_get_transaction_result_dict_to_response, parse_rpc_transaction
    legacy = next(c for c in CASES if c['name'] == 'generated_legacy_two_signers')
    bank = json.loads((Path(__file__).parent / 'fixtures/signed_identical_alt_bank_20261009.json').read_text())['cases']
    v0 = next(c for c in bank if c['name'] == 'identical-intents-two-alt')
    cases = [legacy, v0, legacy]
    wires = [base64.b64decode(c['wire']) for c in cases]
    stream = b''.join(wires)
    with pytest.raises(ValueError): decode_wire_transaction(stream)
    offset = 0
    for i, (case, wire) in enumerate(zip(cases, wires)):
        tx, consumed = decode_wire_transaction(stream, offset, False)
        assert consumed == len(wire)
        assert tx == decode_wire_transaction(wire)[0]
        assert len(tx['signatures']) == 2
        assert tx['version'] == (0 if i == 1 else 'legacy')
        for signer, signature in enumerate(tx['signatures']):
            Ed25519PublicKey.from_public_bytes(base58.b58decode(tx['message']['accountKeys'][signer])).verify(base58.b58decode(signature), wire[129:])
        rpc = copy.deepcopy(case['rpc']); rpc['transaction'] = tx
        events, error = parse_rpc_transaction(rpc_get_transaction_result_dict_to_response(rpc), tx['signatures'][0], None, 0)
        assert error is None and len(events) == (2 if i == 1 else 0)
        offset += consumed
    assert offset == len(stream)
    damaged = stream[:-1]
    assert decode_wire_transaction(damaged, 0, False)[1] == len(wires[0])
    assert decode_wire_transaction(damaged, len(wires[0]), False)[1] == len(wires[1])
    with pytest.raises(ValueError): decode_wire_transaction(damaged, len(wires[0]) + len(wires[1]), False)
