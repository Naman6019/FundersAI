from __future__ import annotations

from pathlib import Path

from app.mf_ingestion.constants import EXCEL_EXTENSIONS
from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument
from app.mf_ingestion.parsers.excel_parser import ExcelParser
from app.mf_ingestion.parsers.pdf_table_parser import PDFTableParser
from app.mf_ingestion.parsers.pdf_text_parser import PDFTextParser


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
        else:
            pdf_frames = self.pdf_table_parser.extract_tables(file_path)
            if not pdf_frames:
                pdf_text = self.pdf_text_parser.extract_text(file_path)

        return self.adapter.parse_holdings(excel_frames, pdf_frames, pdf_text, context)
