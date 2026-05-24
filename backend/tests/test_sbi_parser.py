from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd

from app.mf_ingestion.parsers.adapters.sbi_adapter import SBIAdapter


def test_sbi_parse_holdings_extracts_rows_and_normalizes_percent():
    frame = pd.DataFrame(
        [
            ["SBI Mutual Fund", "007", "Back to Index", None, None, None],
            ["SCHEME NAME :", "SBI ESG Exclusionary Strategy Fund", None, None, None, None],
            ["PORTFOLIO STATEMENT AS ON :", "2026-04-30 00:00:00", None, None, None, None],
            ["Name of the Instrument / Issuer", "ISIN", "Rating / Industry^", "Quantity", "Market value (Rs. in Lakhs)", "% to AUM"],
            ["EQUITY & EQUITY RELATED", None, None, None, None, None],
            ["HDFC Bank Ltd.", "INE040A01034", "Banks", 100.0, 5000.0, 0.038215],
            ["Larsen & Toubro Ltd.", "INE018A01030", "Construction", 50.0, 4000.0, 0.034323],
            ["Sub Total", None, None, None, None, 0.072538],
        ],
        columns=["c1", "c2", "c3", "c4", "c5", "c6"],
    )

    adapter = SBIAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-1", source_url="local", report_month=None),
    )

    assert parsed.scheme_name == "SBI ESG Exclusionary Strategy Fund"
    assert parsed.report_month == date(2026, 4, 1)
    assert len(parsed.holdings) == 2
    assert parsed.holdings[0]["instrument_name"] == "HDFC Bank Ltd."
    assert parsed.holdings[0]["isin"] == "INE040A01034"
    assert parsed.holdings[0]["percent_aum"] == 3.8215
    assert parsed.metrics["total_percent_aum"] == 7.2538


def test_sbi_parse_holdings_skips_summary_and_noise_rows():
    frame = pd.DataFrame(
        [
            ["SCHEME NAME :", "SBI Large and Midcap Fund", None, None, None, None],
            ["PORTFOLIO STATEMENT AS ON :", "2026-04-30", None, None, None, None],
            ["Name of the Instrument / Issuer", "ISIN", "Rating / Industry^", "Quantity", "Market value (Rs. in Lakhs)", "% to AUM"],
            ["EQUITY & EQUITY RELATED", None, None, None, None, None],
            ["ICICI Bank Ltd.", "INE090A01021", "Banks", 120.0, 6000.0, 4.25],
            ["Total", None, None, None, None, 4.25],
            ["1234", None, None, None, None, 1.0],
        ],
        columns=["c1", "c2", "c3", "c4", "c5", "c6"],
    )

    adapter = SBIAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-2", source_url="local", report_month=None),
    )

    assert parsed.scheme_name == "SBI Large and Midcap Fund"
    assert len(parsed.holdings) == 1
    assert parsed.holdings[0]["instrument_name"] == "ICICI Bank Ltd."


def test_sbi_parse_holdings_does_not_mix_repeated_scheme_sections():
    frame = pd.DataFrame(
        [
            ["SCHEME NAME :", "SBI First Fund", None, None, None, None],
            ["PORTFOLIO STATEMENT AS ON :", "2026-04-30", None, None, None, None],
            ["Name of the Instrument / Issuer", "ISIN", "Rating / Industry^", "Quantity", "Market value", "% to AUM"],
            ["HDFC Bank Ltd.", "INE040A01034", "Banks", 100.0, 5000.0, 60.0],
            ["ICICI Bank Ltd.", "INE090A01021", "Banks", 100.0, 5000.0, 40.0],
            ["SCHEME NAME :", "SBI Second Fund", None, None, None, None],
            ["PORTFOLIO STATEMENT AS ON :", "2026-04-30", None, None, None, None],
            ["Name of the Instrument / Issuer", "ISIN", "Rating / Industry^", "Quantity", "Market value", "% to AUM"],
            ["Infosys Ltd.", "INE009A01021", "IT", 100.0, 5000.0, 55.0],
            ["TCS Ltd.", "INE467B01029", "IT", 100.0, 5000.0, 45.0],
        ],
        columns=["c1", "c2", "c3", "c4", "c5", "c6"],
    )

    adapter = SBIAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-3", source_url="local", report_month=None),
    )

    assert parsed.scheme_name in {"SBI First Fund", "SBI Second Fund"}
    assert len(parsed.holdings) == 2
    assert parsed.metrics["total_percent_aum"] == 100.0
    assert "percent_aum_total_out_of_band" not in parsed.warnings
