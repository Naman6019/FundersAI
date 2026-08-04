from pathlib import Path
from types import SimpleNamespace

from app.mf_ingestion.jobs import promote_mf_disclosures
from app.mf_ingestion.jobs.promote_mf_amc_disclosures import (
    _build_target_scopes,
    _compact_staging_rows,
    _dedupe_target_scopes,
    _split_scope_groups,
    assess_batch_targets,
)
from app.mf_ingestion.jobs.promote_mf_disclosures import (
    MIN_PORTFOLIO_FAMILY_COVERAGE,
    _internal_family_conflicts,
    _parse_candidate_ids,
    _portfolio_family_coverage,
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


def test_candidate_allowlist_requires_valid_unique_uuids() -> None:
    first = "ad4ac081-eb76-4147-9004-e3da10133d07"
    second = "02bc8db4-6a67-4728-a04d-82297e40938c"

    assert _parse_candidate_ids(f"{first},{second},{first}") == {first, second}
    assert _parse_candidate_ids("") is None


def test_internal_family_conflicts_reject_disagreeing_official_values() -> None:
    conflicts = _internal_family_conflicts(
        [
            {
                "mapped_family_id": "family-a",
                "benchmark": "MSCI World Index",
                "risk_level": "Very High",
            },
            {
                "mapped_family_id": "family-a",
                "benchmark": "Nasdaq 100 TRI",
                "risk_level": " very  high ",
            },
        ],
        ["benchmark", "risk"],
    )

    assert conflicts == {
        "family-a": {"benchmark": ["MSCI World Index", "Nasdaq 100 TRI"]}
    }


def _holding_row(index: int, *, valid: bool) -> dict:
    return {
        "mapped_scheme_code": str(100000 + index),
        "mapped_family_id": f"family-{index}",
        "mapping_status": "mapped",
        "mapping_confidence": 100,
        "report_month": "2026-06-01",
        "raw_scheme_name": f"Fund {index}",
        "validation_status": "valid" if valid else "needs_review",
        "isin": f"INE{index:08d}0",
        "sector": "Banks",
    }


def test_portfolio_family_gate_accepts_exactly_eighty_percent_valid_families() -> None:
    rows = [_holding_row(index, valid=index < 8) for index in range(10)]
    mapping = {
        row["mapped_scheme_code"]: row["mapped_family_id"]
        for row in rows
    }

    coverage = _portfolio_family_coverage(
        rows,
        mapping,
        {"report_month": "2026-06-01"},
    )

    assert coverage["mapping_percentage"] == 100.0
    assert coverage["validation_percentage"] == MIN_PORTFOLIO_FAMILY_COVERAGE


def test_portfolio_family_gate_rejects_below_eighty_percent_valid_families() -> None:
    rows = [_holding_row(index, valid=index < 7) for index in range(10)]
    mapping = {
        row["mapped_scheme_code"]: row["mapped_family_id"]
        for row in rows
    }

    coverage = _portfolio_family_coverage(
        rows,
        mapping,
        {"report_month": "2026-06-01"},
    )

    assert coverage["mapping_percentage"] == 100.0
    assert coverage["validation_percentage"] == 70.0


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
        "equity-portfolio": ["holdings", "sectors"],
    }


def test_amc_batch_promotion_keeps_broader_workbook_sectors_with_direct_allocations() -> None:
    targets = _build_target_scopes(
        amc="motilal",
        requested_scopes=["sectors"],
        candidates=[],
        holdings=[
            {
                "amc_code": "MOTILAL",
                "source_document_id": "portfolio-workbook",
                "sector": "Banks",
            }
        ],
        sector_allocations=[
            {
                "amc_code": "MOTILAL",
                "source_document_id": "combined-factsheet",
                "sector_name": "Financial Services",
            }
        ],
    )

    assert targets == {
        "combined-factsheet": ["sectors"],
        "portfolio-workbook": ["sectors"],
    }


def test_amc_batch_compacts_only_selected_source_documents() -> None:
    rows = [
        {
            "source_document_id": "nippon-doc",
            "report_month": "2026-06-01",
            "raw_scheme_name": "Nippon India Growth Fund",
            "mapped_scheme_code": "118668",
            "mapped_family_id": "nippon-growth",
            "mapping_status": "mapped",
            "mapping_confidence": 100,
            "validation_status": "valid",
            "sector": None,
        },
        {
            "source_document_id": "nippon-doc",
            "report_month": "2026-06-01",
            "raw_scheme_name": "Nippon India Growth Fund",
            "mapped_scheme_code": "118668",
            "mapped_family_id": "nippon-growth",
            "mapping_status": "mapped",
            "mapping_confidence": 100,
            "validation_status": "valid",
            "sector": "Banks",
        },
        {
            "source_document_id": "other-doc",
            "report_month": "2026-06-01",
            "raw_scheme_name": "Other Fund",
            "sector": "Finance",
        },
    ]

    compact = _compact_staging_rows(
        rows,
        amc_by_document_id={"nippon-doc": "NIPPON"},
        value_column="sector",
    )

    assert compact == [
        {
            "source_document_id": "nippon-doc",
            "report_month": "2026-06-01",
            "raw_scheme_name": "Nippon India Growth Fund",
            "mapped_scheme_code": "118668",
            "mapped_family_id": "nippon-growth",
            "mapping_status": "mapped",
            "mapping_confidence": 100,
            "validation_status": "valid",
            "amc_code": "NIPPON",
            "sector": "__present__",
        }
    ]


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


def test_amc_batch_promotion_prefers_dedicated_portfolio_over_combined_factsheet() -> None:
    targets = {
        "combined-factsheet": ["risk", "holdings", "sectors"],
        "dedicated-portfolio": ["holdings", "sectors"],
    }
    documents = [
        {
            "id": "combined-factsheet",
            "document_type": "factsheet",
            "checksum": "factsheet-checksum",
            "source_url": "https://official.example/factsheet.pdf",
            "parsed_at": "2026-07-20T00:00:00+00:00",
        },
        {
            "id": "dedicated-portfolio",
            "document_type": "portfolio_disclosure",
            "checksum": "portfolio-checksum",
            "source_url": "https://official.example/portfolio.xlsx",
            "parsed_at": "2026-07-15T00:00:00+00:00",
        },
    ]

    assert _dedupe_target_scopes(
        targets,
        documents,
        ["risk", "holdings", "sectors"],
    ) == {
        "combined-factsheet": ["risk"],
        "dedicated-portfolio": ["holdings", "sectors"],
    }


def test_amc_batch_promotion_prefers_workbook_when_factsheet_is_misclassified() -> None:
    targets = {
        "misclassified-factsheet": ["holdings", "sectors"],
        "portfolio-workbook": ["holdings", "sectors"],
    }
    documents = [
        {
            "id": "misclassified-factsheet",
            "document_type": "portfolio_disclosure",
            "checksum": "factsheet-checksum",
            "source_url": "https://official.example/factsheet.pdf",
            "parsed_at": "2026-07-20T00:00:00+00:00",
        },
        {
            "id": "portfolio-workbook",
            "document_type": "portfolio_disclosure",
            "checksum": "portfolio-checksum",
            "source_url": "https://official.example/portfolio.xlsx?download=1",
            "parsed_at": "2026-07-15T00:00:00+00:00",
        },
    ]

    assert _dedupe_target_scopes(
        targets,
        documents,
        ["holdings", "sectors"],
    ) == {"portfolio-workbook": ["holdings", "sectors"]}


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


def _portfolio_target(
    index: int,
    *,
    status: str,
    scope: str = "holdings",
    issues: list[str] | None = None,
    isin_ready: bool = True,
) -> dict:
    coverage_key = (
        "holdings_family_coverage"
        if scope == "holdings"
        else "sector_family_coverage"
    )
    family_id = f"family-{index}"
    coverage = {
        "observed_keys": [f"family:{family_id}"],
        "mapped_family_ids": [family_id],
        "promotable_family_ids": [family_id],
        "isin_family_ids": [family_id] if isin_ready and scope == "holdings" else [],
    }
    if scope == "sectors":
        coverage["applicable_family_ids"] = [family_id]
    return {
        "source_document_id": f"source-{index}",
        "scopes": [scope],
        "status": status,
        "issues": issues or [],
        "warnings": [],
        "report": {coverage_key: coverage},
    }


def test_amc_batch_quarantines_review_sources_when_post_apply_coverage_passes() -> None:
    reports = [
        *[_portfolio_target(index, status="promotable") for index in range(8)],
        *[
            _portfolio_target(
                index,
                status="rejected",
                issues=[
                    "staged_holdings_below_family_coverage_threshold",
                    "staged_holdings_have_no_promotable_rows",
                ],
            )
            for index in range(8, 10)
        ],
    ]

    gate = assess_batch_targets(reports, ["holdings"])

    assert gate["status"] == "promotable"
    assert gate["quarantined_target_count"] == 2
    assert gate["unsafe_rejected_target_count"] == 0
    assert (
        gate["coverage"]["holdings"]["post_apply_family_coverage_percentage"]
        == 80.0
    )


def test_amc_batch_rejects_when_post_apply_coverage_is_below_eighty_percent() -> None:
    reports = [
        *[_portfolio_target(index, status="promotable") for index in range(7)],
        *[
            _portfolio_target(
                index,
                status="rejected",
                issues=["staged_holdings_below_family_coverage_threshold"],
            )
            for index in range(7, 10)
        ],
    ]

    gate = assess_batch_targets(reports, ["holdings"])

    assert gate["status"] == "rejected"
    assert gate["issues"] == ["holdings_batch_family_coverage_below_80"]


def test_amc_batch_rejects_holdings_without_overlap_ready_isins() -> None:
    reports = [
        _portfolio_target(
            index,
            status="promotable",
            isin_ready=index < 7,
        )
        for index in range(10)
    ]

    gate = assess_batch_targets(reports, ["holdings"])

    assert gate["status"] == "rejected"
    assert gate["coverage"]["holdings"][
        "post_apply_isin_family_coverage_percentage"
    ] == 70.0
    assert gate["issues"] == ["holding_isin_batch_family_coverage_below_80"]


def test_amc_batch_never_quarantines_source_integrity_rejections() -> None:
    reports = [
        _portfolio_target(0, status="promotable"),
        _portfolio_target(
            1,
            status="rejected",
            issues=["source_report_month_mismatch"],
        ),
    ]

    gate = assess_batch_targets(reports, ["holdings"])

    assert gate["status"] == "rejected"
    assert gate["quarantined_target_count"] == 0
    assert gate["unsafe_rejected_target_count"] == 1
    assert "one_or_more_unsafe_promotion_targets_rejected" in gate["issues"]


def test_amc_batch_requires_eighty_percent_core_field_coverage() -> None:
    candidates = [
        {
            "candidate_id": f"candidate-{index}",
            "raw_scheme_name": f"Fund {index}",
            "mapped_scheme_code": str(100000 + index),
            "mapped_family_id": f"family-{index}",
            "eligible_scopes": ["risk"] if index < 7 else [],
            "unavailable_scopes": [] if index < 7 else ["risk"],
            "issues": [],
        }
        for index in range(10)
    ]
    reports = [
        {
            "source_document_id": "factsheet",
            "scopes": ["risk"],
            "status": "promotable",
            "issues": [],
            "warnings": [],
            "report": {"candidate_reports": candidates},
        }
    ]

    gate = assess_batch_targets(reports, ["risk"])

    assert gate["status"] == "rejected"
    assert gate["coverage"]["core"]["field_percentages"]["risk"] == 70.0
    assert gate["issues"] == ["risk_batch_family_coverage_below_80"]


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
    assert "mf_staging_holding_coverage_rows" not in job
    assert "source_document_ids[offset : offset + batch_size]" in job
    assert "Revalidate every target immediately before the first mutation." in job


def test_single_document_workflow_supports_a_core_candidate_allowlist() -> None:
    root = Path(__file__).resolve().parents[2]
    workflow = (
        root / ".github" / "workflows" / "promote-mf-disclosures.yml"
    ).read_text(encoding="utf-8")

    assert "candidate_ids:" in workflow
    assert 'args+=(--candidate-ids "$CANDIDATE_IDS")' in workflow
    assert "environment: production-data" in workflow


def test_thresholded_portfolio_promotion_is_indexed_and_valid_only() -> None:
    root = Path(__file__).resolve().parents[2]
    migration = (
        root
        / "backend"
        / "migrations"
        / "20260728_add_mf_thresholded_portfolio_promotion_v2.sql"
    ).read_text(encoding="utf-8")
    job = (
        root
        / "backend"
        / "app"
        / "mf_ingestion"
        / "jobs"
        / "promote_mf_disclosures.py"
    ).read_text(encoding="utf-8")

    assert "mf_scheme_holdings (source_document_id, id)" in migration
    assert "mf_scheme_sector_allocations (source_document_id, id)" in migration
    assert "promote_mf_holdings_document_v2" in migration
    assert "staged_holdings_below_family_coverage_threshold" in migration
    assert "staged_sectors_below_family_coverage_threshold" in migration
    assert "staged_holdings_contain_non_promotable_rows" not in migration
    assert "h.validation_status = 'valid'" in migration
    assert "a.validation_status = 'valid'" in migration
    assert "to service_role" in migration
    assert '"promote_mf_holdings_document_v2"' in job
