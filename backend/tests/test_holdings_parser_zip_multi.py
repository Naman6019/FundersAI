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


def test_zip_corrupt_member_preserves_valid_records_and_diagnostic(tmp_path: Path):
    zip_path = tmp_path / "partial.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("good.xlsx", b"A")
        archive.writestr("bad.xlsx", b"BROKEN")

    parser = HoldingsParser(_FakeAdapter())

    def _parse(raw: bytes):
        if raw == b"BROKEN":
            raise ValueError("corrupt workbook")
        return [pd.DataFrame([[raw.decode("ascii")]])]

    parser.excel_parser.parse_all_sheets_from_bytes = _parse
    result = parser.parse_batch(
        str(zip_path),
        ParseContext(source_document_id="doc-partial", source_url="local", report_month=None),
    )

    assert [record.scheme_name for record in result.records] == ["Scheme A"]
    assert result.successful_sources == 1
    assert result.failed_sources == 1
    assert result.diagnostics[0].member_name == "bad.xlsx"
    assert result.diagnostics[0].code == "zip_member_parse_failed"


def test_zip_all_members_failing_has_no_records(tmp_path: Path):
    zip_path = tmp_path / "failed.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("bad-a.xlsx", b"A")
        archive.writestr("bad-b.xlsx", b"B")

    parser = HoldingsParser(_FakeAdapter())
    parser.excel_parser.parse_all_sheets_from_bytes = lambda _raw: (_ for _ in ()).throw(ValueError("corrupt"))
    result = parser.parse_batch(
        str(zip_path),
        ParseContext(source_document_id="doc-failed", source_url="local", report_month=None),
    )

    assert result.records == []
    assert result.failed_sources == 2
    assert {diagnostic.member_name for diagnostic in result.diagnostics} == {"bad-a.xlsx", "bad-b.xlsx"}


def test_nested_archive_is_rejected_with_evidence(tmp_path: Path):
    zip_path = tmp_path / "nested.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("nested.zip", b"not-a-real-zip")

    result = HoldingsParser(_FakeAdapter()).parse_batch(
        str(zip_path),
        ParseContext(source_document_id="doc-nested", source_url="local", report_month=None),
    )

    assert result.records == []
    assert result.failed_sources == 1
    assert any(item.code == "nested_archive_not_allowed" and item.member_name == "nested.zip" for item in result.diagnostics)
