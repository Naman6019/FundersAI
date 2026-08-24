import re
from dataclasses import replace

import pandas as pd

from app.mf_ingestion.constants import AMC_EDELWEISS
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument


class EdelweissAdapter(GenericPortfolioAdapter):
    amc_code = AMC_EDELWEISS
    scheme_markers = ("edelweiss ",)
    # The official monthly workbook stores 7.66% as 0.0766.
    fractional_percent_cells = True

    _PORTFOLIO_TITLE = re.compile(
        r"^portfolio statement of\s+(?P<scheme>.+?)\s+as on\s+.+$",
        re.IGNORECASE,
    )
    _SHEET_ID = re.compile(r"^[A-Z0-9]{4,16}$")

    def __init__(self) -> None:
        self._scheme_names_by_sheet: dict[str, str] = {}

    def prepare_excel_frames(self, frames: list[pd.DataFrame]) -> None:
        """Canonicalize short sheet IDs through the workbook's official Index tab."""
        self._scheme_names_by_sheet = {}
        index_frame = next(
            (
                frame
                for frame in frames
                if str(getattr(frame, "attrs", {}).get("sheet_name", "")).strip().lower() == "index"
            ),
            None,
        )
        if index_frame is None:
            return

        rows = index_frame.where(pd.notna(index_frame), None).values.tolist()
        for row in rows:
            if len(row) < 2:
                continue
            sheet_id = " ".join(str(row[0] or "").split()).upper()
            scheme_name = " ".join(str(row[1] or "").split())
            if self._SHEET_ID.fullmatch(sheet_id) and len(scheme_name) >= 5:
                self._scheme_names_by_sheet[sheet_id] = scheme_name

    def parse_excel_frame_many(self, frame: pd.DataFrame, context: ParseContext) -> list[ParsedDocument]:
        records = super().parse_excel_frame_many(frame, context)
        sheet_id = str(getattr(frame, "attrs", {}).get("sheet_name", "")).strip().upper()
        scheme_name = self._scheme_names_by_sheet.get(sheet_id)
        if not scheme_name:
            return records
        return [replace(record, scheme_name=scheme_name) for record in records]

    def _find_scheme_name(self, rows: list[list[object]]) -> str:
        """Use the workbook's title row, including Bharat Bond scheme sheets.

        Edelweiss owns schemes whose titles do not contain the word "Edelweiss"
        (for example, BHARAT Bond ETFs), so the generic name-marker check would
        otherwise drop otherwise-valid complete holdings sheets.
        """
        for row in rows:
            for cell in row:
                match = self._PORTFOLIO_TITLE.match(" ".join(str(cell or "").split()))
                if match:
                    return " ".join(match.group("scheme").split())
        return super()._find_scheme_name(rows)
