from datetime import date

import pandas as pd

from app.mf_ingestion.parsers.adapters.motilal_adapter import _parse_motilal_frame
from app.mf_ingestion.parsers.base_parser import ParseContext


def test_motilal_arbitrage_fixture_counts_negative_derivative_exposure_in_total() -> None:
    frame = pd.DataFrame(
        [
            ["Motilal Oswal Arbitrage Fund", None, None, None],
            ["as on June 30, 2026", None, None, None],
            ["Name of the Instrument", "ISIN", "Industry", "% to Net Assets"],
            ["Equity Basket", "INE000A01001", "Banks", 100.0],
            ["Net Receivables / (Payables)", None, None, 68.91],
            ["NIFTY Futures", None, "Derivatives", -68.91],
        ]
    )
    context = ParseContext(
        source_document_id="motilal-arbitrage-june-fixture",
        source_url="https://www.motilaloswalmf.com/official.xlsx",
        report_month=date(2026, 6, 1),
    )

    parsed = _parse_motilal_frame(frame, context)

    assert parsed is not None
    assert parsed["metrics"]["total_percent_aum"] == 100.0
    assert "percent_aum_total_out_of_band" not in parsed["warnings"]
    assert all(row["percent_aum"] > 0 for row in parsed["holdings"])
