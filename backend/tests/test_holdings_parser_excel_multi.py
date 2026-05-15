from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument
from app.mf_ingestion.parsers.holdings_parser import HoldingsParser


class _MultiSheetAdapter(BaseAMCAdapter):
    amc_code = "TEST"

    def parse_holdings(self, excel_frames, pdf_table_frames, pdf_text, context):
        frame = excel_frames[0] if excel_frames else None
        if frame is None:
            return ParsedDocument(scheme_name="", report_month=context.report_month, holdings=[], confidence_score=0.0)
        marker = str(frame.columns[0] or "") if len(frame.columns) > 0 else ""
        if not marker and not frame.empty:
            marker = str(frame.iloc[0, 0] or "")
        if marker == "SCHEME_A":
            return ParsedDocument(
                scheme_name="Scheme A",
                report_month=context.report_month,
                holdings=[{"instrument_name": "AAA", "isin": "INE000A00001", "percent_aum": 50.0}],
                confidence_score=90.0,
            )
        if marker == "SCHEME_B":
            return ParsedDocument(
                scheme_name="Scheme B",
                report_month=context.report_month,
                holdings=[{"instrument_name": "BBB", "isin": "INE000B00002", "percent_aum": 60.0}],
                confidence_score=90.0,
            )
        return ParsedDocument(scheme_name="", report_month=context.report_month, holdings=[], confidence_score=0.0)


def test_holdings_parser_returns_multiple_schemes_for_multi_sheet_excel(tmp_path: Path):
    file_path = tmp_path / "multi_sheet.xlsx"
    with pd.ExcelWriter(file_path) as writer:
        pd.DataFrame([["SCHEME_A"], ["ROW_A"]]).to_excel(writer, sheet_name="A", index=False, header=False)
        pd.DataFrame([["SCHEME_B"], ["ROW_B"]]).to_excel(writer, sheet_name="B", index=False, header=False)

    parser = HoldingsParser(_MultiSheetAdapter())
    parsed = parser.parse_many(
        str(file_path),
        ParseContext(source_document_id="doc", source_url="local", report_month=date(2026, 4, 1)),
    )
    names = sorted(item.scheme_name for item in parsed)
    assert names == ["Scheme A", "Scheme B"]
