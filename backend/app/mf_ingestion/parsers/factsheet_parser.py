from __future__ import annotations

from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument


class FactsheetParser:
    def parse(self, file_path: str, context: ParseContext) -> ParsedDocument:
        # TODO: Add AMC-specific monthly metrics extraction from factsheets.
        return ParsedDocument(
            scheme_name="",
            report_month=context.report_month,
            holdings=[],
            metrics={},
            warnings=["TODO: factsheet parsing not implemented in v1"],
            confidence_score=0.0,
        )
