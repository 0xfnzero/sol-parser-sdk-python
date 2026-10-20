"""python examples/raw_instruction_filter.py — offline signed transaction replay."""
import base64
import json
from pathlib import Path
from sol_parser.shredstream_client import parse_shred_transaction_with_loaded_addresses
from sol_parser.grpc_types import EventType, IncludeOnlyFilter
from sol_parser.json_util import dex_event_json_dumps

for case in json.loads((Path(__file__).parent / "fixtures/raw_instructions.json").read_text()):
    for kind in ("PumpFunTrade", "RaydiumCpmmSwap", "RawInstruction"):
        events = parse_shred_transaction_with_loaded_addresses(
            base64.b64decode(case["wire"]), case["loaded_writable"], case["loaded_readonly"],
            filter=IncludeOnlyFilter([EventType(kind)]))
        print(json.dumps({"signature": case["signature"], "filter": kind,
                          "events": [json.loads(dex_event_json_dumps(e)) for e in events]}))
