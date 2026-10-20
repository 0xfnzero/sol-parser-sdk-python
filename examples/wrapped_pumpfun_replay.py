"""Captured outer inputs only. No RPC; rules are explicitly loaded at startup."""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from sol_parser import format_dex_event_json
from sol_parser.event_types import DexEvent
from sol_parser.grpc_types import EventMetadata, EventType
from sol_parser.raw_instruction import RawInstructionEvent
from sol_parser.wrapped_pumpfun_parser import parse_wrapped_pumpfun_instruction

fixture = json.loads((Path(__file__).resolve().parents[1]/'tests/fixtures/wrapped_pumpfun_inputs.json').read_text())
for item in fixture['inputs']:
    values = dict(item['raw'])
    values['metadata'] = EventMetadata(**values['metadata'])
    raw = RawInstructionEvent(**values)
    event = next((event for rule in fixture['rules'] if (event := parse_wrapped_pumpfun_instruction(raw, rule)) is not None), None)
    print(format_dex_event_json(event or DexEvent(EventType.RAW_INSTRUCTION, raw)))
