"""Run the language-native example as a regression test."""
import importlib.util
from pathlib import Path

def test_reported_signed_shred_routes_native_example():
    spec=importlib.util.spec_from_file_location('pump_shred_routes_example',Path(__file__).parents[1]/'examples/pump_shred_routes.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    assert module.run_replay()==6
