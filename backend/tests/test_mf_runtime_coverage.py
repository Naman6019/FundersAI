from __future__ import annotations

from scripts.report_mf_runtime_coverage import build_runtime_coverage


def _fixture_rows(runtime_family_count: int) -> dict:
    candidates = []
    staged_holdings = []
    snapshots = []
    runtime_holdings = []
    runtime_sectors = []
    for index in range(10):
        scheme_code = str(100000 + index)
        family_id = f"hdfc-family-{index}"
        candidates.append(
            {
                "amc_code": "HDFC",
                "report_month": "2026-06-01",
                "mapped_scheme_code": scheme_code,
                "mapped_family_id": family_id,
                "mapping_status": "mapped",
                "mapping_confidence": 100,
                "promotion_status": "promoted",
                "promoted_scopes": [
                    "risk",
                    "ter_aum",
                    "benchmark",
                    "manager",
                ],
            }
        )
        staged_holdings.append(
            {
                "amc_code": "HDFC",
                "report_month": "2026-06-01",
                "raw_scheme_name": f"HDFC Equity Fund {index}",
                "mapped_scheme_code": scheme_code,
                "mapped_family_id": family_id,
                "mapping_status": "mapped",
                "mapping_confidence": 100,
                "validation_status": "valid",
                "sector": "Banks",
            }
        )
        snapshots.append(
            {
                "scheme_code": scheme_code,
                "risk_level": "High",
                "expense_ratio": 0.5,
                "aum": 1000,
                "benchmark": "Nifty 500 TRI",
                "fund_manager": "Manager",
            }
        )
        if index < runtime_family_count:
            runtime_holdings.append(
                {
                    "scheme_code": scheme_code,
                    "family_id": family_id,
                    "as_of_date": "2026-06-01",
                    "source": "amc_disclosure",
                    "provider_payload": {},
                }
            )
            runtime_sectors.append(
                {
                    "scheme_code": scheme_code,
                    "family_id": family_id,
                    "source": "amc_disclosure",
                    "provider_payload": {"report_month": "2026-06-01"},
                }
            )
    return {
        "candidates": candidates,
        "staged_holdings": staged_holdings,
        "staged_sectors": [],
        "snapshots": snapshots,
        "runtime_holdings": runtime_holdings,
        "runtime_sectors": runtime_sectors,
    }


def test_runtime_coverage_passes_at_exactly_eighty_percent():
    report = build_runtime_coverage(
        report_month="2026-06-01",
        amcs=["hdfc"],
        threshold=80.0,
        **_fixture_rows(runtime_family_count=8),
    )["hdfc"]

    assert report["percentages"] == {
        "risk": 100.0,
        "ter_aum": 100.0,
        "benchmark": 100.0,
        "manager": 100.0,
        "holdings": 80.0,
        "sectors": 80.0,
    }
    assert report["passes_all_fields"] is True


def test_runtime_coverage_rejects_missing_promoted_families():
    report = build_runtime_coverage(
        report_month="2026-06-01",
        amcs=["hdfc"],
        threshold=80.0,
        **_fixture_rows(runtime_family_count=7),
    )["hdfc"]

    assert report["percentages"]["holdings"] == 70.0
    assert report["percentages"]["sectors"] == 70.0
    assert report["passes_all_fields"] is False


def test_runtime_coverage_ignores_stale_or_non_official_rows():
    fixture = _fixture_rows(runtime_family_count=8)
    fixture["runtime_holdings"].extend(
        [
            {
                "scheme_code": "100008",
                "family_id": "hdfc-family-8",
                "as_of_date": "2026-05-01",
                "source": "amc_disclosure",
                "provider_payload": {},
            },
            {
                "scheme_code": "100009",
                "family_id": "hdfc-family-9",
                "as_of_date": "2026-06-01",
                "source": "provider_api",
                "provider_payload": {},
            },
        ]
    )
    fixture["runtime_sectors"].append(
        {
            "scheme_code": "100008",
            "family_id": "hdfc-family-8",
            "source": "amc_disclosure",
            "provider_payload": {"report_month": "2026-05-01"},
        }
    )

    report = build_runtime_coverage(
        report_month="2026-06-01",
        amcs=["hdfc"],
        threshold=80.0,
        **fixture,
    )["hdfc"]

    assert report["percentages"]["holdings"] == 80.0
    assert report["percentages"]["sectors"] == 80.0
