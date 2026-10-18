"""The binary internal path preserves public decoder shape and strict validation."""
import base64
import json
from pathlib import Path
import base58
import pytest
from sol_parser.wire_transaction import decode_wire_transaction, _decode_wire_transaction

CASES=json.loads((Path(__file__).parents[1]/'examples/fixtures/pump_shred_routes.json').read_text())


@pytest.mark.parametrize('case', CASES)
def test_raw_instruction_path_matches_public_decoder(case):
    raw=base64.b64decode(case['wire'])
    public, consumed=decode_wire_transaction(raw)
    private, other=_decode_wire_transaction(raw, raw_instructions=True)
    assert consumed==other==len(raw)
    for ix in private['message']['instructions']:
        assert isinstance(ix['data'],bytes)
        ix['data']=base58.b58encode(ix['data']).decode()
    assert private==public
    for invalid in (raw[:-1], raw+bytes([0])):
        for binary in (False,True):
            with pytest.raises(ValueError):
                _decode_wire_transaction(invalid, raw_instructions=binary)


def test_wire_decoder_without_optional_solders(monkeypatch):
    import importlib.util
    import sys
    import sol_parser.wire_transaction as existing
    monkeypatch.setitem(sys.modules, 'solders', None)
    monkeypatch.setitem(sys.modules, 'solders.pubkey', None)
    monkeypatch.setitem(sys.modules, 'solders.signature', None)
    spec=importlib.util.spec_from_file_location('wire_decoder_fallback',existing.__file__)
    fallback=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fallback)
    for case in CASES:
        raw=base64.b64decode(case['wire'])
        assert fallback.decode_wire_transaction(raw)==decode_wire_transaction(raw)
