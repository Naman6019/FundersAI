from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument


class BaseAMCAdapter(ABC):
    amc_code: str

    @abstractmethod
    def parse_holdings(
        self,
        excel_frames: list[pd.DataFrame],
        pdf_table_frames: list[pd.DataFrame],
        pdf_text: str,
        context: ParseContext,
    ) -> ParsedDocument:
        raise NotImplementedError
