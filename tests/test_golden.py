"""金样：固定输入下 ``parse_log_unified`` 输出与 fixtures 一致。"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "golden_parse_log.json"


def _norm(obj: object) -> object:
    if isinstance(obj, dict):
        return {k: _norm(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_norm(x) for x in obj]
    return obj


@pytest.mark.parametrize("case", json.loads(_FIXTURES.read_text(encoding="utf-8"))["cases"])
def test_golden_parse_log(case: dict) -> None:
    from sol_parser.json_util import dex_event_json_dumps
    from sol_parser.parser import parse_log_unified

    ev = parse_log_unified(
        case["log"],
        case["signature"],
        int(case["slot"]),
        case.get("block_time_us"),
    )
    if case.get("expect_event") is None:
        assert ev is None
        return
    assert _norm(json.loads(dex_event_json_dumps(ev))) == _norm(case["expect_event"])
