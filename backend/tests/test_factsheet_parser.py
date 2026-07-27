from __future__ import annotations

from datetime import date

import pytest

from app.mf_ingestion.parsers.factsheet_parser import (
    FactsheetParser,
    _detect_dominant_factsheet_month,
    _extract_page_aligned_risk_levels,
    _map_document_order_risk_labels,
    _riskometer_row_scheme_names,
    _risk_label_from_needle_angle,
    filter_factsheet_records_for_amc,
)


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


@pytest.mark.parametrize(
    "scheme_name",
    [
        "UTI - Flexi Cap Fund",
        "DSP Mid Cap Fund",
        "Kotak Equity Opportunities Fund",
        "Aditya Birla Sun Life Frontline Equity Fund",
    ],
)
def test_factsheet_parser_recognizes_all_new_production_amc_prefixes(scheme_name):
    text = f"""
Name of the Fund
{scheme_name}
AMFI Tier I Benchmark Index
NIFTY 500 (TRI)
Assets Under Management
(AUM) as on Jun 30, 2026
` 1,234.56 Crores
Base Expense Ratio
Regular Plan: 1.05%
Direct Plan: 0.53%
Name of the Fund Managers
Mr. Test Manager
"""

    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 6, 1))

    assert len(records) == 1
    assert records[0].scheme_name == scheme_name
    assert records[0].aum == 1234.56
    assert records[0].expense_ratio == 0.53
    assert records[0].benchmark == "NIFTY 500 (TRI)"
    assert records[0].fund_manager == "Mr. Test Manager"


def test_factsheet_records_are_scoped_to_the_document_amc():
    text = """
Kotak Equity Opportunities Fund
Direct Plan: 0.53%
NIFTY 500 (TRI)

Axis Ultra Short Term Fund
Direct Plan: 0.25%
NIFTY Ultra Short Duration Debt Index

ICICI Prudential Ultra Short Term Fund
Direct Plan: 0.22%
NIFTY Ultra Short Duration Debt Index
"""

    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 6, 1))
    kotak_records = filter_factsheet_records_for_amc(records, "KOTAK")

    assert [record.scheme_name for record in kotak_records] == ["Kotak Equity Opportunities Fund"]


def test_factsheet_parser_extracts_kotak_aum_label():
    text = """
Name of the Fund
Kotak Equity Opportunities Fund
Fund Manager*: Mr. Rohit Tandon
AAUM: `10,636.99 crs
AUM: `10,772.29 crs
Benchmark***: Nifty 100 TRI
Direct Plan: 0.67%
"""

    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 6, 1))

    assert records[0].aum == 10772.29
    assert records[0].fund_manager == "Mr. Rohit Tandon"


def test_factsheet_parser_extracts_mirae_net_aum_and_etf_expense_ratio():
    text = """
MIRAE ASSET BSE 500 DIVIDEND LEADERS 50 ETF
Benchmark:
BSE 500 Dividend Leaders 50 (TRI)
Net AUM (Cr.)
10.2423
Base Expense Ratio: 0.17%
Fund Managers :
Ms. Ekta Gala
Mr. Akshay Udeshi
"""

    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 6, 1))

    assert records[0].aum == 10.2423
    assert records[0].expense_ratio == 0.17


def test_page_aligned_riskometer_maps_columnar_scheme_order():
    page = """
FUND FACTS - DEBT
Mirae Asset Liquid Fund
Mirae Asset Low Duration Fund
Mirae Asset Dynamic Bond Fund
Scheme Riskometer
The risk of the scheme is Low to Moderate
Scheme Riskometer
The risk of the scheme is Moderate
Scheme Riskometer
The risk of the scheme is Moderately High
Benchmark Riskometer
The risk of the benchmark is Low
"""

    risks = _extract_page_aligned_risk_levels([page])

    assert risks == {
        "miraeassetliquidfund": "Low to Moderate",
        "miraeassetlowdurationfund": "Moderate",
        "miraeassetdynamicbondfund": "Moderately High",
    }


def test_page_aligned_riskometer_handles_split_names_and_footnote_markers():
    page = """
Mirae Asset BSE 500 Dividend Leaders
50 ETF$
Mirae Asset Nifty Top 20 Equal Weight
ETF$
The risk of the scheme is Very High
The risk of the scheme is High
"""

    risks = _extract_page_aligned_risk_levels([page])

    assert risks == {
        "miraeassetbse500dividendleaders50etf": "Very High",
        "miraeassetniftytop20equalweightetf": "High",
    }


def test_page_aligned_riskometer_abstains_when_column_counts_do_not_match():
    page = """
Mirae Asset Liquid Fund
Mirae Asset Dynamic Bond Fund
The risk of the scheme is Low
"""

    assert _extract_page_aligned_risk_levels([page]) == {}


@pytest.mark.parametrize(
    ("angle", "expected"),
    [
        (165.0, "Low"),
        (135.0, "Low to Moderate"),
        (105.0, "Moderate"),
        (75.0, "Moderately High"),
        (45.0, "High"),
        (15.0, "Very High"),
        (-1.0, None),
        (181.0, None),
    ],
)
def test_vector_riskometer_needle_angle_is_deterministic(angle, expected):
    assert _risk_label_from_needle_angle(angle) == expected


def test_vector_riskometer_document_order_requires_exact_complete_counts():
    schemes = ["DSP Flexi Cap Fund", "DSP Overnight Fund"]
    labels = ["Very High", "Low"]

    assert _map_document_order_risk_labels(schemes, labels, expected_scheme_count=2) == {
        "dspflexicapfund": "Very High",
        "dspovernightfund": "Low",
    }
    assert _map_document_order_risk_labels(schemes, labels[:1], expected_scheme_count=2) == {}


def test_vector_riskometer_rows_map_scheme_text_by_vertical_position():
    blocks = [
        (48.0, 55.0, 121.0, 88.0, "DSP Flexi Cap Fund\nDescription", 0, 0),
        (
            48.0,
            120.0,
            121.0,
            165.0,
            "DSP ELSS Tax Saver\nFund (erstwhile\nknown as DSP Tax\nSaver Fund)$$\nDescription",
            1,
            0,
        ),
    ]
    rows = [(90.0, "Very High"), (170.0, "High")]

    assert _riskometer_row_scheme_names(blocks, rows, page_height=220.0) == [
        "DSP Flexi Cap Fund",
        "DSP ELSS Tax Saver Fund",
    ]


def test_factsheet_parser_extracts_untitled_dsp_managers_and_total_aum():
    text = """
Name of the Fund
DSP Large & Mid Cap Fund
FUND MANAGER
Rohit Singhania
Total work experience of 24 years.
Managing this Scheme since June 2015.
Nilesh Aiya
Total work experience of 16 years.
Managing this Scheme since September 2025.
TOTAL AUM 17,906 Cr.
MONTHLY AVERAGE AUM 17,673 Cr.
Direct Plan : 1.37%
BENCHMARK Nifty Large Midcap 250 (TRI)
"""

    records = FactsheetParser().parse_text(text=text, report_month=date(2026, 6, 1))

    assert records[0].aum == 17906.0
    assert records[0].fund_manager == "Rohit Singhania; Nilesh Aiya"


def test_factsheet_parser_extracts_nippon_manager_parentheses_and_single_etf_ter():
    text = """
Nippon India Nifty Chemicals ETF
Fund Manager(s)
Rupesh Patel (Managing Since Jan 2023)
Rishit Parikh (Assistant Fund Manager) (Managing Since Aug 2024)
AMFI Tier 1 Benchmark
Nifty Chemicals TRI
Fund Size
Month End:
88.46 Cr
Total Expense Ratio**
0.25%
"""

    record = FactsheetParser().parse_text(text, report_month=date(2026, 6, 1))[0]

    assert record.expense_ratio == 0.25
    assert record.fund_manager == "Rupesh Patel; Rishit Parikh"


def test_factsheet_parser_extracts_sbi_month_end_aum_and_ratio_matrix():
    text = """
SBI Automotive Opportunities Fund
Fund Size ` in Cr. $ in Mn.
Month end AUM 5,380.73 568.80
Monthly Avg. AUM 5,253.91 555.40
Expense Ratio
Plan Regular Direct
TER 2.04 1.01
BER 1.59 0.70
Fund Manager Total Experience Managing Since
Mr. Tanmaya Desai 17 years June-2024
Benchmark NIFTY Auto TRI
"""

    record = FactsheetParser().parse_text(text, report_month=date(2026, 6, 1))[0]

    assert record.aum == 5380.73
    assert record.expense_ratio == 1.01


def test_factsheet_parser_extracts_sbi_passive_aum_ter_and_managed_by():
    text = """
SBI BSE PSU Bank Index Fund
AUM as on June 30, 2026: ` 263.49 crores
Total Expense Ratio:
Regular Plan 0.87
Direct Plan 0.43
Fund managed by Mr Viral Chhadva
Riskometer (BSE PSU BANK TRI)
"""

    record = FactsheetParser().parse_text(text, report_month=date(2026, 6, 1))[0]

    assert record.aum == 263.49
    assert record.expense_ratio == 0.43
    assert record.fund_manager == "Mr Viral Chhadva"
    assert record.benchmark == "BSE PSU BANK TRI"


def test_factsheet_parser_extracts_icici_untitled_managers_and_riskometer_benchmark():
    text = """
ICICI Prudential Banking & Financial Services Fund
Riskometer (Nifty Financial Services TRI)
Fund Managers** :
Nitya Mishra (Managing this fund since March, 2026 & Overall 14 years of experience)
Venus Ahuja (Managing this fund since November, 2025 & Overall 3 years of experience)
Closing AUM as on 30-Jun-26 : Rs. 1,590.67 crores
Direct : 0.87% p. a.
"""

    record = FactsheetParser().parse_text(text, report_month=date(2026, 6, 1))[0]

    assert record.benchmark == "Nifty Financial Services TRI"
    assert record.fund_manager == "Nitya Mishra; Venus Ahuja"


def test_factsheet_parser_trims_manager_sentences_and_rejects_mirae_fact_headers():
    text = """
MIRAE ASSET INVESTMENT MANAGERS (INDIA) PRIVATE LIMITED FUND FACTS - ETF
Direct Plan: 0.10%

ICICI Prudential Equity Savings Fund
Fund Managers :
Mr. Sankaran Naren has been managing this fund since Sep 2018.
Mr. Mohit jain (Debt Portion)
Closing AUM as on 30-Jun-26 : Rs. 1,000 crores
"""

    records = FactsheetParser().parse_text(text, report_month=date(2026, 6, 1))

    assert [record.scheme_name for record in records] == ["ICICI Prudential Equity Savings Fund"]
    assert records[0].fund_manager == "Mr. Sankaran Naren; Mr. Mohit jain"


def test_dominant_factsheet_month_detects_stale_internal_month():
    text = """
Nippon India Large Cap Fund
Details as on May 31, 2026
Nippon India Small Cap Fund
Details as on May 31, 2026
Nippon India Value Fund
Details as on May 31, 2026
Published in June 2026.
"""

    assert _detect_dominant_factsheet_month(text) == date(2026, 5, 1)


def test_dominant_factsheet_month_abstains_on_ambiguous_dates():
    text = """
SBI Large Cap Fund
Details as on May 31, 2026
SBI Small Cap Fund
Details as on June 30, 2026
SBI Value Fund
Details as on July 31, 2026
"""

    assert _detect_dominant_factsheet_month(text) is None


def test_factsheet_parser_extracts_delayed_and_split_ppfas_manager_names():
    text = """
Name of the Fund
Parag Parikh Liquid Fund
Name of the
Fund Managers
Assets Under Management
5,574.76 Crores
Regular Plan: 0.17%
Direct Plan: 0.09%
Quantitative Indicators
Modified Duration
Mr.
 -
Tejas Soman
Chief Investment Officer - Debt
Ms. Mansi Kariya - Associate Vice President & Fund Manager
"""

    record = FactsheetParser().parse_text(text, report_month=date(2026, 6, 1))[0]

    assert record.fund_manager == "Mr. Tejas Soman; Ms. Mansi Kariya"


def test_factsheet_parser_extracts_dsp_single_plan_and_fof_direct_expense_ratio():
    etf = """
DSP BSE Sensex ETF
TOTAL AUM
4 Cr.
Month End Expense
Ratio**
0.20%
BENCHMARK
BSE Sensex TRI
"""
    fof = """
DSP Multi Asset Allocation Fund
TOTAL AUM
831 Cr.
Month End Expense Ratio
Plan Name
Base Expense Ratio (BER)
Scheme
Underlying Funds
Total
Direct
0.15%
0.38%
0.53%
Regular
0.89%
0.38%
1.27%
BENCHMARK
Composite TRI
"""

    etf_record = FactsheetParser().parse_text(etf, report_month=date(2026, 6, 1))[0]
    fof_record = FactsheetParser().parse_text(fof, report_month=date(2026, 6, 1))[0]

    assert etf_record.expense_ratio == 0.20
    assert fof_record.expense_ratio == 0.15


def test_page_numbered_sections_do_not_split_on_fund_names_inside_holdings():
    text = """
1
DSP Flexi Cap Fund
TOTAL AUM
100 Cr.
Direct Plan: 0.50%

2
DSP Multi Asset Allocation Fund
TOTAL AUM
831 Cr.
Mutual Funds
DSP Gilt Fund
22.96%
DSP NIFTY IT ETF
12.30%
Month End Expense Ratio
Plan Name
Scheme
Underlying Funds
Total
Direct
0.15%
0.38%
0.53%

3
DSP Nifty 50 Index Fund
TOTAL AUM
200 Cr.
Direct Plan: 0.10%

4
DSP Overnight Fund
TOTAL AUM
300 Cr.
Direct Plan: 0.08%

5
DSP Bond Fund
TOTAL AUM
400 Cr.
Direct Plan: 0.25%
"""

    records = FactsheetParser().parse_text(text, report_month=date(2026, 6, 1))
    by_name = {record.scheme_name: record for record in records}

    assert by_name["DSP Multi Asset Allocation Fund"].aum == 831.0
    assert by_name["DSP Multi Asset Allocation Fund"].expense_ratio == 0.15


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
