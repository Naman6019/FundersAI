from __future__ import annotations

from io import BytesIO
import logging

import pandas as pd

logger = logging.getLogger(__name__)


class ExcelParser:
    def parse_all_sheets(self, file_path: str) -> list[pd.DataFrame]:
        workbook = pd.read_excel(file_path, sheet_name=None, engine="openpyxl")
        return self._clean_frames(workbook)

    def parse_all_sheets_from_bytes(self, file_bytes: bytes) -> list[pd.DataFrame]:
        workbook = pd.read_excel(BytesIO(file_bytes), sheet_name=None, engine="openpyxl")
        return self._clean_frames(workbook)

    def _clean_frames(self, workbook: dict[str, pd.DataFrame]) -> list[pd.DataFrame]:
        frames: list[pd.DataFrame] = []
        for _, frame in workbook.items():
            if frame is None or frame.empty:
                continue
            clean = frame.dropna(how="all")
            if clean.empty:
                continue
            frames.append(clean)
        return frames
