"""Execute the same language-native example used by SDK consumers."""
import importlib.util
from pathlib import Path

def test_native_pump_bank():
    path=Path(__file__).resolve().parents[1]/'examples/pump_offline_bank.py'
    spec=importlib.util.spec_from_file_location('pump_offline_bank',path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.run_bank()==20
