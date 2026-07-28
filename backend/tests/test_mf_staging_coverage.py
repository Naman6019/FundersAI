from __future__ import annotations

from scripts.report_mf_staging_coverage import build_staging_coverage


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
