from __future__ import annotations

from io import BytesIO
import logging
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)


class ExcelParser:
    def parse_all_sheets(self, file_path: str) -> list[pd.DataFrame]:
        extension = Path(file_path).suffix.lower()
        workbook = self._read_workbook(file_path, extension=extension)
        return self._clean_frames(workbook)

    def parse_all_sheets_from_bytes(self, file_bytes: bytes) -> list[pd.DataFrame]:
        workbook = self._read_workbook(BytesIO(file_bytes), extension="")
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

    def _read_workbook(self, source, extension: str) -> dict[str, pd.DataFrame]:
        errors: list[str] = []
        engines = ["openpyxl"]
        if extension == ".xls":
            engines.extend(["xlrd", None])
        elif extension in {"", ".xlsx", ".xlsm"}:
            engines.append(None)

        tried: set[str] = set()
        for engine in engines:
            key = str(engine)
            if key in tried:
                continue
            tried.add(key)
            try:
                return pd.read_excel(source, sheet_name=None, engine=engine)
            except Exception as exc:
                errors.append(f"{engine}: {exc}")
                if isinstance(source, BytesIO):
                    source.seek(0)
                continue

        raise RuntimeError(f"excel_read_failed ({'; '.join(errors)})")
