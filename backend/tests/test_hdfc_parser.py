from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd

from app.mf_ingestion.parsers.adapters.hdfc_adapter import HDFCAdapter, _dedupe_holdings


def test_hdfc_parse_holdings_extracts_rows_from_portfolio_frame():
    frame = pd.DataFrame(
        [
            ["HDFC Large and Mid Cap Fund", None, None, None],
            ["PORTFOLIO", None, None, None],
            ["Company/Instrument", "Industry+ /Rating", "% to", None],
            [None, None, "NAV", None],
            ["ICICI Bank Ltd.", "Banks", None, 9.15],
            ["HDFC Bank Ltd.", "Banks", None, 7.84],
            ["Sub Total", None, None, 16.99],
        ],
        columns=["c1", "c2", "c3", "c4"],
    )

    adapter = HDFCAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[],
        pdf_table_frames=[frame],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-1", source_url="local", report_month=date(2026, 4, 1)),
    )

    assert parsed.scheme_name == "HDFC Large and Mid Cap Fund"
    assert parsed.report_month == date(2026, 4, 1)
    assert len(parsed.holdings) == 2
    assert parsed.holdings[0]["instrument_name"] == "ICICI Bank Ltd."
    assert parsed.holdings[0]["isin"] is None
    assert parsed.holdings[0]["percent_aum"] == 9.15
    assert parsed.metrics["total_percent_aum"] == 16.99


def test_hdfc_parse_holdings_tolerates_missing_isin():
    frame = pd.DataFrame(
        [
            ["HDFC Balanced Advantage Fund", None, None, None],
            ["PORTFOLIO", None, None, None],
            ["Company/Instrument", "Industry+ /Rating", "% to NAV", None],
            ["7.29% Rajasthan SDL ISD 191125 MAT 191137", "Sovereign", 0.06, None],
            ["7.48% Andhra Pradesh SDL ISD 030925 MAT 030934", "Sovereign", 0.06, None],
        ],
        columns=["c1", "c2", "c3", "c4"],
    )

    adapter = HDFCAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[],
        pdf_table_frames=[frame],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-2", source_url="local", report_month=date(2026, 4, 1)),
    )

    assert parsed.scheme_name == "HDFC Balanced Advantage Fund"
    assert len(parsed.holdings) == 2
    assert parsed.holdings[0]["isin"] is None
    assert parsed.holdings[0]["percent_aum"] == 0.06


def test_hdfc_parse_holdings_extracts_rows_from_monthly_excel_frame():
    frame = pd.DataFrame(
        [
            ["Portfolio as on 30-Apr-2026", None, None, None, None, None, None, None],
            [None, "ISIN", "Coupon (%)", "Name Of the Instrument", "Industry+ /Rating", "Quantity", "Market/ Fair Value", "% to NAV"],
            [None, "INE090A01021", None, "ICICI Bank Ltd.", "Banks", 100, 1000, 6.47],
            [None, "INE040A01034", None, "HDFC Bank Ltd.Ł", "Banks", 100, 1000, 5.45],
            [None, None, None, "Grand Total", None, None, None, 100.0],
            # pandas 3 forward-fills merged summary values while leaving the
            # instrument cell as NaN. These rows must not inflate the total.
            [None, None, None, float("nan"), None, None, None, 100.0],
            [None, None, None, float("nan"), None, None, None, 100.0],
            [None, None, None, float("nan"), None, None, None, 100.0],
        ],
        columns=[
            "HDFC Value Fund (An open ended equity scheme following a value investment strategy)",
            "HDFC Value Fund (An open ended equity scheme following a value investment strategy).1",
            "HDFC Value Fund (An open ended equity scheme following a value investment strategy).2",
            "HDFC Value Fund (An open ended equity scheme following a value investment strategy).3",
            "HDFC Value Fund (An open ended equity scheme following a value investment strategy).4",
            "HDFC Value Fund (An open ended equity scheme following a value investment strategy).5",
            "HDFC Value Fund (An open ended equity scheme following a value investment strategy).6",
            "HDFC Value Fund (An open ended equity scheme following a value investment strategy).7",
        ],
    )

    adapter = HDFCAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-xlsx", source_url="local", report_month=date(2026, 4, 1)),
    )

    assert parsed.scheme_name == "HDFC Value Fund"
    assert parsed.report_month == date(2026, 4, 1)
    assert len(parsed.holdings) == 2
    assert parsed.holdings[0]["isin"] == "INE090A01021"
    assert parsed.holdings[0]["quantity"] == 100.0
    assert parsed.holdings[0]["market_value"] == 1000.0
    assert parsed.holdings[1]["instrument_name"] == "HDFC Bank Ltd."
    assert parsed.holdings[1]["isin"] == "INE040A01034"
    assert parsed.metrics["total_percent_aum"] == 11.92


def test_hdfc_parse_holdings_extracts_scheme_names_without_fund_fof_etf_suffix():
    """Regression for source_document_id e3816d5c-44bf-403a-90ac-e22e12aa43f2 (HDFC ELSS Tax
    saver, June 2026): schemes whose official title never contains Fund/FOF/ETF (ELSS "Tax
    saver", "FMP <tenure>D <month> <year>", "Long Term Advantage Plan") were silently dropped
    because SCHEME_PATTERN required one of those words. The title's parenthetical scheme-type
    description is a reliable name boundary even without that keyword."""
    frame = pd.DataFrame(
        [
            ["Portfolio as on 30-Jun-2026", None, None, None, None, None, None, None],
            [None, "ISIN", "Coupon (%)", "Name Of the Instrument", "Industry+ /Rating", "Quantity", "Market/ Fair Value", "% to NAV"],
            [None, "INE090A01021", None, "ICICI Bank Ltd.", "Banks", 11000000, 151272, 9.64],
            [None, "INE040A01034", None, "HDFC Bank Ltd.", "Banks", 16600000, 132459.7, 8.44],
        ],
        columns=[
            "HDFC ELSS Tax saver (An Open-ended Equity Linked Savings Scheme with a statutory lock in of 3 years and tax benefit)",
            "HDFC ELSS Tax saver (An Open-ended Equity Linked Savings Scheme with a statutory lock in of 3 years and tax benefit).1",
            "HDFC ELSS Tax saver (An Open-ended Equity Linked Savings Scheme with a statutory lock in of 3 years and tax benefit).2",
            "HDFC ELSS Tax saver (An Open-ended Equity Linked Savings Scheme with a statutory lock in of 3 years and tax benefit).3",
            "HDFC ELSS Tax saver (An Open-ended Equity Linked Savings Scheme with a statutory lock in of 3 years and tax benefit).4",
            "HDFC ELSS Tax saver (An Open-ended Equity Linked Savings Scheme with a statutory lock in of 3 years and tax benefit).5",
            "HDFC ELSS Tax saver (An Open-ended Equity Linked Savings Scheme with a statutory lock in of 3 years and tax benefit).6",
            "HDFC ELSS Tax saver (An Open-ended Equity Linked Savings Scheme with a statutory lock in of 3 years and tax benefit).7",
        ],
    )

    adapter = HDFCAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-elss", source_url="local", report_month=date(2026, 6, 1)),
    )

    assert parsed.scheme_name == "HDFC ELSS Tax saver"
    assert len(parsed.holdings) == 2
    assert parsed.holdings[0]["isin"] == "INE090A01021"


def test_hdfc_parse_holdings_extracts_fmp_scheme_names():
    """Regression for source_document_id a977da99-7553-4c9d-859c-ee9245d7782a (HDFC FMP 1269D
    March 2023, June 2026): same missing-Fund-suffix bug as the ELSS case above, affecting every
    FMP portfolio disclosure."""
    frame = pd.DataFrame(
        [
            ["Portfolio as on 30-Jun-2026", None, None, None, None, None, None, None],
            [None, "ISIN", "Coupon (%)", "Name Of the Instrument", "Industry+ /Rating", "Quantity", "Market/ Fair Value", "% to NAV"],
            [None, "IN2020X01234", 7.5, "7.5% Government of India 2032", "Sovereign", 500000, 50000, 98.5],
        ],
        columns=[
            "HDFC FMP 1269D March 2023 (A Close Ended Income Scheme With Tenure 1269 Days. A Relatively High Interest Rate Risk And Relatively Low Credit Risk)",
            "HDFC FMP 1269D March 2023 (A Close Ended Income Scheme With Tenure 1269 Days. A Relatively High Interest Rate Risk And Relatively Low Credit Risk).1",
            "HDFC FMP 1269D March 2023 (A Close Ended Income Scheme With Tenure 1269 Days. A Relatively High Interest Rate Risk And Relatively Low Credit Risk).2",
            "HDFC FMP 1269D March 2023 (A Close Ended Income Scheme With Tenure 1269 Days. A Relatively High Interest Rate Risk And Relatively Low Credit Risk).3",
            "HDFC FMP 1269D March 2023 (A Close Ended Income Scheme With Tenure 1269 Days. A Relatively High Interest Rate Risk And Relatively Low Credit Risk).4",
            "HDFC FMP 1269D March 2023 (A Close Ended Income Scheme With Tenure 1269 Days. A Relatively High Interest Rate Risk And Relatively Low Credit Risk).5",
            "HDFC FMP 1269D March 2023 (A Close Ended Income Scheme With Tenure 1269 Days. A Relatively High Interest Rate Risk And Relatively Low Credit Risk).6",
            "HDFC FMP 1269D March 2023 (A Close Ended Income Scheme With Tenure 1269 Days. A Relatively High Interest Rate Risk And Relatively Low Credit Risk).7",
        ],
    )

    adapter = HDFCAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-fmp", source_url="local", report_month=date(2026, 6, 1)),
    )

    assert parsed.scheme_name == "HDFC FMP 1269D March 2023"
    assert len(parsed.holdings) == 1
    assert parsed.holdings[0]["isin"] == "IN2020X01234"


def test_hdfc_parse_holdings_splits_inline_name_percent_sequences_and_detects_month():
    frame = pd.DataFrame(
        [
            ["HDFC Multi Cap Fund", None, None],
            ["PORTFOLIO", None, None],
            ["As on 30 April 2026", None, None],
            [
                "Prestige Estates Projects Ltd. Realty 0.83 Mphasis Limited IT - Software 0.82 "
                "Bajaj Consumer Care Ltd. Personal Products 0.81",
                None,
                None,
            ],
        ],
        columns=["c1", "c2", "c3"],
    )
    frame.attrs["page_text_full"] = (
        "HDFC Multi Cap Fund\nPORTFOLIO\nAs on 30 April 2026\n"
        "Prestige Estates Projects Ltd. Realty 0.83 Mphasis Limited IT - Software 0.82 "
        "Bajaj Consumer Care Ltd. Personal Products 0.81\n"
    )

    adapter = HDFCAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[],
        pdf_table_frames=[frame],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-3", source_url="local", report_month=None),
    )

    assert parsed.scheme_name == "HDFC Multi Cap Fund"
    assert parsed.report_month == date(2026, 4, 1)
    assert len(parsed.holdings) >= 3
    assert any(row["instrument_name"] == "Prestige Estates Projects Ltd. Realty" for row in parsed.holdings)
    assert any(row["percent_aum"] == 0.82 for row in parsed.holdings)


def test_hdfc_parse_holdings_ignores_full_text_when_multiple_schemes_present():
    frame = pd.DataFrame(
        [
            ["HDFC First Fund", None, None, None],
            ["PORTFOLIO", None, None, None],
            ["Company/Instrument", "Industry+ /Rating", "% to NAV", None],
            ["ICICI Bank Ltd.", "Banks", 100.0, None],
        ],
        columns=["c1", "c2", "c3", "c4"],
    )
    frame.attrs["page_text_full"] = (
        "HDFC First Fund\nPORTFOLIO\nICICI Bank Ltd. Banks 100.00\n"
        "HDFC Second Fund\nPORTFOLIO\nInfosys Ltd. IT - Software 100.00\n"
    )

    adapter = HDFCAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[],
        pdf_table_frames=[frame],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-4", source_url="local", report_month=date(2026, 4, 1)),
    )

    assert parsed.scheme_name == "HDFC First Fund"
    assert len(parsed.holdings) == 1
    assert parsed.holdings[0]["instrument_name"] == "ICICI Bank Ltd."
    assert parsed.metrics["total_percent_aum"] == 100.0


def test_hdfc_word_column_rows_are_not_merged_with_sector_summary_text():
    frame = pd.DataFrame(
        [
            ["HDFC Large Cap Fund", None, None],
            ["PORTFOLIO", None, None],
            ["Company/Instrument", "Industry+ /Rating", "% to NAV"],
            ["Incorrect Table Row", "Banks", 100.0],
        ]
    )
    frame.attrs["page_words"] = [
        {"text": "HDFC", "x0": 200, "x1": 225, "top": 150},
        {"text": "Bank", "x0": 228, "x1": 255, "top": 150},
        {"text": "Banks", "x0": 280, "x1": 320, "top": 150},
        {"text": "60.00", "x0": 350, "x1": 375, "top": 150},
        {"text": "Infosys", "x0": 200, "x1": 240, "top": 165},
        {"text": "Limited", "x0": 243, "x1": 280, "top": 165},
        {"text": "IT", "x0": 282, "x1": 294, "top": 165},
        {"text": "40.00", "x0": 350, "x1": 375, "top": 165},
        {"text": "Small", "x0": 200, "x1": 225, "top": 180},
        {"text": "One", "x0": 228, "x1": 250, "top": 180},
        {"text": "Banks", "x0": 280, "x1": 320, "top": 180},
        {"text": "0.01", "x0": 350, "x1": 375, "top": 180},
        {"text": "Small", "x0": 200, "x1": 225, "top": 195},
        {"text": "Two", "x0": 228, "x1": 250, "top": 195},
        {"text": "Banks", "x0": 280, "x1": 320, "top": 195},
        {"text": "0.01", "x0": 350, "x1": 375, "top": 195},
        {"text": "Small", "x0": 200, "x1": 225, "top": 210},
        {"text": "Three", "x0": 228, "x1": 260, "top": 210},
        {"text": "Banks", "x0": 280, "x1": 320, "top": 210},
        {"text": "0.01", "x0": 350, "x1": 375, "top": 210},
        {"text": "Small", "x0": 200, "x1": 225, "top": 225},
        {"text": "Four", "x0": 228, "x1": 255, "top": 225},
        {"text": "Banks", "x0": 280, "x1": 320, "top": 225},
        {"text": "0.01", "x0": 350, "x1": 375, "top": 225},
    ]
    frame.attrs["page_text_full"] = (
        "HDFC Large Cap Fund\nPORTFOLIO\nCompany/Instrument\n"
        "HDFC Bank Limited Banks 60.00\nInfosys Limited IT - Software 40.00\n"
        "Insurance 96.76\n"
    )

    parsed = HDFCAdapter().parse_holdings(
        excel_frames=[],
        pdf_table_frames=[frame],
        pdf_text="",
        context=SimpleNamespace(
            source_document_id="hdfc-word-column",
            source_url="local",
            report_month=date(2026, 6, 1),
        ),
    )

    assert parsed.metrics["total_percent_aum"] == 100.04
    assert all(row["instrument_name"] != "Insurance" for row in parsed.holdings)


def test_hdfc_dedupe_removes_fragmented_subtotal_rows():
    holdings = _dedupe_holdings([
        {"instrument_name": "HDFC Bank Ltd.", "percent_aum": 7.0},
        {"instrument_name": "Sub T otal", "percent_aum": 99.0},
        {"instrument_name": "Ramco Systems Ltd. Sub Total Nexus Select Trust REIT", "percent_aum": 5.0},
    ])

    assert [row["instrument_name"] for row in holdings] == ["HDFC Bank Ltd."]
