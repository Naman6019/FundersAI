from __future__ import annotations

from scripts import check_mf_disclosure_coverage


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
                }
            ],
            "mutual_fund_holdings": [{"family_id": "axis-midcap"}],
            "mutual_fund_sectors": [{"family_id": "axis-midcap"}],
        }
    )
    monkeypatch.setattr(check_mf_disclosure_coverage, "supabase", fake_supabase)
    monkeypatch.setenv("MF_DISCLOSURE_COVERAGE_AMCS", "axis")

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
