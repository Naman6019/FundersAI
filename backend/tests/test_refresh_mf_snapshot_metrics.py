from __future__ import annotations

from datetime import date, timedelta

from app.jobs.refresh_mf_snapshot_metrics import _metric_row
from app.services.mf_metrics_service import NAV_METRIC_SNAPSHOT_VERSION


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
