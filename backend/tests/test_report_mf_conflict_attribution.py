from __future__ import annotations

from scripts import report_mf_conflict_attribution as report_module
from scripts.report_mf_conflict_attribution import (
    _categorize_holdings_conflict,
    build_conflict_attribution,
)


def test_categorize_out_of_band_total():
    row = {
        "total_percent_aum": 83.0,
        "validation_statuses": ["valid"],
        "holding_rows_missing_isin": 0,
        "also_staged_in_n_other_documents": 0,
    }
    result = _categorize_holdings_conflict(row, 90.0, 110.0)
    assert result == {"causes": ["out_of_band_total"], "tags": []}


def test_categorize_no_percent_aum_value():
    row = {
        "total_percent_aum": None,
        "validation_statuses": ["review"],
        "holding_rows_missing_isin": 0,
        "also_staged_in_n_other_documents": 0,
    }
    result = _categorize_holdings_conflict(row, 90.0, 110.0)
    assert "no_percent_aum_value" in result["causes"]
    assert "non_valid_status" in result["causes"]


def test_categorize_captures_missing_isin_and_duplicate_tags_without_hiding_cause():
    row = {
        "total_percent_aum": 95.0,
        "validation_statuses": ["review"],
        "holding_rows_missing_isin": 3,
        "also_staged_in_n_other_documents": 1,
    }
    result = _categorize_holdings_conflict(row, 90.0, 110.0)
    assert result["causes"] == ["non_valid_status"]
    assert set(result["tags"]) == {"missing_isin", "duplicate_across_documents"}


def test_categorize_in_band_valid_row_still_gets_a_cause_since_it_was_flagged():
    # find_holdings_out_of_band only ever returns rows it flagged for some reason;
    # this guards against a row silently falling through with an empty cause list
    # if the caller passes something that looks clean by these three fields alone.
    row = {
        "total_percent_aum": 100.0,
        "validation_statuses": ["valid"],
        "holding_rows_missing_isin": 0,
        "also_staged_in_n_other_documents": 0,
    }
    result = _categorize_holdings_conflict(row, 90.0, 110.0)
    assert result["causes"] == ["non_valid_status"]


def test_build_conflict_attribution_ranks_amcs_by_total_and_groups_causes(monkeypatch):
    def fake_risk_conflicts(*, amc, report_month, min_confidence):
        if amc == "kotak":
            return [{"raw_scheme_name": "Kotak Bond Fund", "staged_scheme_code": "K1"}]
        return []

    def fake_holdings_out_of_band(*, amc, report_month):
        if amc == "kotak":
            return [
                {
                    "raw_scheme_name": "Kotak Bond Short Term Fund",
                    "scheme_key": "K2",
                    "total_percent_aum": 83.0,
                    "validation_statuses": ["valid"],
                    "holding_rows_missing_isin": 0,
                    "also_staged_in_n_other_documents": 1,
                },
                {
                    "raw_scheme_name": "Kotak Equity Fund",
                    "scheme_key": "K3",
                    "total_percent_aum": None,
                    "validation_statuses": ["invalid"],
                    "holding_rows_missing_isin": 2,
                    "also_staged_in_n_other_documents": 0,
                },
            ]
        if amc == "hdfc":
            return [
                {
                    "raw_scheme_name": "HDFC Flexi Cap Fund",
                    "scheme_key": "H1",
                    "total_percent_aum": 99.0,
                    "validation_statuses": ["review"],
                    "holding_rows_missing_isin": 1,
                    "also_staged_in_n_other_documents": 0,
                }
            ]
        return []

    monkeypatch.setattr(report_module, "find_risk_conflicts", fake_risk_conflicts)
    monkeypatch.setattr(report_module, "find_holdings_out_of_band", fake_holdings_out_of_band)

    report = build_conflict_attribution(
        amcs=["kotak", "hdfc", "sbi"], report_months=["2026-06-01"]
    )

    assert report["ranked_amcs"] == ["kotak", "hdfc", "sbi"]
    kotak = report["amcs"]["kotak"]
    assert kotak["total_conflicts"] == 3
    assert kotak["by_cause"]["risk_mismatch"] == 1
    assert kotak["by_cause"]["holdings_out_of_band_total"] == 1
    assert kotak["by_cause"]["holdings_no_percent_aum_value"] == 1
    assert kotak["by_cause"]["holdings_non_valid_status"] == 1
    assert kotak["contributing_tags"]["holdings_missing_isin"] == 1
    assert kotak["contributing_tags"]["holdings_duplicate_across_documents"] == 1
    assert report["amcs"]["sbi"]["total_conflicts"] == 0
