from __future__ import annotations

import pandas as pd

from app.mf_ingestion.parsers.adapters.angel_one_adapter import AngelOneAdapter
from app.mf_ingestion.parsers.adapters.capitalmind_adapter import CapitalmindAdapter
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext

CONTEXT = ParseContext(source_document_id="doc", source_url="local", report_month=None)


def _frame(rows: list[list[object]]) -> pd.DataFrame:
    frame = pd.DataFrame(rows[1:], columns=rows[0])
    return frame


def test_angel_one_closed_up_house_name_is_recognised_as_a_scheme():
    """Angel One's workbooks spell the house name closed up ("AngelOne Nifty 1D
    Rate Liquid ETF"), which matched neither "angel one " nor "angel ", so
    _find_scheme_name returned nothing and the entire portfolio parsed to zero
    holdings against the real August 2026 disclosure."""
    frame = _frame(
        [
            ["AngelOne Nifty 1D Rate Liquid ETF GROWTH", None, None],
            ["Portfolio as on 31-JUL-2026", None, None],
            ["Name of Instrument", "Market Value (In Rs. lakh)", "% To Net Assets"],
            ["Clearing Corporation of India Ltd", 30353.729513, 0.999677],
            ["Net Current Assets", 9.807331, 0.000323],
        ]
    )

    records = AngelOneAdapter().parse_excel_frame_many(frame, CONTEXT)

    assert len(records) == 1
    assert records[0].scheme_name.startswith("AngelOne")
    assert len(records[0].holdings) == 2


def test_angel_one_fraction_of_one_percentages_are_scaled_to_percent():
    """"% To Net Assets" is published as a fraction of 1, so the two holdings sum
    to 1.0 in the source and must stage as 100%, not as 1%."""
    frame = _frame(
        [
            ["AngelOne Nifty 1D Rate Liquid ETF GROWTH", None, None],
            ["Name of Instrument", "Market Value (In Rs. lakh)", "% To Net Assets"],
            ["Clearing Corporation of India Ltd", 30353.729513, 0.999677],
            ["Net Current Assets", 9.807331, 0.000323],
        ]
    )

    records = AngelOneAdapter().parse_excel_frame_many(frame, CONTEXT)

    total = sum(row["percent_aum"] for row in records[0].holdings)
    assert round(total, 3) == 100.0


def test_capitalmind_percent_to_nav_is_a_fraction_of_one():
    """Capitalmind prints "% to NAV" as a fraction (0.1018 means 10.18%). Left
    unscaled the whole Liquid Fund staged at ~1% of AUM."""
    frame = _frame(
        [
            ["Capitalmind Liquid Fund", None, None],
            ["Name of the Instrument / Issuer", "ISIN", "% to NAV"],
            ["6.97% Government of India (06/09/2026)", "IN0020160035", 0.1018],
            ["7.95% Sikka Ports and Terminals Limited", "INE941D07158", 0.0764],
            ["Clearing Corporation of India Ltd", None, 0.4239],
        ]
    )

    records = CapitalmindAdapter().parse_excel_frame_many(frame, CONTEXT)

    total = sum(row["percent_aum"] for row in records[0].holdings)
    assert 50.0 < total < 70.0, f"expected percent-scale values, got {total}"


def test_generic_adapter_offers_the_combined_factsheet_text_parse():
    """Multi-scheme factsheets lay holdings out as text under a per-scheme heading,
    which the pdfplumber table path cannot see -- it returned zero holdings for 21
    of the 22 factsheets in R2. Every marker-declaring adapter must therefore offer
    the text parse, not just the four AMCs that hand-rolled their own override."""
    adapter = AngelOneAdapter()
    assert callable(getattr(adapter, "parse_pdf_file_many", None))
    assert adapter.combined_factsheet_text_parse is True


def test_marker_less_adapter_does_not_attempt_the_text_parse():
    """scheme_prefixes drive scheme detection, so an adapter with no markers would
    match every line; it must decline instead of returning junk."""

    class Bare(GenericPortfolioAdapter):
        amc_code = "BARE"

    assert Bare().parse_pdf_file_many("does-not-exist.pdf", CONTEXT) == []
