from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from app.services import admin_service


class Query:
    def __init__(self, rows):
        self.rows = list(rows)
        self.filters = {}
        self.in_filter = None
        self.count_requested = False
        self.start = 0
        self.end = None

    def select(self, _fields, count=None):
        self.count_requested = count == "exact"
        return self

    def eq(self, field, value):
        self.filters[field] = value
        return self

    def in_(self, field, values):
        self.in_filter = (field, {str(value) for value in values})
        return self

    def order(self, field, desc=False):
        self.rows.sort(key=lambda row: str(row.get(field) or ""), reverse=desc)
        return self

    def range(self, start, end):
        self.start, self.end = start, end
        return self

    def limit(self, value):
        self.start, self.end = 0, value - 1
        return self

    def execute(self):
        rows = self.rows
        for field, value in self.filters.items():
            rows = [row for row in rows if row.get(field) == value]
        if self.in_filter:
            field, values = self.in_filter
            rows = [row for row in rows if str(row.get(field)) in values]
        count = len(rows) if self.count_requested else None
        end = self.end + 1 if self.end is not None else None
        return SimpleNamespace(data=rows[self.start:end], count=count)


class Client:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return Query(self.tables.get(name, []))


def test_metric_health_reports_catalog_and_supported_denominators(monkeypatch):
    candidates = [
        {
            "amc_code": "HDFC",
            "report_month": "2026-07-01",
            "mapped_scheme_code": code,
            "mapped_family_id": f"family-{code}",
            "mapping_status": "mapped",
            "mapping_confidence": 99,
            "promotion_status": "promoted",
        }
        for code in ("101", "102")
    ]
    client = Client({
        "mf_factsheet_candidates": candidates,
        "nav_api_cache": [
            {"scheme_code": code, "point_count": 400, "last_nav_date": "2026-08-03", "expires_at": "2026-08-05T00:00:00+00:00"}
            for code in ("101", "102")
        ],
        "mutual_fund_core_snapshot": [
            {
                "scheme_code": "101",
                "alpha": 1.2,
                "beta": 0.9,
                "benchmark": "NIFTY 500 TRI",
                "risk_level": "Very High",
                "provider_payload": {"metric_snapshot": {"overlap_points": 200, "minimum_overlap_points": 30}},
            },
            {
                "scheme_code": "102",
                "alpha": None,
                "beta": None,
                "benchmark": None,
                "risk_level": None,
                "provider_payload": {"metric_snapshot": {"overlap_points": 0, "minimum_overlap_points": 30}},
            },
        ],
        "stock_prices_daily": [{"symbol": "NIFTY", "date": "2026-08-03"}],
    })
    monkeypatch.setattr(admin_service, "get_admin_repository", lambda: client)

    coverage = admin_service._mf_metric_coverage(datetime(2026, 8, 4, tzinfo=timezone.utc))

    assert coverage["catalog_total"] == 2
    assert coverage["supported_mapped_total"] == 2
    assert coverage["metric_eligible_total"] == 1
    assert coverage["history_ready_count"] == 2
    assert coverage["alpha_beta_count"] == 1
    assert coverage["supported_alpha_beta_coverage"] == 1.0
    assert coverage["supported_history_alpha_beta_count"] == 1
    assert coverage["supported_history_alpha_beta_coverage"] == 0.5
    assert coverage["supported_benchmark_coverage"] == 0.5
    assert coverage["supported_risk_coverage"] == 0.5
    assert coverage["benchmark_freshness"]["fresh"] is True


def test_metric_health_intersects_fresh_history_and_alpha_beta(monkeypatch):
    candidates = [
        {
            "amc_code": "HDFC",
            "report_month": "2026-07-01",
            "mapped_scheme_code": code,
            "mapped_family_id": f"family-{code}",
            "mapping_status": "mapped",
            "mapping_confidence": 99,
            "promotion_status": "promoted",
        }
        for code in ("101", "102", "103")
    ]
    client = Client({
        "mf_factsheet_candidates": candidates,
        "nav_api_cache": [
            {"scheme_code": "101", "point_count": 400, "expires_at": "2026-08-05T00:00:00+00:00"},
            {"scheme_code": "102", "point_count": 400, "expires_at": "2026-08-05T00:00:00+00:00"},
            {"scheme_code": "103", "point_count": 400, "expires_at": "2026-08-03T00:00:00+00:00"},
        ],
        "mutual_fund_core_snapshot": [
            {"scheme_code": "101", "alpha": 1.0, "beta": 0.9, "provider_payload": {"metric_snapshot": {"overlap_points": 100, "minimum_overlap_points": 30}}},
            {"scheme_code": "102", "alpha": None, "beta": None, "provider_payload": {"metric_snapshot": {"overlap_points": 100, "minimum_overlap_points": 30}}},
            {"scheme_code": "103", "alpha": 1.0, "beta": 0.9, "provider_payload": {"metric_snapshot": {"overlap_points": 100, "minimum_overlap_points": 30}}},
        ],
        "stock_prices_daily": [{"symbol": "NIFTY", "date": "2026-08-03"}],
    })
    monkeypatch.setattr(admin_service, "get_admin_repository", lambda: client)

    coverage = admin_service._mf_metric_coverage(datetime(2026, 8, 4, tzinfo=timezone.utc))

    assert coverage["history_ready_count"] == 2
    assert coverage["alpha_beta_count"] == 2
    assert coverage["supported_history_alpha_beta_count"] == 1
    assert coverage["supported_history_alpha_beta_coverage"] == 0.3333
