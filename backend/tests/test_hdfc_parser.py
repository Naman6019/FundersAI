from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd

from app.mf_ingestion.parsers.adapters.hdfc_adapter import HDFCAdapter


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
