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


def test_dsp_bond_fund_ignores_trailing_disclosure_and_nav_tables():
    """Regression: DSP Bond Fund's holdings total came up as 322% instead of ~100%.
    Root cause had two parts, both from a trailing "historical distribution disclosure"
    table further down the same sheet (unrelated to the holdings table): (1) its long,
    sentence-length column header incidentally contains the substring "...as % to NAV)..."
    deep inside legal boilerplate, which without a length cap on the header-detection
    heuristic gets misdetected as a second holdings-table header -- and everything below
    it, including a NAV-per-unit-value table, then gets parsed as bogus holdings for the
    same scheme; (2) even once that false header is rejected, the disclosure table's own
    data row (a "% to NAV"-shaped amount that isn't really a percentage) still falls
    within the unbounded scan range after the real header, since nothing marked where the
    real holdings table ends. Verified against the real DSP ISIN DEBT Portfolio
    workbook's BOND sheet (as on 30 Jun 2026)."""
    frame = pd.DataFrame(
        [
            [None, "DSP Bond Fund", None, None, None, None, None, None, None, None],
            [None, "Portfolio as on June 30, 2026", None, None, None, None, None, None, None, None],
            [
                "Sr. No.", "Name of Instrument", "ISIN", "Rating/Industry", "Quantity",
                "Market value (Rs. In lakhs)", "% to Net Assets", "Maturity Date", "Put/Call Option", "YTM (%)",
            ],
            [1, "6.36% GOI 2031", "IN0020250141", "Sovereign", 3500000, 3574.92, 55.0, None, None, 6.4195],
            [None, "Total", None, None, None, 3574.92, 55.0, None, None, None],
            [2, "TREPS / Reverse Repo Investments", None, None, None, 359.62, 45.0, None, None, None],
            [None, "Total", None, None, None, 359.62, 45.0, None, None, None],
            [None, "GRAND TOTAL", None, None, None, 3934.54, 100.0, None, None, None],
            ["Notes:", None, None, None, None, None, None, None, None, None],
            [
                None, "Security Name", "ISIN",
                "value of the security considered under net receivables (i.e. value recognized in NAV in absolute terms and as % to NAV)\n(Rs.in lakhs)",
                None, "total amount due to the scheme on that investment\n(Rs.in lakhs)", None, None, None, None,
            ],
            [
                None, "0% Il&Fs Transportation Networks Limited NCD Series A 23032019", "INE975G08140",
                0, 0, 1325.56, 82.70049, None, 146.67, None,
            ],
            [None, "Plan/Option Name", "NAV per unit (Rs)", None, "Aggregate distributions (Rs. per Unit)", None, None, None, None, None],
            [None, "Direct Plan-Growth Plan", "90.0894", "91.9083", "-", None, None, None, None, None],
        ]
    )

    adapter = DSPAdapter()
    parsed = adapter.parse_holdings(
        excel_frames=[frame],
        pdf_table_frames=[],
        pdf_text="",
        context=SimpleNamespace(source_document_id="doc-dsp-bond", source_url="local", report_month=date(2026, 6, 1)),
    )

    names = {row["instrument_name"] for row in parsed.holdings}
    assert names == {"6.36% GOI 2031", "TREPS / Reverse Repo Investments"}
    assert parsed.metrics["total_percent_aum"] == 100.0
    assert "percent_aum_total_out_of_band" not in parsed.warnings
