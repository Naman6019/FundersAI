from __future__ import annotations

import logging
import zipfile
from pathlib import Path

from app.mf_ingestion.constants import EXCEL_EXTENSIONS
from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument
from app.mf_ingestion.parsers.excel_parser import ExcelParser
from app.mf_ingestion.parsers.pdf_table_parser import PDFTableParser
from app.mf_ingestion.parsers.pdf_text_parser import PDFTextParser

logger = logging.getLogger(__name__)
ZIP_MAX_EXCEL_FILES = 2000


class HoldingsParser:
    def __init__(self, adapter: BaseAMCAdapter) -> None:
        self.adapter = adapter
        self.excel_parser = ExcelParser()
        self.pdf_table_parser = PDFTableParser()
        self.pdf_text_parser = PDFTextParser()

    def parse(self, file_path: str, context: ParseContext) -> ParsedDocument:
        parsed_documents = self.parse_many(file_path, context)
        if not parsed_documents:
            return ParsedDocument(
                scheme_name="",
                report_month=context.report_month,
                holdings=[],
                warnings=["holdings_not_found_in_document"],
                confidence_score=0.0,
            )
        return max(parsed_documents, key=lambda item: len(item.holdings))

    def parse_many(self, file_path: str, context: ParseContext) -> list[ParsedDocument]:
        extension = Path(file_path).suffix.lower()

        if extension in EXCEL_EXTENSIONS:
            frames = self.excel_parser.parse_all_sheets(file_path)
            return self._parse_excel_frames(frames, context)

        if extension == ".zip":
            return self._parse_zip_documents(file_path, context)

        pdf_frames = self.pdf_table_parser.extract_tables(file_path)
        pdf_text = ""
        if not pdf_frames:
            pdf_text = self.pdf_text_parser.extract_text(file_path)
        parsed = self.adapter.parse_holdings([], pdf_frames, pdf_text, context)
        return [parsed] if parsed.holdings else []

    def _parse_excel_frames(self, frames: list, context: ParseContext) -> list[ParsedDocument]:
        if not frames:
            return []

        by_scheme: dict[str, ParsedDocument] = {}
        for frame in frames:
            try:
                parsed = self.adapter.parse_holdings([frame], [], "", context)
            except Exception:
                logger.exception("event=excel_sheet_parse_failed source_document_id=%s", context.source_document_id)
                continue
            if not parsed.holdings:
                continue

            scheme_key = " ".join(str(parsed.scheme_name or "").lower().split())
            existing = by_scheme.get(scheme_key)
            if not existing or len(parsed.holdings) > len(existing.holdings):
                by_scheme[scheme_key] = parsed

        return list(by_scheme.values())

    def _parse_zip_documents(self, file_path: str, context: ParseContext) -> list[ParsedDocument]:
        parsed_documents: list[ParsedDocument] = []
        by_scheme: dict[str, ParsedDocument] = {}
        with zipfile.ZipFile(file_path) as archive:
            names = sorted(archive.namelist())
            excel_names = [name for name in names if Path(name).suffix.lower() in EXCEL_EXTENSIONS]
            for index, member_name in enumerate(excel_names):
                if index >= ZIP_MAX_EXCEL_FILES:
                    logger.info(
                        "event=zip_excel_limit_reached file_path=%s excel_entries=%s processed=%s",
                        file_path,
                        len(excel_names),
                        ZIP_MAX_EXCEL_FILES,
                    )
                    break
                try:
                    member_bytes = archive.read(member_name)
                    member_frames = self.excel_parser.parse_all_sheets_from_bytes(member_bytes)
                    for parsed in self._parse_excel_frames(member_frames, context):
                        scheme_key = " ".join(str(parsed.scheme_name or "").lower().split())
                        existing = by_scheme.get(scheme_key)
                        if not existing or len(parsed.holdings) > len(existing.holdings):
                            by_scheme[scheme_key] = parsed
                except Exception:
                    logger.exception("event=zip_excel_member_parse_failed file_path=%s member=%s", file_path, member_name)
                    continue
        parsed_documents.extend(by_scheme.values())
        return parsed_documents
