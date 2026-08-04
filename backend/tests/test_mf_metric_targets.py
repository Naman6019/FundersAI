from __future__ import annotations

from types import SimpleNamespace

from app.services.mf_metric_target_service import (
    prioritized_metric_targets,
    supported_metric_targets,
)


class Query:
    def __init__(self, rows):
        self.rows = list(rows)
        self.filters = {}
        self.in_filter = None
        self.start = 0
        self.end = None

    def select(self, _fields):
        return self

    def eq(self, field, value):
        self.filters[field] = value
        return self

    def order(self, field, desc=False):
        self.rows.sort(key=lambda row: str(row.get(field) or ""), reverse=desc)
        return self

    def range(self, start, end):
        self.start, self.end = start, end
        return self

    def in_(self, field, values):
        self.in_filter = (field, {str(value) for value in values})
        return self

    def execute(self):
        rows = self.rows
        for field, value in self.filters.items():
            rows = [row for row in rows if row.get(field) == value]
        if self.in_filter:
            field, values = self.in_filter
            rows = [row for row in rows if str(row.get(field)) in values]
        end = self.end + 1 if self.end is not None else None
        return SimpleNamespace(data=rows[self.start:end])


class Client:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return Query(self.tables.get(name, []))


def test_supported_targets_keep_latest_validated_row_per_scheme():
    client = Client({
        "mf_factsheet_candidates": [
            {
                "amc_code": "HDFC",
                "report_month": "2026-07-01",
                "mapped_scheme_code": "101",
                "mapped_family_id": "family-a",
                "mapping_status": "mapped",
                "mapping_confidence": 99,
                "promotion_status": "promoted",
            },
            {
                "amc_code": "HDFC",
                "report_month": "2026-06-01",
                "mapped_scheme_code": "101",
                "mapped_family_id": "family-old",
                "mapping_status": "mapped",
                "mapping_confidence": 99,
                "promotion_status": "promoted",
            },
            {
                "amc_code": "HDFC",
                "report_month": "2026-07-01",
                "mapped_scheme_code": "102",
                "mapped_family_id": "family-b",
                "mapping_status": "mapped",
                "mapping_confidence": 80,
                "promotion_status": "promoted",
            },
        ]
    })

    assert supported_metric_targets(client) == [{
        "scheme_code": "101",
        "family_id": "family-a",
        "amc_code": "HDFC",
        "report_month": "2026-07-01",
        "promotion_status": "promoted",
    }]


def test_metric_targets_prioritize_missing_then_stale_then_fresh():
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
            {"scheme_code": "102", "expires_at": "2020-01-01T00:00:00+00:00", "updated_at": "2020-01-01"},
            {"scheme_code": "103", "expires_at": "2099-01-01T00:00:00+00:00", "updated_at": "2026-01-01"},
        ],
    })

    assert [row["scheme_code"] for row in prioritized_metric_targets(client)] == ["101", "102", "103"]
