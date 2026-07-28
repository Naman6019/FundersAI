from pathlib import Path
from types import SimpleNamespace

from app.mf_ingestion.jobs import promote_mf_disclosures
from app.mf_ingestion.jobs.promote_mf_amc_disclosures import (
    _build_target_scopes,
    _dedupe_target_scopes,
    _split_scope_groups,
)


class _PagedRpc:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.start = 0
        self.end = len(rows) - 1

    def range(self, start: int, end: int):
        self.start = start
        self.end = end
        return self

    def execute(self):
        return SimpleNamespace(data=self.rows[self.start : self.end + 1])


class _PagedRpcSupabase:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows

    def rpc(self, _function_name: str, _params: dict):
        return _PagedRpc(self.rows)


def test_rpc_rows_are_paginated_past_supabase_default_limit(monkeypatch) -> None:
    rows = [{"id": index} for index in range(2_005)]
    monkeypatch.setattr(
        promote_mf_disclosures,
        "supabase",
        _PagedRpcSupabase(rows),
    )

    assert promote_mf_disclosures._fetch_all_rpc_rows(
        "coverage_rows",
        {"p_report_month": "2026-06-01"},
    ) == rows


def test_amc_batch_promotion_assigns_only_available_source_scopes() -> None:
    targets = _build_target_scopes(
        amc="mirae",
        requested_scopes=[
            "risk",
            "ter_aum",
            "benchmark",
            "manager",
            "holdings",
            "sectors",
        ],
        candidates=[
            {"amc_code": "MIRAE", "source_document_id": "core"},
            {"amc_code": "HDFC", "source_document_id": "other-core"},
        ],
        holdings=[
            {
                "amc_code": "MIRAE",
                "source_document_id": "equity-portfolio",
                "sector": "__present__",
            },
            {
                "amc_code": "MIRAE",
                "source_document_id": "debt-portfolio",
                "sector": None,
            },
        ],
        sector_allocations=[
            {
                "amc_code": "MIRAE",
                "source_document_id": "aggregate-sectors",
                "sector_name": "__present__",
            }
        ],
    )

    assert targets == {
        "aggregate-sectors": ["sectors"],
        "core": ["risk", "ter_aum", "benchmark", "manager"],
        "debt-portfolio": ["holdings"],
        "equity-portfolio": ["holdings"],
    }


def test_amc_batch_promotion_normalizes_absl_database_code() -> None:
    targets = _build_target_scopes(
        amc="aditya_birla",
        requested_scopes=["risk", "holdings"],
        candidates=[{"amc_code": "ABSL", "source_document_id": "absl-core"}],
        holdings=[{"amc_code": "ABSL", "source_document_id": "absl-portfolio"}],
        sector_allocations=[],
    )

    assert targets == {
        "absl-core": ["risk"],
        "absl-portfolio": ["holdings"],
    }


def test_amc_batch_promotion_validates_portfolio_scopes_independently() -> None:
    assert _split_scope_groups(
        ["risk", "ter_aum", "benchmark", "manager", "holdings", "sectors"]
    ) == [
        ["risk", "ter_aum", "benchmark", "manager"],
        ["holdings"],
        ["sectors"],
    ]


def test_amc_batch_promotion_keeps_newest_document_for_same_type_and_url() -> None:
    targets = {
        "old": ["holdings", "sectors"],
        "new": ["holdings", "sectors"],
    }
    documents = [
        {
            "id": "old",
            "document_type": "portfolio_disclosure",
            "checksum": "old-checksum",
            "source_url": "https://official.example/portfolio.xlsx",
            "parsed_at": "2026-07-01T00:00:00+00:00",
        },
        {
            "id": "new",
            "document_type": "portfolio_disclosure",
            "checksum": "new-checksum",
            "source_url": "https://official.example/portfolio.xlsx",
            "parsed_at": "2026-07-15T00:00:00+00:00",
        },
    ]

    assert _dedupe_target_scopes(
        targets,
        documents,
        ["holdings", "sectors"],
    ) == {"new": ["holdings", "sectors"]}


def test_amc_batch_promotion_uses_document_role_for_shared_checksum() -> None:
    targets = {
        "factsheet": ["risk", "holdings", "sectors"],
        "portfolio": ["risk", "holdings", "sectors"],
    }
    documents = [
        {
            "id": "factsheet",
            "document_type": "factsheet",
            "checksum": "shared",
            "source_url": "https://official.example/combined.pdf",
            "parsed_at": "2026-07-15T00:00:00+00:00",
        },
        {
            "id": "portfolio",
            "document_type": "portfolio_disclosure",
            "checksum": "shared",
            "source_url": "https://official.example/combined.pdf",
            "parsed_at": "2026-07-15T00:00:00+00:00",
        },
    ]

    assert _dedupe_target_scopes(
        targets,
        documents,
        ["risk", "holdings", "sectors"],
    ) == {
        "factsheet": ["risk"],
        "portfolio": ["holdings", "sectors"],
    }


def test_amc_batch_promotion_retains_distinct_portfolio_documents() -> None:
    targets = {
        "active": ["holdings"],
        "passive": ["holdings"],
    }
    documents = [
        {
            "id": "active",
            "document_type": "portfolio_disclosure",
            "checksum": "active-checksum",
            "source_url": "https://official.example/active.xlsx",
            "parsed_at": "2026-07-15T00:00:00+00:00",
        },
        {
            "id": "passive",
            "document_type": "portfolio_disclosure",
            "checksum": "passive-checksum",
            "source_url": "https://official.example/passive.xlsx",
            "parsed_at": "2026-07-15T00:00:00+00:00",
        },
    ]

    assert _dedupe_target_scopes(targets, documents, ["holdings"]) == {
        "active": ["holdings"],
        "passive": ["holdings"],
    }


def test_amc_batch_promotion_workflow_is_bounded_and_protected() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = (
        root / ".github" / "workflows" / "promote-mf-amc-disclosures.yml"
    ).read_text(encoding="utf-8")
    job = (
        root
        / "backend"
        / "app"
        / "mf_ingestion"
        / "jobs"
        / "promote_mf_amc_disclosures.py"
    ).read_text(encoding="utf-8")

    assert "environment: production-data" in workflow
    assert 'expected_approval="PROMOTE AMC ${AMC} ${EXPECTED_MONTH}"' in workflow
    assert "--max-source-documents" in workflow
    assert "DEFAULT_MAX_SOURCE_DOCUMENTS = 150" in job
    assert "Revalidate every target immediately before the first mutation." in job
