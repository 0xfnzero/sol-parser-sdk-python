"""Shared offline input normalization. Empty captures and invalid CLI flags fail."""

import argparse
import base64
import json
from pathlib import Path
from sol_parser.wire_transaction import decode_wire_transaction
from sol_parser.rpc_parser import (
    rpc_get_transaction_result_dict_to_response,
    parse_rpc_transaction,
)


def load_cases(default):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, default=default)
    document = json.loads(parser.parse_args().fixture.read_text())
    cases = document.get("cases", [{"rpc": document.get("result", document)}])
    if not isinstance(cases, list) or not cases:
        raise ValueError("Empty or malformed replay")
    return [dict(c, rpc=c.get("rpc", c.get("wire_rpc", c.get("raw")))) for c in cases]


def replay_events(raw, recv_us=1_000_000):
    if isinstance(raw["transaction"], list):
        if raw["transaction"][1] != "base64":
            raise ValueError("Expected base64 transaction")
        body, _ = decode_wire_transaction(base64.b64decode(raw["transaction"][0]))
        raw = dict(raw, transaction=body)
    response = rpc_get_transaction_result_dict_to_response(raw)
    if response is None:
        raise ValueError("Malformed compiled transaction")
    events, error = parse_rpc_transaction(
        response, raw["transaction"]["signatures"][0], None, recv_us
    )
    if error:
        raise ValueError(error)
    return events
