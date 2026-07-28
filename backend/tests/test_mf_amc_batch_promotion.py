from pathlib import Path

from app.mf_ingestion.jobs.promote_mf_amc_disclosures import (
    _build_target_scopes,
    _dedupe_target_scopes,
    _split_scope_groups,
)


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
