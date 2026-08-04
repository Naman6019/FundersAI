from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.mf_ingestion.jobs import promote_mf_disclosures


class Query:
    def __init__(self, rows):
        self.rows = list(rows)
        self.eq_filter = None
        self.in_filter = None

    def select(self, _fields):
        return self

    def eq(self, field, value):
        self.eq_filter = (field, value)
        return self

    def in_(self, field, values):
        self.in_filter = (field, {str(value) for value in values})
        return self

    def execute(self):
        rows = self.rows
        if self.eq_filter:
            field, value = self.eq_filter
            rows = [row for row in rows if row.get(field) == value]
        if self.in_filter:
            field, values = self.in_filter
            rows = [row for row in rows if str(row.get(field)) in values]
        return SimpleNamespace(data=rows)


class Client:
    def __init__(self):
        self.tables = {
            "mutual_fund_family_mapping": [
                {"scheme_code": "100", "family_id": "family-a"},
                {"scheme_code": "101", "family_id": "family-a"},
                {"scheme_code": "102", "family_id": "family-a"},
            ],
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "100",
                    "amc_name": "HDFC Mutual Fund",
                    "benchmark": "NIFTY 500 TRI",
                    "risk_level": "Very High",
                    "provider_payload": {},
                },
                {
                    "scheme_code": "101",
                    "amc_name": "HDFC Mutual Fund",
                    "benchmark": None,
                    "risk_level": None,
                    "provider_payload": {},
                },
                {
                    "scheme_code": "102",
                    "amc_name": "HDFC Mutual Fund",
                    "benchmark": "BSE 500 TRI",
                    "risk_level": None,
                    "provider_payload": {},
                },
                {
                    "scheme_code": "999",
                    "amc_name": "Other Mutual Fund",
                    "benchmark": None,
                    "risk_level": None,
                    "provider_payload": {},
                },
            ],
        }

    def table(self, name):
        return Query(self.tables[name])


def test_family_plan_propagates_only_safe_invariant_fields(monkeypatch):
    monkeypatch.setattr(promote_mf_disclosures, "supabase", Client())
    candidate = {
        "source_document_id": "doc-1",
        "amc_code": "HDFC",
        "mapped_scheme_code": "100",
        "mapped_family_id": "family-a",
        "benchmark": "NIFTY 500 TRI",
        "risk_level": "Very High",
    }

    plan = promote_mf_disclosures.build_family_invariant_propagation_plan(
        candidate,
        ["benchmark", "risk", "ter_aum"],
        date(2026, 7, 1),
        requested_by="test",
    )

    assert plan["fields"] == ["risk_level"]
    assert "benchmark" in plan["conflicts"]
    assert {row["scheme_code"] for row in plan["updates"]} == {"101", "102"}
    assert all(set(row) == {"scheme_code", "risk_level", "provider_payload"} for row in plan["updates"])
    provenance = plan["updates"][0]["provider_payload"]["official_family_propagation"]["risk_level"]
    assert provenance["source_document_id"] == "doc-1"
    assert provenance["report_month"] == "2026-07-01"
