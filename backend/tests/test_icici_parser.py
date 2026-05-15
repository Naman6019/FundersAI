from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd

from app.mf_ingestion.parsers.adapters.icici_adapter import ICICIAdapter


def test_icici_parse_holdings_extracts_rows_from_icici_style_frame():
    frame = pd.DataFrame(
        [
            [None, "ICICI Prudential Mutual Fund", None, None, None, None, None],
            [None, "ICICI Prudential Active Momentum Fund", None, None, None, None, None],
            [None, "Portfolio as on Apr 30,2026", None, None, None, None, None],
            [None, "Company/Issuer/Instrument Name", "ISIN", "Industry/Rating", "Quantity", "Exposure/Market Value(Rs.Lakh)", "% to Nav"],
            [None, "Equity & Equity Related Instruments", None, None, None, 171086.76, 0.892009],
            [None, "HDFC Bank Ltd.", "INE040A01034", "Banks", 949800, 7329.61, 0.038215],
            [None, "Larsen & Toubro Ltd.", "INE018A01030", "Construction", 164003, 6583.08, 0.034323],
            [None, "Sub Total", None, None, None, 171086.76, 0.892009],
        ],
        columns=["Unnamed: 0", "ICICI Prudential Mutual Fund", "Unnamed: 2", "Unnamed: 3", "Unnamed: 4", "Unnamed: 5", "Unnamed: 6"],
    )
    adapter = ICICIAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-1", source_url="local", report_month=None),
    )

    assert parsed.scheme_name == "ICICI Prudential Active Momentum Fund"
    assert parsed.report_month == date(2026, 4, 1)
    assert len(parsed.holdings) == 2
    assert parsed.holdings[0]["instrument_name"] == "HDFC Bank Ltd."
    assert parsed.holdings[0]["isin"] == "INE040A01034"
    assert parsed.holdings[0]["sector"] == "Banks"
    assert parsed.holdings[0]["percent_aum"] == 3.8215
    assert parsed.metrics["total_percent_aum"] == 7.2538


def test_icici_parse_holdings_prefers_non_empty_sheet():
    derivative_frame = pd.DataFrame(
        [
            [None, "Derivative", None, None],
            [None, "Instrument", "Qty", "Value"],
            [None, "NIFTY FUT", 100, 12345],
        ],
        columns=["Unnamed: 0", "ICICI Prudential Active Momentum Fund", "Unnamed: 2", "Unnamed: 3"],
    )
    holdings_frame = pd.DataFrame(
        [
            [None, "ICICI Prudential Active Momentum Fund", None, None, None],
            [None, "Portfolio as on Apr 30,2026", None, None, None],
            [None, "Company/Issuer/Instrument Name", "ISIN", "Industry/Rating", "% to Nav"],
            [None, "HDFC Bank Ltd.", "INE040A01034", "Banks", 0.038215],
        ],
        columns=["Unnamed: 0", "ICICI Prudential Mutual Fund", "Unnamed: 2", "Unnamed: 3", "Unnamed: 4"],
    )

    adapter = ICICIAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[derivative_frame, holdings_frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-2", source_url="local", report_month=None),
    )

    assert parsed.scheme_name == "ICICI Prudential Active Momentum Fund"
    assert len(parsed.holdings) == 1
    assert parsed.holdings[0]["isin"] == "INE040A01034"
