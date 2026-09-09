from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def _load_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "run_fund_truth_check_eval.py"
    spec = importlib.util.spec_from_file_location("run_fund_truth_check_eval", script_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


runner = _load_module()


def _record(*, entity_count: int, resolution_status: str) -> dict:
    return {
        "case": {"expected": {"entity_count": entity_count}},
        "response": {"resolved_entities": [{"resolution_status": resolution_status}]},
    }


def test_data_plane_guard_reports_resolution_coverage() -> None:
    required, resolved = runner._assert_data_plane_available(
        {
            "resolved": _record(entity_count=1, resolution_status="supported"),
            "safety_only": _record(entity_count=0, resolution_status="not_found"),
        }
    )

    assert (required, resolved) == (1, 1)


def test_data_plane_guard_rejects_a_vacuous_all_unresolved_run() -> None:
    with pytest.raises(RuntimeError, match="evaluation_data_plane_unavailable"):
        runner._assert_data_plane_available(
            {"unresolved": _record(entity_count=1, resolution_status="not_found")}
        )
