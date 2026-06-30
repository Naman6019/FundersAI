from __future__ import annotations

from scripts import check_mf_disclosure_coverage, report_mf_disclosure_diagnostics


class _FakeResponse:
    def __init__(self, data):
        self.data = data


class _FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.start = 0
        self.end = len(rows) - 1

    def select(self, _columns):
        return self

    def range(self, start, end):
        self.start = start
        self.end = end
        return self

    def execute(self):
        return _FakeResponse(self.rows[self.start : self.end + 1])


class _FakeSupabase:
    def __init__(self, tables):
        self.tables = tables

    def table(self, name):
        return _FakeQuery(self.tables.get(name, []))


def test_disclosure_coverage_passes_when_supported_amc_has_required_data(monkeypatch):
    fake_supabase = _FakeSupabase(
        {
            "mutual_fund_family_mapping": [{"scheme_code": "101", "family_id": "axis-midcap"}],
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "101",
                    "scheme_name": "Axis Midcap Fund - Direct Plan - Growth",
                    "amc_name": "Axis Mutual Fund",
                    "aum": 30205.58,
                    "expense_ratio": 0.54,
                    "benchmark": "BSE Midcap 150 TRI",
                    "fund_manager": "Test Manager",
                    "risk_level": "Very High",
                }
            ],
            "mutual_fund_holdings": [{"family_id": "axis-midcap"}],
            "mutual_fund_sectors": [{"family_id": "axis-midcap"}],
        }
    )
    monkeypatch.setattr(check_mf_disclosure_coverage, "supabase", fake_supabase)
    monkeypatch.setenv("MF_DISCLOSURE_COVERAGE_AMCS", "axis")

    assert check_mf_disclosure_coverage.check_disclosure_coverage() == 0


def test_strict_coverage_amcs_override_reporting_amcs(monkeypatch):
    fake_supabase = _FakeSupabase(
        {
            "mutual_fund_family_mapping": [{"scheme_code": "101", "family_id": "axis-midcap"}],
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "101",
                    "scheme_name": "Axis Midcap Fund - Direct Plan - Growth",
                    "amc_name": "Axis Mutual Fund",
                    "aum": 30205.58,
                    "expense_ratio": 0.54,
                    "benchmark": "BSE Midcap 150 TRI",
                    "fund_manager": "Test Manager",
                    "risk_level": "Very High",
                }
            ],
            "mutual_fund_holdings": [{"family_id": "axis-midcap"}],
            "mutual_fund_sectors": [{"family_id": "axis-midcap"}],
        }
    )
    monkeypatch.setattr(check_mf_disclosure_coverage, "supabase", fake_supabase)
    monkeypatch.setenv("MF_DISCLOSURE_COVERAGE_AMCS", "nippon")
    monkeypatch.setenv("MF_DISCLOSURE_STRICT_COVERAGE_AMCS", "axis")

    assert check_mf_disclosure_coverage.check_disclosure_coverage() == 0


def test_disclosure_coverage_matches_nippon_supported_amc(monkeypatch):
    fake_supabase = _FakeSupabase(
        {
            "mutual_fund_family_mapping": [{"scheme_code": "119332", "family_id": "nippon-small"}],
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "119332",
                    "scheme_name": "Nippon India Small Cap Fund - Direct Plan - Growth",
                    "amc_name": "Nippon India Mutual Fund",
                    "aum": 59456.65,
                    "expense_ratio": 0.67,
                    "benchmark": "Nifty Smallcap 250 TRI",
                    "fund_manager": "Mr. Samir Rachh",
                    "risk_level": "Very High",
                }
            ],
            "mutual_fund_holdings": [{"family_id": "nippon-small"}],
            "mutual_fund_sectors": [{"family_id": "nippon-small"}],
        }
    )
    monkeypatch.setattr(check_mf_disclosure_coverage, "supabase", fake_supabase)
    monkeypatch.setenv("MF_DISCLOSURE_COVERAGE_AMCS", "nippon")

    assert check_mf_disclosure_coverage.check_disclosure_coverage() == 0


def test_disclosure_coverage_fails_when_benchmark_or_holdings_are_missing(monkeypatch):
    fake_supabase = _FakeSupabase(
        {
            "mutual_fund_family_mapping": [{"scheme_code": "101", "family_id": "axis-midcap"}],
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "101",
                    "scheme_name": "Axis Midcap Fund - Direct Plan - Growth",
                    "amc_name": "Axis Mutual Fund",
                    "aum": 30205.58,
                    "expense_ratio": 0.54,
                    "benchmark": None,
                }
            ],
            "mutual_fund_holdings": [],
            "mutual_fund_sectors": [],
        }
    )
    monkeypatch.setattr(check_mf_disclosure_coverage, "supabase", fake_supabase)
    monkeypatch.setenv("MF_DISCLOSURE_COVERAGE_AMCS", "axis")

    assert check_mf_disclosure_coverage.check_disclosure_coverage() == 1


def test_disclosure_coverage_fails_when_fund_manager_is_missing(monkeypatch):
    fake_supabase = _FakeSupabase(
        {
            "mutual_fund_family_mapping": [{"scheme_code": "101", "family_id": "axis-midcap"}],
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "101",
                    "scheme_name": "Axis Midcap Fund - Direct Plan - Growth",
                    "amc_name": "Axis Mutual Fund",
                    "aum": 30205.58,
                    "expense_ratio": 0.54,
                    "benchmark": "BSE Midcap 150 TRI",
                    "fund_manager": None,
                    "risk_level": "Very High",
                }
            ],
            "mutual_fund_holdings": [{"family_id": "axis-midcap"}],
            "mutual_fund_sectors": [{"family_id": "axis-midcap"}],
        }
    )
    monkeypatch.setattr(check_mf_disclosure_coverage, "supabase", fake_supabase)
    monkeypatch.setenv("MF_DISCLOSURE_COVERAGE_AMCS", "axis")

    assert check_mf_disclosure_coverage.check_disclosure_coverage() == 1


def test_disclosure_coverage_fails_when_risk_level_is_missing(monkeypatch):
    fake_supabase = _FakeSupabase(
        {
            "mutual_fund_family_mapping": [{"scheme_code": "101", "family_id": "axis-midcap"}],
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "101",
                    "scheme_name": "Axis Midcap Fund - Direct Plan - Growth",
                    "amc_name": "Axis Mutual Fund",
                    "aum": 30205.58,
                    "expense_ratio": 0.54,
                    "benchmark": "BSE Midcap 150 TRI",
                    "fund_manager": "Test Manager",
                    "risk_level": None,
                }
            ],
            "mutual_fund_holdings": [{"family_id": "axis-midcap"}],
            "mutual_fund_sectors": [{"family_id": "axis-midcap"}],
        }
    )
    monkeypatch.setattr(check_mf_disclosure_coverage, "supabase", fake_supabase)
    monkeypatch.setenv("MF_DISCLOSURE_COVERAGE_AMCS", "axis")

    assert check_mf_disclosure_coverage.check_disclosure_coverage() == 1


def test_disclosure_coverage_fails_when_configured_amc_has_no_snapshot_rows(monkeypatch):
    fake_supabase = _FakeSupabase(
        {
            "mutual_fund_family_mapping": [],
            "mutual_fund_core_snapshot": [],
            "mutual_fund_holdings": [],
            "mutual_fund_sectors": [],
        }
    )
    monkeypatch.setattr(check_mf_disclosure_coverage, "supabase", fake_supabase)
    monkeypatch.setenv("MF_DISCLOSURE_COVERAGE_AMCS", "motilal")

    assert check_mf_disclosure_coverage.check_disclosure_coverage() == 1


def test_empty_strict_coverage_amcs_reports_without_failing(monkeypatch):
    fake_supabase = _FakeSupabase(
        {
            "mutual_fund_family_mapping": [{"scheme_code": "101", "family_id": "axis-midcap"}],
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "101",
                    "scheme_name": "Axis Midcap Fund - Direct Plan - Growth",
                    "amc_name": "Axis Mutual Fund",
                    "aum": 30205.58,
                    "expense_ratio": 0.54,
                    "benchmark": None,
                }
            ],
            "mutual_fund_holdings": [],
            "mutual_fund_sectors": [],
        }
    )
    monkeypatch.setattr(check_mf_disclosure_coverage, "supabase", fake_supabase)
    monkeypatch.setenv("MF_DISCLOSURE_COVERAGE_AMCS", "axis")
    monkeypatch.setenv("MF_DISCLOSURE_STRICT_COVERAGE_AMCS", "")

    assert check_mf_disclosure_coverage.check_disclosure_coverage() == 0


def test_disclosure_diagnostics_reports_document_review_and_family_gaps(monkeypatch):
    fake_supabase = _FakeSupabase(
        {
            "mf_raw_documents": [
                {
                    "id": "doc-sbi-1",
                    "amc_code": "sbi",
                    "document_type": "portfolio_disclosure",
                    "parse_status": "parsed_partial",
                    "validation_issues": ["percent_aum_out_of_band"],
                },
                {
                    "id": "doc-sbi-2",
                    "amc_code": "sbi",
                    "document_type": "factsheet",
                    "parse_status": "parsed",
                    "validation_issues": [],
                },
            ],
            "mf_parse_review_queue": [
                {
                    "source_document_id": "doc-sbi-1",
                    "amc_code": "sbi",
                    "validation_issues": ["holdings_not_found_in_document"],
                }
            ],
            "mf_schemes": [{"id": "scheme-1", "amc_code": "sbi", "scheme_name": "SBI First Fund"}],
            "mf_scheme_holdings": [{"scheme_id": "scheme-1"}],
            "mutual_fund_family_mapping": [{"scheme_code": "101", "family_id": "sbi-first"}],
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "101",
                    "scheme_name": "SBI First Fund",
                    "amc_name": "SBI Mutual Fund",
                    "aum": 1000.0,
                    "expense_ratio": 0.8,
                    "benchmark": "Nifty 500 TRI",
                    "fund_manager": "Test Manager",
                    "risk_level": "Very High",
                }
            ],
            "mutual_fund_holdings": [{"scheme_code": "101", "family_id": "sbi-first"}],
            "mutual_fund_sectors": [],
        }
    )
    monkeypatch.setattr(report_mf_disclosure_diagnostics, "supabase", fake_supabase)

    report = report_mf_disclosure_diagnostics.build_diagnostics(["sbi"])
    sbi = report["amcs"]["sbi"]

    assert sbi["documents_by_status"] == {"parsed": 1, "parsed_partial": 1}
    assert sbi["documents_by_type_status"]["portfolio_disclosure"]["parsed_partial"] == 1
    assert sbi["review_issue_counts"]["holdings_not_found_in_document"] == 1
    assert sbi["review_issue_counts"]["percent_aum_out_of_band"] == 1
    assert sbi["parser_scheme_holdings_count"] == 1
    assert sbi["snapshot_family_count"] == 1
    assert sbi["aum_family_count"] == 1
    assert sbi["expense_ratio_family_count"] == 1
    assert sbi["benchmark_family_count"] == 1
    assert sbi["fund_manager_family_count"] == 1
    assert sbi["risk_level_family_count"] == 1
    assert sbi["final_holding_family_count"] == 1
    assert sbi["final_sector_family_count"] == 0
    assert sbi["missing_final_sector_family_count"] == 1
