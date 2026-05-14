from __future__ import annotations

import pandas as pd

from app.mf_ingestion.constants import AMC_SBI
from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument


class SBIAdapter(BaseAMCAdapter):
    amc_code = AMC_SBI

    def parse_holdings(self, excel_frames: list[pd.DataFrame], pdf_table_frames: list[pd.DataFrame], pdf_text: str, context: ParseContext) -> ParsedDocument:
        return ParsedDocument(
            scheme_name="",
            report_month=context.report_month,
            holdings=[],
            warnings=["TODO: implement SBI adapter"],
            confidence_score=0.0,
        )
