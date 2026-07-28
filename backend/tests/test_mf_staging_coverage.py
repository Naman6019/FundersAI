from __future__ import annotations

from pathlib import Path

from scripts.report_mf_staging_coverage import build_staging_coverage


def test_staging_coverage_rpc_is_read_only_and_service_role_only():
    root = Path(__file__).resolve().parents[2]
    sql = (
        root / "backend" / "migrations" / "20260728_add_mf_staging_coverage_rpc.sql"
    ).read_text(encoding="utf-8")

    assert "language sql" in sql
    assert "stable" in sql
    assert "security definer" in sql
    assert "grant execute" in sql
    assert "to service_role" in sql
    assert "insert " not in sql.lower()
    assert "update " not in sql.lower()
    assert "delete " not in sql.lower()


def test_promotion_eligible_coverage_rpc_is_read_only_and_exposes_gate_fields():
    root = Path(__file__).resolve().parents[2]
    sql = (
        root
        / "backend"
        / "migrations"
        / "20260728_add_mf_promotion_eligible_coverage_rpc.sql"
    ).read_text(encoding="utf-8")

    assert sql.count("language sql") == 2
    assert sql.count("stable") == 2
    assert sql.count("security definer") == 2
    assert sql.count("to service_role") == 2
    assert "mapping_confidence numeric" in sql
    assert "validation_status text" in sql
    assert "insert " not in sql.lower()
    assert "update " not in sql.lower()
    assert "delete " not in sql.lower()


def test_staging_coverage_uses_distinct_current_mapped_families():
    report = build_staging_coverage(
        report_month="2026-06-01",
        amcs=["mirae"],
        candidates=[
            {
                "source_document_id": "mirae-core",
                "amc_code": "mirae",
                "report_month": "2026-06-01",
                "normalized_scheme_name": "mirae asset one fund",
                "mapped_family_id": "one",
                "mapped_scheme_code": "1001",
                "mapping_confidence": 100.0,
                "mapping_status": "mapped",
                "promotion_status": "staged",
                "aum": 1,
                "expense_ratio": 1,
                "benchmark": "Index",
                "fund_manager": "Manager",
                "risk_level": "High",
            },
            {
                "source_document_id": "mirae-core",
                "amc_code": "mirae",
                "report_month": "2026-06-01",
                "normalized_scheme_name": "mirae asset two fund",
                "mapped_family_id": None,
                "mapping_status": "unmapped",
            },
        ],
        holdings=[
            {
                "source_document_id": "mirae-portfolio",
                "amc_code": "mirae",
                "report_month": "2026-06-01",
                "raw_scheme_name": "Mirae Asset One Fund",
                "mapped_family_id": "one",
                "mapped_scheme_code": "1001",
                "mapping_confidence": 100.0,
                "mapping_status": "mapped",
                "validation_status": "valid",
                "sector": "Banks",
            },
            {
                "source_document_id": "mirae-portfolio",
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
    assert report["core_source_document_ids"] == ["mirae-core"]
    assert report["portfolio_source_document_ids"] == ["mirae-portfolio"]
    assert report["passes_all_fields"] is False


def test_staging_coverage_separates_non_applicable_sectors_from_missing_sectors():
    candidates = [
        {
            "amc_code": "mirae",
            "report_month": "2026-06-01",
            "normalized_scheme_name": name.lower(),
            "mapped_family_id": family,
            "mapped_scheme_code": f"code-{family}",
            "mapping_confidence": 100.0,
            "mapping_status": "mapped",
            "promotion_status": "staged",
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
            "mapped_scheme_code": "code-equity",
            "mapping_confidence": 100.0,
            "mapping_status": "mapped",
            "validation_status": "valid",
            "sector": None,
        },
        {
            "amc_code": "mirae",
            "report_month": "2026-06-01",
            "raw_scheme_name": "Mirae Asset Gold ETF Fund of Fund",
            "mapped_family_id": "gold-fof",
            "mapped_scheme_code": "code-gold-fof",
            "mapping_confidence": 100.0,
            "mapping_status": "mapped",
            "validation_status": "valid",
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
        "mapped_scheme_code": "1001",
        "mapping_confidence": 100.0,
        "mapping_status": "mapped",
        "promotion_status": "staged",
        "validation_status": "valid",
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
        "mapped_scheme_code": "1001",
        "mapping_confidence": 100.0,
        "mapping_status": "mapped",
        "promotion_status": "staged",
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
        "mapped_scheme_code": "1001",
        "mapping_confidence": 100.0,
        "mapping_status": "mapped",
        "validation_status": "valid",
        "sector": None,
    }
    sector = {
        "amc_code": "motilal",
        "report_month": "2026-06-01",
        "raw_scheme_name": "Motilal Oswal Midcap Fund",
        "mapped_family_id": "motilal-midcap",
        "mapped_scheme_code": "1001",
        "mapping_confidence": 100.0,
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


def test_staging_coverage_excludes_holdings_that_are_not_promotion_eligible():
    candidate = {
        "amc_code": "mirae",
        "report_month": "2026-06-01",
        "normalized_scheme_name": "mirae asset equity fund",
        "mapped_family_id": "equity",
        "mapped_scheme_code": "1001",
        "mapping_confidence": 100.0,
        "mapping_status": "mapped",
        "promotion_status": "staged",
        "aum": 1,
        "expense_ratio": 1,
        "benchmark": "Index",
        "fund_manager": "Manager",
        "risk_level": "High",
    }
    holding = {
        "amc_code": "mirae",
        "report_month": "2026-06-01",
        "raw_scheme_name": "Mirae Asset Equity Fund",
        "mapped_family_id": "equity",
        "mapped_scheme_code": "1001",
        "mapping_confidence": 100.0,
        "mapping_status": "mapped",
        "validation_status": "needs_review",
        "sector": "Banks",
    }

    report = build_staging_coverage(
        report_month="2026-06-01",
        amcs=["mirae"],
        candidates=[candidate],
        holdings=[holding],
        threshold=80.0,
    )["mirae"]

    assert report["mapping_percentages"]["portfolio"] == 100.0
    assert report["percentages"]["holdings"] == 0.0
    assert report["percentages"]["sectors"] == 0.0
    assert report["passes_all_fields"] is False
