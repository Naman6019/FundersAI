from __future__ import annotations

from datetime import date, timedelta

from types import SimpleNamespace

from app.jobs import refresh_mf_snapshot_metrics
from app.jobs.refresh_mf_snapshot_metrics import _benchmark_rows, _cache_row_pages, _metric_row
from app.services.mf_metrics_service import (
    NAV_METRIC_SNAPSHOT_VERSION,
    compute_nav_metrics_with_diagnostics,
)


def _history(days: int, *, daily_base: float) -> list[dict]:
    current = 100.0
    start = date(2025, 1, 1)
    rows = []
    for index in range(days):
        current *= 1 + daily_base + ((index % 7) * 0.00003)
        rows.append({
            "nav_date": (start + timedelta(days=index)).isoformat(),
            "nav": current,
        })
    return rows


def test_metric_row_precomputes_versioned_risk_and_return_snapshot():
    fund_history = _history(420, daily_base=0.0005)
    benchmark_history = [
        {"date": row["nav_date"], "close": row["nav"]}
        for row in _history(420, daily_base=0.0003)
    ]
    result = _metric_row(
        {
            "scheme_code": "101",
            "payload": fund_history,
            "point_count": len(fund_history),
            "last_nav_date": fund_history[-1]["nav_date"],
        },
        {"scheme_code": "101", "provider_payload": {"existing": "kept"}},
        benchmark_history,
        "2026-07-25T00:00:00+00:00",
    )

    assert result is not None
    assert result["return_1y"] is not None
    assert result["volatility_1y"] is not None
    assert result["max_drawdown_1y"] is not None
    assert result["sharpe_ratio"] is not None
    assert result["alpha"] is not None
    assert result["beta"] is not None
    assert result["provider_payload"]["existing"] == "kept"
    assert result["provider_payload"]["metric_snapshot"]["version"] == NAV_METRIC_SNAPSHOT_VERSION
    assert result["provider_payload"]["metric_snapshot"]["history_points"] == 420
    assert result["provider_payload"]["metric_snapshot"]["benchmark_mode"] == "proxy"
    assert result["provider_payload"]["metric_snapshot"]["overlap_points"] >= 30
    assert result["provider_payload"]["metric_snapshot"]["calculation_status"] == "computed"


def test_metric_row_skips_cache_without_matching_core_snapshot():
    assert _metric_row(
        {
            "scheme_code": "101",
            "payload": _history(40, daily_base=0.0005),
            "point_count": 40,
            "last_nav_date": "2026-01-01",
        },
        {},
        [],
        "2026-07-25T00:00:00+00:00",
    ) is None


def test_metric_row_preserves_last_known_good_alpha_beta_when_overlap_is_missing():
    result = _metric_row(
        {
            "scheme_code": "101",
            "payload": _history(40, daily_base=0.0005),
            "point_count": 40,
            "last_nav_date": "2025-02-09",
        },
        {
            "scheme_code": "101",
            "alpha": 1.25,
            "beta": 0.91,
            "provider_payload": {},
        },
        [{"date": "2026-01-01", "close": 100.0}, {"date": "2026-01-02", "close": 101.0}],
        "2026-07-25T00:00:00+00:00",
    )

    assert result is not None
    assert result["alpha"] == 1.25
    assert result["beta"] == 0.91
    snapshot = result["provider_payload"]["metric_snapshot"]
    assert snapshot["last_known_good_used"] is True
    assert snapshot["calculation_status"] == "last_known_good"
    assert snapshot["calculation_failure_reason"] == "insufficient_overlap"


def test_metric_diagnostics_report_insufficient_overlap():
    metrics, diagnostics = compute_nav_metrics_with_diagnostics(
        _history(40, daily_base=0.0005),
        benchmark_rows=[{"date": "2026-01-01", "close": 100.0}],
        risk_free_rate=0.06,
    )

    assert metrics["alpha"] is None
    assert metrics["beta"] is None
    assert diagnostics["calculation_status"] == "insufficient_overlap"
    assert diagnostics["overlap_points"] == 0


def test_benchmark_query_requests_newest_rows_and_returns_ascending_unique_dates():
    class Query:
        def __init__(self):
            self.desc = None

        def select(self, _fields):
            return self

        def eq(self, _field, _value):
            return self

        def order(self, _field, *, desc=False):
            self.desc = desc
            return self

        def limit(self, value):
            assert value == 2200
            return self

        def execute(self):
            assert self.desc is True
            return SimpleNamespace(data=[
                {"date": "2026-07-03", "close": 103, "source": "new"},
                {"date": "2026-07-02", "close": 102, "source": "old"},
                {"date": "2026-07-02", "close": 102.5, "source": "new"},
            ])

    query = Query()
    repo = SimpleNamespace(supabase=SimpleNamespace(table=lambda _name: query))

    rows = _benchmark_rows(repo)

    assert [row["date"] for row in rows] == ["2026-07-02", "2026-07-03"]
    assert rows[0]["source"] == "new"


def test_cache_pages_query_only_supported_codes_in_small_indexed_batches(monkeypatch):
    requested_batches: list[list[str]] = []

    class Query:
        def select(self, _fields):
            return self

        def in_(self, field, values):
            assert field == "scheme_code"
            requested_batches.append(list(values))
            self.values = list(values)
            return self

        def execute(self):
            return SimpleNamespace(
                data=[{"scheme_code": value, "payload": []} for value in reversed(self.values)]
            )

    repo = SimpleNamespace(supabase=SimpleNamespace(table=lambda _name: Query()))
    monkeypatch.setattr(refresh_mf_snapshot_metrics, "PAGE_SIZE", 2)

    pages = list(_cache_row_pages(repo, ["100", "101", "102", "103", "104"], 4))

    assert requested_batches == [["100", "101"], ["102", "103"]]
    assert [[row["scheme_code"] for row in page] for page in pages] == [
        ["100", "101"],
        ["102", "103"],
    ]
