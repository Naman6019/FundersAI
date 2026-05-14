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
ZIP_MAX_EXCEL_FILES = 30


class HoldingsParser:
    def __init__(self, adapter: BaseAMCAdapter) -> None:
        self.adapter = adapter
        self.excel_parser = ExcelParser()
        self.pdf_table_parser = PDFTableParser()
        self.pdf_text_parser = PDFTextParser()

    def parse(self, file_path: str, context: ParseContext) -> ParsedDocument:
        extension = Path(file_path).suffix.lower()

        excel_frames = []
        pdf_frames = []
        pdf_text = ""

        if extension in EXCEL_EXTENSIONS:
            excel_frames = self.excel_parser.parse_all_sheets(file_path)
        elif extension == ".zip":
            excel_frames = self._parse_zip_excel_frames(file_path)
        else:
            pdf_frames = self.pdf_table_parser.extract_tables(file_path)
            if not pdf_frames:
                pdf_text = self.pdf_text_parser.extract_text(file_path)

        return self.adapter.parse_holdings(excel_frames, pdf_frames, pdf_text, context)

    def _parse_zip_excel_frames(self, file_path: str) -> list:
        frames = []
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
                    frames.extend(member_frames)
                except Exception:
                    logger.exception("event=zip_excel_member_parse_failed file_path=%s member=%s", file_path, member_name)
                    continue
        return frames
