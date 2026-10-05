import base58, copy, pytest
from sol_parser.stonkfun_registry import StonkFunPoolRegistry, StonkFunGraduatedPool
from sol_parser.transaction_route import PROGRAMS, STANDARD

pk = lambda n: base58.b58encode(bytes([n]) * 32).decode()


def migration():
    keys = [pk(i + 1) for i in range(28)]
    keys[3] = STANDARD
    keys[4] = PROGRAMS["RaydiumCpmm"]
    keys.append(PROGRAMS["LaunchLab"])
    return dict(
        slot=1,
        transaction=dict(
            signatures=[base58.b58encode(bytes([31]) * 64).decode()],
            message=dict(
                accountKeys=keys,
                instructions=[
                    dict(
                        programIdIndex=28,
                        accounts=list(range(28)),
                        data=base58.b58encode(
                            bytes.fromhex("885cc8671cda908c")
                        ).decode(),
                    )
                ],
            ),
        ),
        meta=dict(err=None),
    )


def test_registry_valid_replay_and_failed():
    tx = migration()
    r = StonkFunPoolRegistry()
    assert r.observe_rpc_transaction(tx) == 1
    assert r.observe_rpc_transaction(tx) == 0
    tx["meta"]["err"] = {"InstructionError": [0, "x"]}
    assert StonkFunPoolRegistry().observe_rpc_transaction(tx) == 0


@pytest.mark.parametrize(
    "kind", ["missing_status", "negative_program", "bad_account", "duplicate_group"]
)
def test_registry_rejects_bad_evidence_atomically(kind):
    tx = migration()
    ix = tx["transaction"]["message"]["instructions"][0]
    if kind == "missing_status":
        del tx["meta"]["err"]
    if kind == "negative_program":
        ix["programIdIndex"] = -1
    if kind == "bad_account":
        ix["accounts"][27] = 99
    if kind == "duplicate_group":
        tx["meta"]["innerInstructions"] = [dict(index=0, instructions=[])] * 2
    r = StonkFunPoolRegistry()
    with pytest.raises(ValueError):
        r.observe_rpc_transaction(tx)
    assert r.verified_cpmm_pools() == []


def test_registry_bool_slot_rejected():
    p = StonkFunGraduatedPool(
        pk(1),
        pk(2),
        pk(3),
        pk(4),
        STANDARD,
        base58.b58encode(bytes([31]) * 64).decode(),
        True,
    )
    with pytest.raises(ValueError):
        p.validate()
