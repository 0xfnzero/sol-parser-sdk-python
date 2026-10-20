import json
from pathlib import Path
from sol_parser.raw_instruction import RawInstructionEvent
from sol_parser.grpc_types import EventMetadata
from sol_parser.wrapped_pumpfun_parser import parse_wrapped_pumpfun_instruction

def test_real_wrapper_inputs():
    fixture = json.loads((Path(__file__).parent/'fixtures/wrapped_pumpfun_inputs.json').read_text())
    count = 0
    for item in fixture['inputs']:
        values = dict(item['raw'])
        values['metadata'] = EventMetadata(**values['metadata'])
        raw = RawInstructionEvent(**values)
        for rule in fixture['rules']:
            event = parse_wrapped_pumpfun_instruction(raw, rule)
            if event is None:
                continue
            assert len(item['actual_cpis']) == 1
            actual = item['actual_cpis'][0]
            t = event.data
            assert t.spendable_quote_in == int.from_bytes(bytes(actual['data'][8:16]), 'little')
            assert t.min_tokens_out == int.from_bytes(bytes(actual['data'][16:24]), 'little')
            assert (t.mint,t.user) == (actual['accounts'][1],actual['accounts'][13])
            assert t.third_program['program_id'] == raw.program_id
            assert (t.sol_amount,t.quote_amount,t.token_amount) == (0,0,0)
            raw.accounts[0] = None
            assert parse_wrapped_pumpfun_instruction(raw, rule) is None
            count += 1
            break
    assert count == 5
