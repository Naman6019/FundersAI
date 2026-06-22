from __future__ import annotations

import re
from datetime import date
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.mf_ingestion.parsers.adapters.axis_adapter import AxisAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext
from app.mf_ingestion.parsers.factsheet_parser import FactsheetParser
from app.mf_ingestion.parsers.holdings_parser import HoldingsParser
from app.mf_ingestion.services import parsing_service
from app.mf_ingestion.services.parsing_service import AMC_DISCLOSURE_SOURCE, ParsingService

AXIS_FACTSHEET = Path(__file__).resolve().parents[1] / "axis_factsheet.pdf"


def _scheme_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _axis_context() -> ParseContext:
    return ParseContext(source_document_id="axis-march-2026", source_url="", report_month=date(2026, 3, 1))


def test_axis_text_fixture_parses_percent_nav_holdings_without_pdf():
    text_fixture = """
Instrument Type/Issuer Name
Industry
% of NAV
EQUITY
100.00%
ICICI Bank Limited
Banks
8.00%
HDFC Bank Limited
Banks
7.00%
Reliance Industries Limited
Petroleum Products
10.00%
Infosys Limited
IT - Software
5.00%
Bharti Airtel Limited
Telecom - Services
5.00%
Eternal Limited
Retailing
3.00%
Bajaj Finance Limited
Finance
4.00%
Larsen & Toubro Limited
Construction
4.00%
Sun Pharmaceutical Industries Limited
Pharmaceuticals
4.00%
Sample Portfolio Holding Limited
Diversified
50.00%
Grand Total
100.00%
AXIS FLEXI CAP FUND
Fund Manager
"""

    records = AxisAdapter().parse_pdf_text_many(text_fixture, _axis_context())

    assert len(records) == 1
    record = records[0]
    assert record.scheme_name == "Axis Flexi Cap Fund"
    assert record.metrics["total_percent_aum"] == pytest.approx(100.0)
    assert record.holdings
    assert all(row.get("isin") is None for row in record.holdings)
    assert {row.get("instrument_name") for row in record.holdings}.isdisjoint({"Grand Total", "EQUITY"})


def test_axis_combined_factsheet_portfolio_snapshot_layout():
    text_fixture = """
AXIS LARGE CAP FUND
Portfolio Snapshot
March2026
Instrument Type/Issuer Name
Industry
% of NAV
EQUITY
100.00%
ICICI Bank Limited
Banks
8.84%
HDFC Bank Limited
Banks
7.71%
Reliance Industries Limited
Petroleum Products
5.08%
Infosys Limited
IT - Software
4.81%
Axis Bank Limited
Banks
1.34%
Axis NIFTY 50 ETF
Others
0.83%
Mutual Fund Units
1.23%
Axis Money Market Fund - Direct Plan - Growth Option
1.23%
Grand Total
100.00%
"""

    records = AxisAdapter().parse_pdf_text_many(text_fixture, _axis_context())

    assert len(records) == 1
    record = records[0]
    assert record.scheme_name == "Axis Large Cap Fund"
    assert record.report_month == date(2026, 3, 1)
    assert record.metrics["total_percent_aum"] == pytest.approx(29.84)
    names = {row.get("instrument_name") for row in record.holdings}
    assert "ICICI Bank Limited" in names
    assert "Axis NIFTY 50 ETF" in names
    assert "Grand Total" not in names
    assert "Mutual Fund Units" not in names


@pytest.mark.skipif(not AXIS_FACTSHEET.exists(), reason="backend/axis_factsheet.pdf is not available")
def test_axis_factsheet_metrics_are_deduped_and_sane():
    records = FactsheetParser().parse(str(AXIS_FACTSHEET), _axis_context())
    by_key: dict[str, list] = {}
    for record in records:
        by_key.setdefault(_scheme_key(record.scheme_name), []).append(record)

    assert all(len(group) == 1 for group in by_key.values())
    assert not [record for record in records if record.expense_ratio and record.expense_ratio > 3.0]

    expected = {
        "Axis Flexi Cap Fund": (12047.3, 0.70, "Nifty 500 TRI"),
        "Axis Large Cap Fund": (30376.3, 0.72, "BSE 100 TRI"),
        "Axis Focused Fund": (10585.87, 0.84, "Nifty 500 TRI"),
        "Axis Midcap Fund": (30205.58, 0.54, "BSE Midcap 150 TRI"),
        "Axis Small Cap Fund": (24812.7, 0.56, "Nifty Smallcap 250 TRI"),
        "Axis Money Market Fund": (8423.3, 0.17, "NIFTY Corporate Bond Index A-II"),
    }
    for scheme_name, (aum, ter, benchmark) in expected.items():
        record = by_key[_scheme_key(scheme_name)][0]
        assert record.aum == pytest.approx(aum)
        assert record.expense_ratio == pytest.approx(ter)
        assert record.benchmark == benchmark
        assert record.fund_manager


@pytest.mark.skipif(not AXIS_FACTSHEET.exists(), reason="backend/axis_factsheet.pdf is not available")
def test_axis_holdings_parse_bounded_nav_blocks_without_isin():
    records = HoldingsParser(AxisAdapter()).parse_many(str(AXIS_FACTSHEET), _axis_context())
    by_key = {_scheme_key(record.scheme_name): record for record in records}

    for scheme_name in (
        "Axis Flexi Cap Fund",
        "Axis Large Cap Fund",
        "Axis Focused Fund",
        "Axis Midcap Fund",
        "Axis Small Cap Fund",
        "Axis Money Market Fund",
    ):
        assert _scheme_key(scheme_name) in by_key
        record = by_key[_scheme_key(scheme_name)]
        assert record.metrics["total_percent_aum"] == pytest.approx(100.0)
        assert record.holdings
        assert any(row.get("isin") is None for row in record.holdings)

    money_market_names = {str(row.get("instrument_name") or "") for row in by_key[_scheme_key("Axis Money Market Fund")].holdings}
    assert "Reliance Industries Limited" not in money_market_names
    assert "Eternal Limited" not in money_market_names

    forbidden_names = {"Grand Total", "Domestic Equities", "Debt, Cash & other current assets", "EQUITY"}
    stored_names = {str(row.get("instrument_name") or "") for record in records for row in record.holdings}
    assert not forbidden_names & stored_names
    assert not [
        (record.scheme_name, record.metrics.get("total_percent_aum"))
        for record in records
        if record.metrics.get("total_percent_aum") == pytest.approx(414.62)
    ]


def test_axis_same_month_null_isin_holdings_are_replaced(monkeypatch):
    fake_supabase = _FakeSupabase(
        rows=[
            {
                "scheme_code": 123,
                "family_id": None,
                "as_of_date": "2026-03-01",
                "source": AMC_DISCLOSURE_SOURCE,
                "security_name": "Old Holding",
            },
            {
                "scheme_code": 123,
                "family_id": None,
                "as_of_date": "2026-02-01",
                "source": AMC_DISCLOSURE_SOURCE,
                "security_name": "Stale Holding",
            },
        ]
    )
    monkeypatch.setattr(parsing_service, "supabase", fake_supabase)

    service = object.__new__(ParsingService)
    service.r2_store = SimpleNamespace(enabled=False)

    service._archive_and_trim_holdings(
        scheme_code=123,
        family_id=None,
        current_report_month="2026-03-01",
        replace_current_month=True,
    )

    deleted_months = {filters["as_of_date"] for filters in fake_supabase.deletes}
    assert deleted_months == {"2026-02-01", "2026-03-01"}


class _FakeSupabase:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.deletes: list[dict] = []

    def table(self, table_name: str):
        return _FakeTable(self, table_name)


class _FakeTable:
    def __init__(self, root: _FakeSupabase, table_name: str) -> None:
        self.root = root
        self.table_name = table_name
        self.filters: dict[str, object] = {}
        self.is_delete = False

    def select(self, _columns: str):
        return self

    def delete(self):
        self.is_delete = True
        return self

    def eq(self, key: str, value):
        self.filters[key] = value
        return self

    def execute(self):
        if self.is_delete:
            self.root.deletes.append(dict(self.filters))
            return SimpleNamespace(data=[])

        rows = list(self.root.rows)
        for key, value in self.filters.items():
            rows = [row for row in rows if row.get(key) == value]
        return SimpleNamespace(data=rows)
