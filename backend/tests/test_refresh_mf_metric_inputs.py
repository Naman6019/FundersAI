from __future__ import annotations

import json
import sys
from types import SimpleNamespace

from app.jobs import refresh_mf_metric_inputs as job


def test_refresh_job_is_bounded_retries_and_records_failures(monkeypatch, tmp_path):
    targets = [
        {"scheme_code": "101", "family_id": "family-101", "amc_code": "HDFC"},
        {"scheme_code": "102", "family_id": "family-102", "amc_code": "HDFC"},
        {"scheme_code": "103", "family_id": "family-103", "amc_code": "HDFC"},
    ]
    calls = []
    results = {
        "101": [
            {"cache_status": "miss", "point_count": 0, "error": "temporary"},
            {"cache_status": "refreshed", "point_count": 420},
        ],
        "102": [{"cache_status": "refreshed", "point_count": 10}],
    }

    class Repo:
        supabase = SimpleNamespace()

        def create_provider_run(self, _run):
            return "run-1"

        def update_provider_run(self, run_id, run):
            assert run_id == "run-1"
            assert run.symbols_attempted == 2

    def refresh(code, *, force_refresh):
        assert force_refresh is True
        calls.append(code)
        return results[code].pop(0)

    output = tmp_path / "metric-inputs.json"
    monkeypatch.setattr(job, "StockRepository", Repo)
    monkeypatch.setattr(job, "prioritized_metric_targets", lambda _client: targets)
    monkeypatch.setattr(job, "get_cached_nav_history", refresh)
    monkeypatch.setattr(job.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "refresh_mf_metric_inputs",
            "--limit",
            "2",
            "--retries",
            "1",
            "--minimum-success-ratio",
            "0.5",
            "--output",
            str(output),
        ],
    )

    assert job.main() == 0
    assert calls == ["101", "101", "102"]
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["attempted"] == 2
    assert payload["succeeded"] == 1
    assert payload["failed"] == 1
    assert payload["failures"][0]["reason"] == "insufficient_history"
