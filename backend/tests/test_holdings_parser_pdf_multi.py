from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument
from app.mf_ingestion.parsers.holdings_parser import HoldingsParser


class _PdfMultiAdapter(BaseAMCAdapter):
    amc_code = "TEST"

    def parse_holdings(self, excel_frames, pdf_table_frames, pdf_text, context):
        if len(pdf_table_frames) > 1:
            # Fallback path should still work when per-frame extraction returns nothing.
            return ParsedDocument(
                scheme_name="Fallback Scheme",
                report_month=context.report_month,
                holdings=[{"instrument_name": "FALLBACK", "isin": None, "percent_aum": 1.0}],
                confidence_score=80.0,
            )

        if not pdf_table_frames:
            return ParsedDocument(scheme_name="", report_month=context.report_month, holdings=[], confidence_score=0.0)

        marker = str(pdf_table_frames[0].iloc[0, 0])
        if marker == "A1":
            return ParsedDocument(
                scheme_name="Scheme A",
                report_month=context.report_month,
                holdings=[{"instrument_name": "AAA", "isin": "INE000A00001", "percent_aum": 1.0}],
                confidence_score=90.0,
            )
        if marker == "A2":
            return ParsedDocument(
                scheme_name="Scheme A",
                report_month=context.report_month,
                holdings=[
                    {"instrument_name": "AAA", "isin": "INE000A00001", "percent_aum": 1.0},
                    {"instrument_name": "AAB", "isin": "INE000A00002", "percent_aum": 2.0},
                ],
                confidence_score=90.0,
            )
        if marker == "B1":
            return ParsedDocument(
                scheme_name="Scheme B",
                report_month=context.report_month,
                holdings=[{"instrument_name": "BBB", "isin": "INE000B00002", "percent_aum": 3.0}],
                confidence_score=90.0,
            )
        return ParsedDocument(scheme_name="", report_month=context.report_month, holdings=[], confidence_score=0.0)


def test_holdings_parser_returns_multiple_schemes_for_multi_frame_pdf(tmp_path: Path):
    file_path = tmp_path / "sample.pdf"
    file_path.write_bytes(b"%PDF-1.4 test")

    parser = HoldingsParser(_PdfMultiAdapter())
    parser.pdf_table_parser.extract_tables = lambda _path: [
        pd.DataFrame([["A1"]]),
        pd.DataFrame([["A2"]]),
        pd.DataFrame([["B1"]]),
    ]

    parsed = parser.parse_many(
        str(file_path),
        ParseContext(source_document_id="doc", source_url="local", report_month=date(2026, 4, 1)),
    )
    names = sorted(item.scheme_name for item in parsed)
    assert names == ["Scheme A", "Scheme B"]
    scheme_a = next(item for item in parsed if item.scheme_name == "Scheme A")
    assert len(scheme_a.holdings) == 2


class _FallbackOnlyAdapter(_PdfMultiAdapter):
    def parse_holdings(self, excel_frames, pdf_table_frames, pdf_text, context):
        if len(pdf_table_frames) == 1:
            return ParsedDocument(scheme_name="", report_month=context.report_month, holdings=[], confidence_score=0.0)
        return super().parse_holdings(excel_frames, pdf_table_frames, pdf_text, context)


def test_holdings_parser_pdf_falls_back_to_all_frames_when_per_frame_empty(tmp_path: Path):
    file_path = tmp_path / "fallback.pdf"
    file_path.write_bytes(b"%PDF-1.4 test")

    parser = HoldingsParser(_FallbackOnlyAdapter())
    parser.pdf_table_parser.extract_tables = lambda _path: [pd.DataFrame([["A1"]]), pd.DataFrame([["B1"]])]

    parsed = parser.parse_many(
        str(file_path),
        ParseContext(source_document_id="doc-2", source_url="local", report_month=date(2026, 4, 1)),
    )
    assert len(parsed) == 1
    assert parsed[0].scheme_name == "Fallback Scheme"


class _WarningMergeAdapter(BaseAMCAdapter):
    amc_code = "TEST"

    def parse_holdings(self, excel_frames, pdf_table_frames, pdf_text, context):
        if not pdf_table_frames:
            return ParsedDocument(scheme_name="", report_month=context.report_month, holdings=[], confidence_score=0.0)
        marker = str(pdf_table_frames[0].iloc[0, 0])
        if marker == "X1":
            return ParsedDocument(
                scheme_name="Scheme X",
                report_month=None,
                holdings=[{"instrument_name": "AAA", "isin": "INE000A00001", "percent_aum": 40.0}],
                warnings=["percent_aum_total_out_of_band", "report_month_not_detected"],
                confidence_score=80.0,
            )
        if marker == "X2":
            return ParsedDocument(
                scheme_name="Scheme X",
                report_month=date(2026, 4, 1),
                holdings=[{"instrument_name": "BBB", "isin": "INE000B00001", "percent_aum": 60.0}],
                warnings=[],
                confidence_score=85.0,
            )
        return ParsedDocument(scheme_name="", report_month=context.report_month, holdings=[], confidence_score=0.0)


def test_holdings_parser_merge_recomputes_out_of_band_and_month_warnings(tmp_path: Path):
    file_path = tmp_path / "merge-warning.pdf"
    file_path.write_bytes(b"%PDF-1.4 test")

    parser = HoldingsParser(_WarningMergeAdapter())
    parser.pdf_table_parser.extract_tables = lambda _path: [pd.DataFrame([["X1"]]), pd.DataFrame([["X2"]])]

    parsed = parser.parse_many(
        str(file_path),
        ParseContext(source_document_id="doc-merge", source_url="local", report_month=None),
    )
    assert len(parsed) == 1
    scheme = parsed[0]
    assert scheme.report_month == date(2026, 4, 1)
    assert scheme.metrics["total_percent_aum"] == 100.0
    assert "percent_aum_total_out_of_band" not in (scheme.warnings or [])
    assert "report_month_not_detected" not in (scheme.warnings or [])
