from __future__ import annotations

import zipfile
from pathlib import Path

import pandas as pd

from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument
from app.mf_ingestion.parsers.holdings_parser import HoldingsParser


class _FakeAdapter(BaseAMCAdapter):
    amc_code = "TEST"

    def parse_holdings(self, excel_frames, pdf_table_frames, pdf_text, context):
        marker = str(excel_frames[0].iloc[0, 0]) if excel_frames else ""
        scheme = "Scheme A" if marker == "A" else "Scheme B"
        return ParsedDocument(
            scheme_name=scheme,
            report_month=context.report_month,
            holdings=[{"instrument_name": f"{scheme} Holding", "isin": f"INEXAMPLE{marker}1", "percent_aum": 1.0}],
            metrics={"total_percent_aum": 1.0},
            warnings=[],
            confidence_score=99.0,
        )


def test_holdings_parser_parse_many_reads_all_zip_excel_members(tmp_path: Path):
    zip_path = tmp_path / "sample.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("a.xlsx", b"A")
        archive.writestr("b.xlsx", b"B")

    parser = HoldingsParser(_FakeAdapter())

    def _fake_parse_all_sheets_from_bytes(raw: bytes):
        marker = raw.decode("ascii")
        return [pd.DataFrame([[marker]])]

    parser.excel_parser.parse_all_sheets_from_bytes = _fake_parse_all_sheets_from_bytes

    parsed = parser.parse_many(
        str(zip_path),
        ParseContext(source_document_id="doc-1", source_url="local", report_month=None),
    )
    scheme_names = sorted(item.scheme_name for item in parsed)
    assert scheme_names == ["Scheme A", "Scheme B"]
