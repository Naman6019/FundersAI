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


def test_factsheet_parser_ignores_ppfas_contents_list_when_anchored_sections_exist():
    text = """
Parag Parikh Flexi Cap Fund
Parag Parikh ELSS Tax Saver Fund
Parag Parikh Liquid Fund

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

Riskometers as on April 30, 2026
Parag Parikh Flexi Cap Fund
The risk of the scheme is very high risk
"""
    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 4, 1))

    assert len(records) == 1
    assert records[0].scheme_name == "Parag Parikh Flexi Cap Fund"
    assert records[0].aum == 137579.16
    assert records[0].expense_ratio == 0.53
    assert records[0].benchmark == "NIFTY 500 (TRI)"
    assert records[0].risk_level == "Very High"


def test_factsheet_parser_maps_ppfas_riskometer_section_to_schemes():
    text = """
Name of the Fund
Parag Parikh ELSS Tax Saver Fund
Direct Plan: 0.62%

Name of the Fund
Parag Parikh Conservative Hybrid Fund
Direct Plan: 0.31%

Name of the Fund
Parag Parikh Arbitrage Fund
Direct Plan: 0.35%

Riskometers as on April 30, 2026
Parag Parikh ELSS Tax Saver Fund
The risk of the scheme is very high risk
Parag Parikh Conservative Hybrid Fund
The risk of the scheme is moderately high risk
Parag Parikh Arbitrage Fund
The risk of the scheme is low risk
"""
    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 4, 1))
    risk_by_name = {record.scheme_name: record.risk_level for record in records}

    assert risk_by_name["Parag Parikh ELSS Tax Saver Fund"] == "Very High"
    assert risk_by_name["Parag Parikh Conservative Hybrid Fund"] == "Moderately High"
    assert risk_by_name["Parag Parikh Arbitrage Fund"] == "Low"


def test_factsheet_parser_extracts_ppfas_split_aum_and_direct_expense():
    text = """
Name of the Fund
Parag Parikh ELSS Tax Saver Fund (PPTSF)
AMFI Tier I Benchmark Index
NIFTY 500 (TRI)
Assets Under Management
(AUM) as on Apr 30, 2026
`
 Crores
5,594.27
Average AUM for the Month
`
 Crores
5,617.03
Regular Plan: 1.54%*
Direct Plan: 0.54%*
"""
    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 4, 1))

    assert len(records) == 1
    assert records[0].aum == 5594.27
    assert records[0].expense_ratio == 0.54
    assert records[0].benchmark == "NIFTY 500 (TRI)"


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


def test_factsheet_parser_extracts_the_risk_of_scheme_label():
    text = """
Parag Parikh Flexi Cap Fund
The risk of the scheme is Very High
"""
    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 4, 1))

    assert len(records) == 1
    assert records[0].risk_level == "Very High"


def test_factsheet_parser_extracts_riskometer_label():
    text = """
HDFC Large Cap Fund
Riskometer: Moderate
"""
    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 4, 1))

    assert len(records) == 1
    assert records[0].risk_level == "Moderate"


def test_factsheet_parser_extracts_principal_risk_label():
    text = """
ICICI Prudential Large Cap Fund
Investors understand that their principal will be at Very High risk
"""
    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 4, 1))

    assert len(records) == 1
    assert records[0].risk_level == "Very High"


def test_factsheet_parser_rejects_product_labelling_as_benchmark():
    text = """
HDFC Arbitrage Fund
Benchmark
Product Labelling
Assets Under Management
Rs. 25,084.91 Crores
Direct Plan: 0.01%
"""
    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 5, 1))

    assert len(records) == 1
    assert records[0].benchmark is None


def test_factsheet_parser_extracts_hdfc_benchmark_index_label():
    text = """
HDFC Large Cap Fund
ASSETS UNDER MANAGEMENT
As on May 31, 2026
37,808.31Cr.
EXPENSE RATIO
Direct: 0.99%
#BENCHMARK INDEX
NIFTY 100 Total Returns Index (TRI)
##ADDL. BENCHMARK INDEX
BSE SENSEX Index (TRI)
"""
    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 5, 1))

    assert len(records) == 1
    assert records[0].benchmark == "NIFTY 100 Total Returns Index (TRI)"


def test_factsheet_parser_extracts_sbi_same_line_benchmark_index_label():
    text = """
SBI Large & Midcap Fund
Benchmark Index: Nifty LargeMidcap 250 TRI
Assets Under Management Rs. 24,500 crores
Direct Plan: 0.72%
"""
    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 5, 1))

    assert len(records) == 1
    assert records[0].benchmark == "Nifty LargeMidcap 250 TRI"


def test_factsheet_parser_extracts_nippon_tier_one_benchmark_label():
    text = """
Nippon India Small Cap Fund
Tier I Benchmark: Nifty Smallcap 250 TRI
Assets Under Management Rs. 59,456.65 crores
Direct Plan: 0.67%
"""
    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 5, 1))

    assert len(records) == 1
    assert records[0].benchmark == "Nifty Smallcap 250 TRI"


def test_factsheet_parser_extracts_icici_scheme_benchmark_label():
    text = """
ICICI Prudential Multi Asset Fund
Scheme Benchmark - NIFTY 50 Hybrid Composite Debt 50:50 Index
Closing AUM as on 31-May-26 : Rs. 50,000 crores
Direct : 0.82% p. a.
"""
    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 5, 1))

    assert len(records) == 1
    assert records[0].benchmark == "NIFTY 50 Hybrid Composite Debt 50:50 Index"


def test_factsheet_parser_rejects_returns_table_label_as_benchmark():
    text = """
HDFC BSE 500 ETF
Benchmark
Returns
Assets Under Management
Rs. 100 Crores
Direct Plan: 0.20%
"""
    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 5, 1))

    assert len(records) == 1
    assert records[0].benchmark is None


def test_factsheet_parser_ignores_malformed_riskometer_text():
    text = """
SBI Large Cap Fund
Riskometer: Banana
Direct Plan: 0.61%
"""
    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 4, 1))

    assert len(records) == 1
    assert records[0].risk_level is None
