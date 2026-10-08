import base64, copy, json
import struct, base58
from pathlib import Path
import pytest
from sol_parser import (
    analyze_simulation_routes,
    analyze_rpc_transaction_routes,
    decode_wire_transaction,
)
from sol_parser.transaction_route import TOKEN_2022
from test_stonkfun_routes import canonical

CORPUS = json.loads(
    (Path(__file__).parent / "fixtures/cached_tip_routes_20261002.json").read_text()
)

LIVE_CORPUS = json.loads(
    (
        Path(__file__).parent / "fixtures/simulation_routes_live_20261002.json"
    ).read_text()
)

ATA_CORPUS = json.loads(
    (Path(__file__).parent / "fixtures/simulation_ata_20261002.json").read_text()
)


@pytest.mark.parametrize("case", ATA_CORPUS["cases"], ids=lambda c: c["name"])
def test_first_ata_simulation(case):
    route = analyze_simulation_routes(base64.b64decode(case["wire"]), case["response"])
    assert canonical(route.to_dict()) == case["expected"]
    assert route.succeeded
    assert all(t.position.outer_index != 0 for t in route.transfers)
    assert all(l.actual_input_amount == l.specified_amount for l in route.legs)


def test_ata_initialization_infers_mint_without_balances():
    c = ATA_CORPUS["cases"][0]
    response = copy.deepcopy(c["response"])
    value = response["result"]["value"]
    group = value["innerInstructions"][0]
    ix = group["instructions"][3]
    info = ix["parsed"]["info"]
    value["preTokenBalances"] = value["postTokenBalances"] = []
    group["instructions"].append(
        dict(
            programId=ix["programId"],
            stackHeight=2,
            parsed=dict(
                type="transfer",
                info=dict(
                    source=info["account"],
                    destination=info["owner"],
                    authority=info["owner"],
                    amount="1",
                ),
            ),
        )
    )
    route = analyze_simulation_routes(base64.b64decode(c["wire"]), response)
    assert route.transfers[0].mint == info["mint"]
    assert route.transfers[0].position.inner_index == 4


@pytest.mark.parametrize("kind", ["extension", "owner", "lamports"])
def test_rejects_invalid_ata_setup(kind):
    c = ATA_CORPUS["cases"][0]
    response = copy.deepcopy(c["response"])
    ixs = response["result"]["value"]["innerInstructions"][0]["instructions"]
    if kind == "extension":
        ixs[0]["parsed"]["info"]["extensionTypes"] = ["unknown"]
    if kind == "owner":
        ixs[3]["parsed"]["info"]["owner"] = "1"
    if kind == "lamports":
        ixs[1]["parsed"]["info"]["lamports"] = -1
    with pytest.raises(ValueError):
        analyze_simulation_routes(base64.b64decode(c["wire"]), response)


def test_compiled_entry_requires_execution_status():
    c = CORPUS["cases"][0]
    tx, _ = decode_wire_transaction(base64.b64decode(c["wire"]))
    meta = copy.deepcopy(c["response"]["result"]["value"])
    del meta["err"]
    meta["innerInstructions"] = []
    with pytest.raises(ValueError, match="status"):
        analyze_rpc_transaction_routes(dict(transaction=tx, meta=meta))


@pytest.mark.parametrize("shape", [None, [], "invalid"])
def test_rejects_malformed_parsed_payload(shape):
    c = CORPUS["cases"][0]
    response = copy.deepcopy(c["response"])
    response["result"]["value"]["innerInstructions"][0]["instructions"][0][
        "parsed"
    ] = shape
    with pytest.raises(ValueError, match="parsed"):
        analyze_simulation_routes(base64.b64decode(c["wire"]), response)


@pytest.mark.parametrize("case", LIVE_CORPUS["cases"], ids=lambda c: c["name"])
def test_current_bank_simulation(case):
    route = analyze_simulation_routes(base64.b64decode(case["wire"]), case["response"])
    assert canonical(route.to_dict()) == case["expected"]
    if not route.succeeded:
        assert all(
            l.actual_input_amount is None and l.actual_output_amount is None
            for l in route.legs
        )


def test_compiled_cpi_evidence_preserved():
    c = CORPUS["cases"][0]
    wire = base64.b64decode(c["wire"])
    response = copy.deepcopy(c["response"])
    tx, _ = decode_wire_transaction(wire)
    ix = response["result"]["value"]["innerInstructions"][0]["instructions"][0]
    info = ix["parsed"]["info"]
    keys = tx["message"]["accountKeys"]
    response["result"]["value"]["innerInstructions"][0]["instructions"][0] = dict(
        programIdIndex=keys.index(ix["programId"]),
        accounts=[keys.index(info[k]) for k in ("source", "destination", "authority")],
        data=base58.b58encode(struct.pack("<BQ", 3, int(info["amount"]))).decode(),
        stackHeight=ix["stackHeight"],
    )
    assert (
        canonical(analyze_simulation_routes(wire, response).to_dict()) == c["expected"]
    )


ALT_CASE = json.loads((Path(__file__).parent / "fixtures/simulation_alt_20261008.json").read_text())["cases"][0]


def test_resolved_alt_simulation():
    before = copy.deepcopy(ALT_CASE["response"])
    route = analyze_simulation_routes(base64.b64decode(ALT_CASE["wire"]), before)
    assert canonical(route.to_dict()) == ALT_CASE["expected"]
    assert route.succeeded and len(route.legs) == 2
    assert before == ALT_CASE["response"]


@pytest.mark.parametrize("kind", ["missing", "short_writable", "extra_writable", "short_readonly", "extra_readonly", "invalid_key"])
def test_invalid_alt_resolution(kind):
    response = copy.deepcopy(ALT_CASE["response"])
    value = response["result"]["value"]
    if kind == "missing":
        del value["loadedAddresses"]
    elif kind == "invalid_key":
        value["loadedAddresses"]["writable"][0] = "1"
    else:
        action, side = kind.split("_")
        addresses = value["loadedAddresses"][side]
        if action == "short": addresses.pop()
        else: addresses.append(addresses[0])
    with pytest.raises(ValueError):
        analyze_simulation_routes(base64.b64decode(ALT_CASE["wire"]), response)


def test_no_alt_rejects_extra_loaded_addresses():
    c = CORPUS["cases"][0]
    response = copy.deepcopy(c["response"])
    response["result"]["value"]["loadedAddresses"] = {"writable": [], "readonly": []}
    assert canonical(analyze_simulation_routes(base64.b64decode(c["wire"]), response).to_dict()) == c["expected"]
    response["result"]["value"]["loadedAddresses"]["readonly"] = [ALT_CASE["response"]["result"]["value"]["loadedAddresses"]["readonly"][0]]
    with pytest.raises(ValueError):
        analyze_simulation_routes(base64.b64decode(c["wire"]), response)


@pytest.mark.parametrize("case", CORPUS["cases"], ids=lambda c: c["name"])
def test_real_simulation_routes(case, monkeypatch):
    import requests

    monkeypatch.setattr(requests, "post", lambda *a, **k: pytest.fail("implicit RPC"))
    wire = base64.b64decode(case["wire"])
    before = copy.deepcopy(case["response"])
    route = analyze_simulation_routes(wire, case["response"])
    assert canonical(route.to_dict()) == case["expected"] and case["response"] == before
    assert len(route.legs) == (3 if case["name"].startswith("route") else 1)
    assert all(l.actual_input_amount == l.specified_amount for l in route.legs)
    assert len(route.native_token_actions) == 2
    assert all(
        a.account != "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5"
        for a in route.native_token_actions
    )
    tx, _ = decode_wire_transaction(wire)
    i = tx["message"]["accountKeys"].index(
        "96gYZGLnJYVFmbjzopPSU6QiEV5fGqZNyN9nmNhvrZU5"
    )
    v = case["response"]["result"]["value"]
    assert int(v["postBalances"][i]) - int(v["preBalances"][i]) == 5000
    with pytest.raises(ValueError, match="compiled"):
        analyze_rpc_transaction_routes(dict(transaction=tx, meta=v))


def test_failure_keeps_intent_without_fills():
    c = CORPUS["cases"][2]
    response = copy.deepcopy(c["response"])
    response["result"]["value"]["err"] = {"InstructionError": [8, "Custom"]}
    r = analyze_simulation_routes(base64.b64decode(c["wire"]), response)
    assert not r.succeeded and len(r.legs) == 3
    assert all(
        l.actual_input_amount is None and l.actual_output_amount is None for l in r.legs
    )


def test_explicit_fee_and_unknown_net_output():
    c = next(c for c in CORPUS["cases"] if c["name"] == "route-buy")
    wire = base64.b64decode(c["wire"])
    response = copy.deepcopy(c["response"])
    original = analyze_simulation_routes(wire, response)
    assert original.legs[1].actual_output_amount is None
    ix = next(
        ix
        for g in response["result"]["value"]["innerInstructions"]
        for ix in g["instructions"]
        if ix["programId"] == TOKEN_2022
        and ix.get("parsed", {}).get("info", {}).get("destination")
        == original.legs[1].output_account
    )
    assert ix["parsed"]["type"] == "transferChecked"
    gross = int(ix["parsed"]["info"]["tokenAmount"]["amount"])
    ix["parsed"]["type"] = "transferCheckedWithFee"
    ix["parsed"]["info"]["feeAmount"] = "7"
    assert (
        analyze_simulation_routes(wire, response).legs[1].actual_output_amount
        == gross - 7
    )
    del ix["parsed"]["info"]["feeAmount"]
    with pytest.raises(ValueError):
        analyze_simulation_routes(wire, response)


@pytest.mark.parametrize(
    "kind",
    ["amount", "program", "account", "kind", "group", "stack", "missing", "error"],
)
def test_invalid_simulation_evidence(kind):
    c = CORPUS["cases"][0]
    response = copy.deepcopy(c["response"])
    v = response["result"]["value"]
    ix = v["innerInstructions"][0]["instructions"][0]
    if kind == "amount":
        ix["parsed"]["info"]["amount"] = 1.5
    if kind == "program":
        ix["programId"] = decode_wire_transaction(base64.b64decode(c["wire"]))[0][
            "message"
        ]["accountKeys"][0]
    if kind == "account":
        ix["parsed"]["info"]["source"] = "not-in-transaction"
    if kind == "kind":
        ix["parsed"]["type"] = "approve"
    if kind == "group":
        v["innerInstructions"].append(v["innerInstructions"][0])
    if kind == "stack":
        ix["stackHeight"] = 1
    if kind == "missing":
        del v["innerInstructions"]
    if kind == "error":
        response["error"] = {"code": -1, "message": "no simulation"}
    with pytest.raises(ValueError):
        analyze_simulation_routes(base64.b64decode(c["wire"]), response)

PUMPSWAP_CORPUS=json.loads((Path(__file__).parent/'fixtures/pumpswap_mainnet_simulations_20261004.json').read_text())
@pytest.mark.parametrize('case',PUMPSWAP_CORPUS['cases'],ids=lambda c:c['name'])
def test_pumpswap_mainnet_simulation(case):
    route=analyze_simulation_routes(base64.b64decode(case['wire']),case['response'])
    assert canonical(route.to_dict())==case['expected']
    assert route.succeeded and len(route.legs)==1
    if case['name']=='pumpswap_buy': assert route.legs[0].actual_output_amount is None

DAMM_CORPUS=json.loads((Path(__file__).parent/'fixtures/damm_v2_mainnet_simulations_20261004.json').read_text())
@pytest.mark.parametrize('case',DAMM_CORPUS['cases'],ids=lambda c:c['name'])
def test_damm_actual_simulation(case):
    route=analyze_simulation_routes(base64.b64decode(case['wire']),case['response'])
    assert canonical(route.to_dict())==case['expected']
    if not route.succeeded:
        assert all(leg.actual_input_amount is None and leg.actual_output_amount is None for leg in route.legs)


PUMPFUN_CORPUS=json.loads((Path(__file__).parent/'fixtures/pumpfun_current_mainnet_simulations_20261004.json').read_text())
PUMPFUN_SETTLEMENT_CORPUS=json.loads((Path(__file__).parent/'fixtures/pumpfun_settlement_mainnet_simulations_20261004.json').read_text())
PUMPFUN_SELL_CORPUS=json.loads((Path(__file__).parent/'fixtures/pumpfun_funded_sell_mainnet_simulations_20261004.json').read_text())
PUMPFUN_USDC_CORPUS=json.loads((Path(__file__).parent/'fixtures/pumpfun_usdc_multihop_mainnet_simulations_20261004.json').read_text())
PUMPFUN_CONCENTRATED_CORPUS=json.loads((Path(__file__).parent/'fixtures/pumpfun_concentrated_multihop_mainnet_simulations_20261005.json').read_text())
@pytest.mark.parametrize('case',PUMPFUN_CONCENTRATED_CORPUS['cases'],ids=lambda c:c['name'])
def test_native_curve_concentrated_multihop_simulation(case):
    route=analyze_simulation_routes(base64.b64decode(case['wire']),case['response'])
    assert canonical(route.to_dict())==case['expected']
    assert route.succeeded and len(route.legs)==2
    buy=case['name'].endswith('buy')
    assert route.legs[0].actual_input_amount==(1000 if buy else 100000000)
    dex=route.legs[0 if buy else 1]
    assert dex.protocol=={'whirlpool':'OrcaWhirlpool','dlmm':'MeteoraDlmm','clmm':'RaydiumClmm'}[case['name'].split('_')[0]]
    assert dex.actual_output_amount is not None and dex.actual_output_amount>=dex.other_amount_threshold
    # PumpFun modifies wallet lamports directly on sell; its output remains unknown.
    assert route.legs[1 if buy else 0].actual_output_amount is None
@pytest.mark.parametrize('case',PUMPFUN_USDC_CORPUS['cases'],ids=lambda c:c['name'])
def test_native_curve_usdc_multihop_simulation(case):
    route=analyze_simulation_routes(base64.b64decode(case['wire']),case['response'])
    assert canonical(route.to_dict())==case['expected']
    assert route.succeeded and len(route.legs)==2
    if case['name'].endswith('buy'):
        assert route.legs[0].actual_input_amount==1000 and route.legs[1].actual_input_amount==7800
    else:
        assert route.legs[0].actual_input_amount==100000000 and route.legs[1].actual_input_amount==7452
@pytest.mark.parametrize('case',PUMPFUN_SELL_CORPUS['cases'],ids=lambda c:c['name'])
def test_funded_pumpfun_sell_simulation(case):
    route=analyze_simulation_routes(base64.b64decode(case['wire']),case['response'])
    assert canonical(route.to_dict())==case['expected']
    assert len(route.legs)==1 and route.legs[0].output_account==route.legs[0].trader
    assert route.legs[0].actual_input_amount==(100000000 if route.succeeded else None)
    assert route.legs[0].actual_output_amount is None
@pytest.mark.parametrize('case',PUMPFUN_SETTLEMENT_CORPUS['cases'],ids=lambda c:c['name'])
def test_pumpfun_actual_settlement_simulation(case):
    route=analyze_simulation_routes(base64.b64decode(case['wire']),case['response'])
    assert canonical(route.to_dict())==case['expected']
    assert route.legs[0].actual_input_amount==10000
    if case['name'].startswith('funded_wsol'):
        assert any(t.mint=='So11111111111111111111111111111111111111112' and t.amount==10000 for t in route.transfers)
        assert any(isinstance(a.action,dict) and 'Close' in a.action for a in route.native_token_actions)
@pytest.mark.parametrize('case',PUMPFUN_CORPUS['cases'],ids=lambda c:c['name'])
def test_pumpfun_mainnet_simulation(case):
    route=analyze_simulation_routes(base64.b64decode(case['wire']),case['response'])
    assert canonical(route.to_dict())==case['expected']
    assert len(route.legs)==1 and route.legs[0].protocol=='PumpFun'
    assert route.legs[0].actual_input_amount == 10000
    assert route.legs[0].input_account == route.legs[0].trader

@pytest.mark.parametrize('condition',['missing_pool','nested','unknown_recipient','missing_depth','overflow'])
def test_native_pumpfun_debit_requires_unambiguous_evidence(condition):
    case=PUMPFUN_CORPUS['cases'][0];response=copy.deepcopy(case['response'])
    payments=[ix for g in response['result']['value']['innerInstructions'] for ix in g['instructions'] if ix.get('program')=='system' and ix.get('parsed',{}).get('type')=='transfer']
    pool=case['expected']['legs'][0]['pool']
    for ix in payments:
        if condition=='nested':ix['stackHeight']=3
        elif condition=='missing_depth':ix.pop('stackHeight',None)
        elif condition=='missing_pool' and ix['parsed']['info']['destination']==pool:ix['stackHeight']=3
        elif condition=='unknown_recipient':ix['parsed']['info']['destination']=case['expected']['legs'][0]['output_account']
        elif condition=='overflow':ix['parsed']['info']['lamports']=str((1<<64)-1)
    route=analyze_simulation_routes(base64.b64decode(case['wire']),response)
    assert route.succeeded and len(route.legs)==1
    assert route.legs[0].actual_input_amount is None

@pytest.mark.parametrize('discriminator,exact_in',[
    ('c2ab1c46684d5b2f',True),('b817ee6167c5d33d',False),('5df6823ce7e940b2',True)
])
def test_failed_pumpfun_v2_retains_intent(discriminator,exact_in):
    import copy
    case=PUMPFUN_CORPUS['cases'][0]
    wire=base64.b64decode(case['wire'])
    original=bytes.fromhex('c2ab1c46684d5b2f')
    assert wire.count(original)==1
    response=copy.deepcopy(case['response'])
    response['result']['value']['err']={'InstructionError':[0,'Custom']}
    route=analyze_simulation_routes(wire.replace(original,bytes.fromhex(discriminator)),response)
    assert not route.succeeded and len(route.legs)==1
    assert route.legs[0].amount_specified_is_input is exact_in
    assert route.legs[0].actual_input_amount is None and route.legs[0].actual_output_amount is None

CACHED_DAMM_CORPUS=json.loads((Path(__file__).parent/'fixtures/cached_damm_v2_mainnet_simulations_20261004.json').read_text())
@pytest.mark.parametrize('case',CACHED_DAMM_CORPUS['cases'],ids=lambda c:c['name'])
def test_cached_damm_simulation(case):
    route=analyze_simulation_routes(base64.b64decode(case['wire']),case['response'])
    assert canonical(route.to_dict())==case['expected']
    assert len(route.legs)==1 and route.legs[0].protocol=='MeteoraDammV2'
    if route.succeeded:
        assert route.legs[0].actual_input_amount==10000
        # This Token-2022 transfer lacks verified withheld-fee evidence.
        assert route.legs[0].actual_output_amount is None
    else:
        assert route.legs[0].actual_input_amount is None
        assert route.legs[0].actual_output_amount is None
@pytest.mark.parametrize('mode',[0,1,2,3])
def test_damm_swap2_mode_intent(mode):
    case=CACHED_DAMM_CORPUS['cases'][0]
    wire=base64.b64decode(case['wire'])
    original=bytes([65,75,63,76,235,91,91,136])+struct.pack('<QQB',10000,1,0)
    assert wire.count(original)==1
    modified=wire.replace(original,original[:-1]+bytes([mode]))
    route=analyze_simulation_routes(modified,case['response'])
    if mode==3:
        assert not route.legs
    else:
        assert len(route.legs)==1
        assert route.legs[0].amount_specified_is_input is (mode!=2)
        assert route.legs[0].specified_amount==10000
        assert route.legs[0].other_amount_threshold==1

LP_CORPUS = json.loads((Path(__file__).parent / "fixtures/cpmm_lp_simulations_20261006.json").read_text())

@pytest.mark.parametrize("case", LP_CORPUS["cases"], ids=lambda c: c["name"])
def test_lp_simulation_preserves_funding_swap_without_inventing_lp_transfer(case):
    route = analyze_simulation_routes(base64.b64decode(case["wire"]), case["response"])
    assert canonical(route.to_dict()) == case["expected"]
    assert route.succeeded and len(route.legs) == 1

@pytest.mark.parametrize("kind,opcode", [("mintTo",7),("burn",8),("mintToChecked",14),("burnChecked",15)])
@pytest.mark.parametrize("program", ["TokenkegQfeZyiNwAJbNbGKPFXCWuBvf9Ss623VQ5DA", TOKEN_2022])
def test_supply_cpi_exact_encoding_and_integer_validation(kind, opcode, program):
    from sol_parser.simulation_route import _account_setup
    checked = kind.endswith("Checked")
    minting = kind.startswith("mintTo")
    key = "multisigMintAuthority" if minting else "multisigAuthority"
    info = dict(mint="mint", account="account", signers=["signer"], **{key:"authority"})
    amount = dict(amount=str((1<<64)-1), decimals=255)
    if checked: info["tokenAmount"] = amount
    else: info["amount"] = amount["amount"]
    accounts, data = _account_setup(program, kind, info)
    assert accounts == (["mint","account"] if minting else ["account","mint"]) + ["authority","signer"]
    assert data == struct.pack("<BQ", opcode, (1<<64)-1) + (bytes([255]) if checked else b"")
    for invalid in [str(1<<64), "-1", True, 1.5]:
        malformed=copy.deepcopy(info)
        (malformed["tokenAmount"] if checked else malformed)["amount"]=invalid
        with pytest.raises(ValueError): _account_setup(program, kind, malformed)
    malformed=copy.deepcopy(info);malformed["signers"]="signer"
    with pytest.raises(ValueError): _account_setup(program, kind, malformed)
    if checked:
        malformed=copy.deepcopy(info);malformed["tokenAmount"]["decimals"]=256
        with pytest.raises(ValueError): _account_setup(program, kind, malformed)

LIFECYCLE=json.loads((Path(__file__).parent/'fixtures/account_lifecycle_20261008.json').read_text())
@pytest.mark.parametrize('case',LIFECYCLE['cases'],ids=lambda c:c['name'])
def test_current_bank_account_lifecycle_and_rollback(case):
    route=analyze_simulation_routes(base64.b64decode(case['wire']),case['response'])
    assert canonical(route.to_dict())==case['expected']
    validation=case['validation']
    if validation['status']=='execution_verified':
        assert route.succeeded and validation['bank_net_credit']>0
    else:
        assert not route.succeeded and route.legs
        assert all(l.actual_input_amount is None and l.actual_output_amount is None for l in route.legs)
        error=case['response']['result']['value']['err']
        assert error['InstructionError'][0]==validation['expected_failure_index']
        assert error['InstructionError'][1]==({'Custom':11}if validation['scenario']=='close_funded_token_account'else'IllegalOwner')
        assert case['response']['result']['value']['accounts']==[None]

SETTLEMENT=json.loads((Path(__file__).parent/'fixtures/native_settlement_20261008.json').read_text())
@pytest.mark.parametrize('case',SETTLEMENT['cases'],ids=lambda c:c['name'])
def test_current_bank_combined_native_settlement(case):
    route=analyze_simulation_routes(base64.b64decode(case['wire']),case['response'])
    parsed=canonical(route.to_dict())
    assert parsed==case['expected']
    assert route.succeeded and len(route.legs)>=2
    validation=case['validation']
    assert validation['new_account_lamports']>=validation['minimum_lamports']
    assert validation['base_net_credit']>=validation['minimum_base_net_credit']>0
    closed={a['account'] for a in parsed['native_token_actions'] if isinstance(a['action'],dict) and 'Close' in a['action']}
    assert closed==set(validation['closed_accounts'])
    if validation['existing_wsol_preserved']:
        funding=[a for a in parsed['native_token_actions'] if isinstance(a['action'],dict) and a['action'].get('Fund',{}).get('lamports')=='777']
        assert len(funding)==1 and funding[0]['account'] not in closed
