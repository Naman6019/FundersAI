from __future__ import annotations

import scripts.report_mf_staging_coverage as staging_coverage
from scripts.report_mf_staging_coverage import (
    _get_by_source_document_ids,
    build_staging_coverage,
)


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.source_ids = []
        self.start = 0
        self.end = 999

    def select(self, _columns):
        return self

    def in_(self, column, values):
        assert column == "source_document_id"
        self.source_ids = values
        return self

    def order(self, column):
        assert column == "id"
        return self

    def range(self, start, end):
        self.start = start
        self.end = end
        return self

    def execute(self):
        filtered = [
            row for row in self.rows if row["source_document_id"] in self.source_ids
        ]
        return _FakeResponse(filtered[self.start : self.end + 1])


class _FakeSupabase:
    def __init__(self, rows):
        self.rows = rows

    def table(self, _table):
        return _FakeQuery(self.rows)


def test_staging_coverage_reads_holdings_by_indexed_source_document(monkeypatch):
    rows = [
        {"id": "1", "source_document_id": "doc-a"},
        {"id": "2", "source_document_id": "doc-b"},
        {"id": "3", "source_document_id": "doc-c"},
    ]
    monkeypatch.setattr(staging_coverage, "supabase", _FakeSupabase(rows))

    assert _get_by_source_document_ids(
        "mf_scheme_holdings",
        "id,source_document_id",
        ["doc-a", "doc-c"],
        chunk_size=1,
        page_size=1,
    ) == [rows[0], rows[2]]


def test_staging_coverage_uses_distinct_current_mapped_families():
    report = build_staging_coverage(
        report_month="2026-06-01",
        amcs=["mirae"],
        candidates=[
            {
                "amc_code": "mirae",
                "report_month": "2026-06-01",
                "normalized_scheme_name": "mirae asset one fund",
                "mapped_family_id": "one",
                "mapping_status": "mapped",
                "aum": 1,
                "expense_ratio": 1,
                "benchmark": "Index",
                "fund_manager": "Manager",
                "risk_level": "High",
            },
            {
                "amc_code": "mirae",
                "report_month": "2026-06-01",
                "normalized_scheme_name": "mirae asset two fund",
                "mapped_family_id": None,
                "mapping_status": "unmapped",
            },
        ],
        holdings=[
            {
                "amc_code": "mirae",
                "report_month": "2026-06-01",
                "raw_scheme_name": "Mirae Asset One Fund",
                "mapped_family_id": "one",
                "mapping_status": "mapped",
                "sector": "Banks",
            },
            {
                "amc_code": "mirae",
                "report_month": "2026-06-01",
                "raw_scheme_name": "Mirae Asset Two Fund",
                "mapped_family_id": None,
                "mapping_status": "unmapped",
                "sector": None,
            },
        ],
        threshold=80.0,
    )["mirae"]

    assert report["mapped_core_families"] == 1
    assert report["percentages"]["aum"] == 100.0
    assert report["mapping_percentages"]["core"] == 50.0
    assert report["mapping_percentages"]["portfolio"] == 50.0
    assert report["passes_all_fields"] is False


def test_staging_coverage_separates_non_applicable_sectors_from_missing_sectors():
    candidates = [
        {
            "amc_code": "mirae",
            "report_month": "2026-06-01",
            "normalized_scheme_name": name.lower(),
            "mapped_family_id": family,
            "mapping_status": "mapped",
            "aum": 1,
            "expense_ratio": 1,
            "benchmark": "Index",
            "fund_manager": "Manager",
            "risk_level": "High",
        }
        for name, family in (
            ("Mirae Asset Equity Fund", "equity"),
            ("Mirae Asset Gold ETF Fund of Fund", "gold-fof"),
        )
    ]
    holdings = [
        {
            "amc_code": "mirae",
            "report_month": "2026-06-01",
            "raw_scheme_name": "Mirae Asset Equity Fund",
            "mapped_family_id": "equity",
            "mapping_status": "mapped",
            "sector": None,
        },
        {
            "amc_code": "mirae",
            "report_month": "2026-06-01",
            "raw_scheme_name": "Mirae Asset Gold ETF Fund of Fund",
            "mapped_family_id": "gold-fof",
            "mapping_status": "mapped",
            "sector": None,
        },
    ]

    report = build_staging_coverage(
        report_month="2026-06-01",
        amcs=["mirae"],
        candidates=candidates,
        holdings=holdings,
        threshold=80.0,
    )["mirae"]

    assert report["sector_applicable_families"] == 1
    assert report["sector_not_applicable_families"] == 1
    assert report["percentages"]["sectors"] == 0.0
    assert report["passes_all_fields"] is False


def test_staging_coverage_maps_absl_database_code_to_aditya_birla_registry_key():
    row = {
        "amc_code": "ABSL",
        "report_month": "2026-06-01",
        "normalized_scheme_name": "aditya birla sun life equity fund",
        "raw_scheme_name": "Aditya Birla Sun Life Equity Fund",
        "mapped_family_id": "absl-equity",
        "mapping_status": "mapped",
        "aum": 1,
        "expense_ratio": 1,
        "benchmark": "Index",
        "fund_manager": "Manager",
        "risk_level": "High",
        "sector": "Banks",
    }

    report = build_staging_coverage(
        report_month="2026-06-01",
        amcs=["aditya_birla"],
        candidates=[row],
        holdings=[row],
        threshold=80.0,
    )["aditya_birla"]

    assert report["mapping_percentages"] == {"core": 100.0, "portfolio": 100.0}
    assert report["passes_all_fields"] is True


def test_staging_coverage_counts_official_aggregate_sector_rows():
    candidate = {
        "amc_code": "motilal",
        "report_month": "2026-06-01",
        "normalized_scheme_name": "motilal oswal midcap fund",
        "mapped_family_id": "motilal-midcap",
        "mapping_status": "mapped",
        "aum": 1,
        "expense_ratio": 1,
        "benchmark": "Index",
        "fund_manager": "Manager",
        "risk_level": "Very High",
    }
    holding = {
        "amc_code": "motilal",
        "report_month": "2026-06-01",
        "raw_scheme_name": "Motilal Oswal Midcap Fund",
        "mapped_family_id": "motilal-midcap",
        "mapping_status": "mapped",
        "sector": None,
    }
    sector = {
        "amc_code": "motilal",
        "report_month": "2026-06-01",
        "raw_scheme_name": "Motilal Oswal Midcap Fund",
        "mapped_family_id": "motilal-midcap",
        "mapping_status": "mapped",
        "validation_status": "valid",
        "sector_name": "Banks",
    }

    report = build_staging_coverage(
        report_month="2026-06-01",
        amcs=["motilal"],
        candidates=[candidate],
        holdings=[holding],
        sector_allocations=[sector],
        threshold=80.0,
    )["motilal"]

    assert report["counts"]["sectors"] == 1
    assert report["percentages"]["sectors"] == 100.0
    assert report["passes_all_fields"] is True
