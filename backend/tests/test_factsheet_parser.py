from __future__ import annotations

from datetime import date

from app.mf_ingestion.parsers.factsheet_parser import FactsheetParser


def test_factsheet_parser_extracts_ppfas_core_fields_from_text():
    text = """
Name of the Fund
Parag Parikh Flexi Cap Fund (PPFCF)
AMFI Tier I Benchmark Index
NIFTY 500 (TRI)
Assets Under Management
(AUM) as on Apr 30, 2026
` 1,37,579.16 Crores
Base Expense Ratio
Regular Plan: 1.05%
Direct Plan: 0.53%
Name of the Fund Managers
Mr. Rajeev Thakkar - Chief Investment Officer
Mr. Raj Mehta - Executive Vice President
"""
    parser = FactsheetParser()
    records = parser.parse_text(text=text, report_month=date(2026, 4, 1))

    assert len(records) == 1
    record = records[0]
    assert record.scheme_name == "Parag Parikh Flexi Cap Fund"
    assert record.aum == 137579.16
    assert record.expense_ratio == 0.53
    assert record.benchmark == "NIFTY 500 (TRI)"
    assert "Mr. Rajeev Thakkar" in (record.fund_manager or "")
    assert "Mr. Raj Mehta" in (record.fund_manager or "")


def test_factsheet_parser_prefers_closing_aum_when_present():
    text = """
ICICI Prudential Active Momentum Fund
Scheme Details
Benchmark
Nifty 500 TRI
Monthly AAUM as on 30-Apr-26 : Rs. 382.37 crores
Closing AUM as on 30-Apr-26 : Rs. 390.13 crores
Fund Managers :
Ms. Manasvi Shah
Base Expense Ratio :
Other : 1.14% p. a.
Direct : 0.72% p. a.
"""
    parser = FactsheetParser()
    records = parser.parse_text(text=text, report_month=date(2026, 4, 1))

    assert len(records) == 1
    record = records[0]
    assert record.scheme_name == "ICICI Prudential Active Momentum Fund"
    assert record.aum == 390.13
    assert record.expense_ratio == 0.72
    assert record.benchmark == "Nifty 500 TRI"
    assert "Ms. Manasvi Shah" in (record.fund_manager or "")


def test_factsheet_parser_backfills_aum_from_later_scheme_occurrence():
    text = """
ICICI Prudential Large Cap Fund
Base Expense Ratio :
Other : 1.40% p. a.
Direct : 0.64% p. a.

Returns of ICICI Prudential Large Cap Fund - Growth Option as on April 30, 2026
Scheme Details
Monthly AAUM as on 30-Apr-26 : Rs. 20,441.38 crores
Closing AUM as on 30-Apr-26 : Rs. 20,936.07 crores
"""
    parser = FactsheetParser()
    records = parser.parse_text(text=text, report_month=date(2026, 4, 1))

    assert len(records) == 1
    record = records[0]
    assert record.scheme_name == "ICICI Prudential Large Cap Fund"
    assert record.expense_ratio == 0.64
    assert record.aum == 20936.07
