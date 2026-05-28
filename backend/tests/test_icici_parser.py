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


def test_icici_total_percent_includes_non_isin_cash_rows_without_storing_them():
    frame = pd.DataFrame(
        [
            [None, "ICICI Prudential Mutual Fund", None, None, None, None, None],
            [None, "ICICI Prudential Overnight Fund", None, None, None, None, None],
            [None, "Portfolio as on Apr 30,2026", None, None, None, None, None],
            [None, "Company/Issuer/Instrument Name", "ISIN", "Industry/Rating", "Quantity", "Exposure/Market Value(Rs.Lakh)", "% to Nav"],
            [None, "91 DAY T-BILL 14.05.26", "IN002025X455", "Sovereign", 26000000, 25952.39, 0.96],
            [None, "TREPS / Reverse Repo Investments", None, None, None, None, None],
            [None, "TREPS", None, None, None, 2450601.12, 90.62],
            [None, "Reverse Repo", None, None, None, 148698.67, 5.50],
            [None, "Net Receivable / Payable", None, None, None, -731.50, -0.02],
        ],
        columns=["Unnamed: 0", "ICICI Prudential Mutual Fund", "Unnamed: 2", "Unnamed: 3", "Unnamed: 4", "Unnamed: 5", "Unnamed: 6"],
    )

    adapter = ICICIAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-3", source_url="local", report_month=None),
    )

    assert parsed.scheme_name == "ICICI Prudential Overnight Fund"
    assert len(parsed.holdings) == 1
    assert parsed.holdings[0]["instrument_name"] == "91 DAY T-BILL 14.05.26"
    assert parsed.metrics["total_percent_aum"] == 97.06
    assert "percent_aum_total_out_of_band" not in parsed.warnings


def test_icici_non_isin_category_totals_do_not_double_count_exposure():
    frame = pd.DataFrame(
        [
            [None, "ICICI Prudential Mutual Fund", None, None, None, None, None],
            [None, "ICICI Prudential Bond Fund", None, None, None, None, None],
            [None, "Portfolio as on Apr 30,2026", None, None, None, None, None],
            [None, "Company/Issuer/Instrument Name", "ISIN", "Industry/Rating", "Quantity", "Exposure/Market Value(Rs.Lakh)", "% to Nav"],
            [None, "Government Securities", None, None, None, 520983.0, 0.520983],
            [None, "Government Securities", "IN0020240035", "Sovereign", 100, 81487.0, 0.81487],
            [None, "TREPS", None, None, None, 1000.0, 0.18513],
            [None, "Total Net Assets", None, None, None, 100000.0, 1.0],
        ],
        columns=["Unnamed: 0", "ICICI Prudential Mutual Fund", "Unnamed: 2", "Unnamed: 3", "Unnamed: 4", "Unnamed: 5", "Unnamed: 6"],
    )

    adapter = ICICIAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-5", source_url="local", report_month=None),
    )

    assert len(parsed.holdings) == 1
    assert parsed.metrics["total_percent_aum"] == 100.0
    assert "percent_aum_total_out_of_band" not in parsed.warnings


def test_icici_non_isin_parent_allocation_is_dropped_when_dated_children_exist():
    frame = pd.DataFrame(
        [
            [None, "ICICI Prudential Mutual Fund", None, None, None, None, None],
            [None, "ICICI Prudential Overnight Fund", None, None, None, None, None],
            [None, "Portfolio as on Apr 30,2026", None, None, None, None, None],
            [None, "Company/Issuer/Instrument Name", "ISIN", "Industry/Rating", "Quantity", "Exposure/Market Value(Rs.Lakh)", "% to Nav"],
            [None, "91 Days Treasury Bills", "IN002025X463", "Sovereign", 100, 13594.0, 0.013594],
            [None, "Reverse Repo", None, None, None, 905744.0, 0.905744],
            [None, "Reverse Repo (5/4/2026)", None, None, None, 95327.0, 0.095327],
            [None, "Reverse Repo (5/4/2026)", None, None, None, 810417.0, 0.810417],
            [None, "TREPS", None, None, None, 39215.0, 0.039215],
            [None, "Net Current Assets", None, None, None, -5496.0, -0.005496],
        ],
        columns=["Unnamed: 0", "ICICI Prudential Mutual Fund", "Unnamed: 2", "Unnamed: 3", "Unnamed: 4", "Unnamed: 5", "Unnamed: 6"],
    )

    adapter = ICICIAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-6", source_url="local", report_month=None),
    )

    assert len(parsed.holdings) == 1
    assert parsed.metrics["total_percent_aum"] == 95.3057
    assert "percent_aum_total_out_of_band" not in parsed.warnings


def test_icici_real_sub_one_percent_rows_are_not_over_scaled():
    frame = pd.DataFrame(
        [
            [None, "ICICI Prudential Mutual Fund", None, None, None, None, None],
            [None, "ICICI Prudential Overnight Fund", None, None, None, None, None],
            [None, "Portfolio as on Apr 30,2026", None, None, None, None, None],
            [None, "Company/Issuer/Instrument Name", "ISIN", "Industry/Rating", "Quantity", "Exposure/Market Value(Rs.Lakh)", "% to Nav"],
            [None, "91 DAY T-BILL 14.05.26", "IN002025X455", "Sovereign", 26000000, 25952.39, 0.96],
            [None, "TREPS", None, None, None, 2450601.12, 90.62],
        ],
        columns=["Unnamed: 0", "ICICI Prudential Mutual Fund", "Unnamed: 2", "Unnamed: 3", "Unnamed: 4", "Unnamed: 5", "Unnamed: 6"],
    )

    adapter = ICICIAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-4", source_url="local", report_month=None),
    )

    assert parsed.holdings[0]["percent_aum"] == 0.96
    assert parsed.metrics["total_percent_aum"] == 91.58
