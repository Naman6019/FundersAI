from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pandas as pd

from app.mf_ingestion.parsers.adapters.dsp_adapter import DSPAdapter


def test_dsp_overnight_fund_keeps_treps_as_the_dominant_holding():
    """Regression for DSP Overnight Fund / BSE Liquid Rate ETF / Nifty 1D Rate Liquid
    ETF coming up with near-zero holdings coverage: GenericPortfolioAdapter's
    SUMMARY_MARKERS used to blocklist any row starting with "treps", but for this
    table format "TREPS / Reverse Repo Investments" isn't a section header -- it's the
    terminal, percent-bearing instrument row representing the fund's actual
    money-market exposure (often ~99% of a liquid/overnight scheme). Verified against
    the real DSP ISIN DEBT Portfolio workbook's OVERNIGHT sheet (as on 30 Jun 2026)."""
    frame = pd.DataFrame(
        [
            [None, "DSP Overnight Fund", None, None, None, None, None, None, None, None],
            [None, "Portfolio as on June 30, 2026", None, None, None, None, None, None, None, None],
            [
                "Sr. No.", "Name of Instrument", "ISIN", "Rating/Industry", "Quantity",
                "Market value (Rs. In lakhs)", "% to Net Assets", "Maturity Date", "Put/Call Option", "YTM (%)",
            ],
            [None, "MONEY MARKET INSTRUMENTS", None, None, None, None, None, None, None, None],
            [None, "Certificate of Deposit", None, None, None, None, None, None, None, None],
            [1, "Canara Bank", "INE476A16I75", "CRISIL A1+", 6000, 30000, 0.0931, None, None, 5.5104],
            [2, "Indian Bank", "INE562A16QV1", "CRISIL A1+", 5000, 25000, 0.0776, None, None, 5.7515],
            [None, "Total", None, None, None, 55000, 0.1707, None, None, None],
            [None, "Treasury Bill", None, None, None, None, None, None, None, None],
            [3, "91 DAYS T-BILL 2026", "IN002026X016", "Sovereign", 5500000, 5493.77, 0.017, None, None, 5.1706],
            [None, "Total", None, None, None, 5493.77, 0.017, None, None, None],
            [8, "TREPS / Reverse Repo Investments", None, None, None, 254485.08, 0.7898, None, None, None],
            [None, "Total", None, None, None, 254485.08, 0.7898, None, None, None],
            [None, "Cash & Cash Equivalent", None, None, None, None, None, None, None, None],
            [None, "Net Receivables/Payables", None, None, None, -6730.88, -0.0208, None, None, None],
            [None, "Total", None, None, None, -6730.88, -0.0208, None, None, None],
            [None, "GRAND TOTAL", None, None, None, 322217.89, 1.0, None, None, None],
        ]
    )

    adapter = DSPAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-dsp-overnight", source_url="local", report_month=date(2026, 6, 1)),
    )

    names = {row["instrument_name"] for row in parsed.holdings}
    assert "TREPS / Reverse Repo Investments" in names
    assert "Total" not in names

    treps_row = next(row for row in parsed.holdings if row["instrument_name"] == "TREPS / Reverse Repo Investments")
    assert treps_row["percent_aum"] == 78.98

    assert "percent_aum_total_out_of_band" not in parsed.warnings
