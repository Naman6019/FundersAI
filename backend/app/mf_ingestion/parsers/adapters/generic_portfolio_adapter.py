from __future__ import annotations

import math
import re
from datetime import date
from typing import Any

import pandas as pd

from app.mf_ingestion.normalizers.column_normalizer import normalize_column_name
from app.mf_ingestion.normalizers.instrument_normalizer import normalize_instrument_name
from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument

DATE_PATTERN = re.compile(
    r"\b(?:as\s+(?:on|of)\s+)?(?P<day>\d{1,2})?[\s,./-]*"
    r"(?P<month>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"[\s,./-]+(?P<year>20\d{2})\b",
    re.IGNORECASE,
)
ISIN_PATTERN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")
# No "treps" entry here (unlike some AMC-specific adapters): rows without their own
# percent_aum are already dropped upstream, so a bare "TREPS" header row never reaches
# this filter. In this shared table format "TREPS / Reverse Repo Investments" is the
# terminal instrument-level row carrying the real percentage for money-market/overnight
# schemes -- blocking it drops their dominant (often only) holding. Its duplicate
# "Total" subtotal row is still excluded by the "total" marker below.
SUMMARY_MARKERS = (
    "grand total",
    "sub total",
    "subtotal",
    "total",
    "equity and equity related",
    "equity & equity related",
    "debt instruments",
    "money market instruments",
    "cash and cash equivalents",
    "mutual fund units",
)


class GenericPortfolioAdapter(BaseAMCAdapter):
    """Shared deterministic table parser; AMC subclasses only declare name markers."""

    amc_code = ""
    scheme_markers: tuple[str, ...] = ()
    fractional_percent_cells = False

    def parse_excel_frame_many(self, frame: pd.DataFrame, context: ParseContext) -> list[ParsedDocument]:
        return self._parse_frame_many(frame, context)

    def parse_pdf_frame_many(self, frame: pd.DataFrame, context: ParseContext) -> list[ParsedDocument]:
        return self._parse_frame_many(frame, context)

    def parse_holdings(
        self,
        excel_frames: list[pd.DataFrame],
        pdf_table_frames: list[pd.DataFrame],
        pdf_text: str,
        context: ParseContext,
    ) -> ParsedDocument:
        parsed = [
            record
            for frame in [*excel_frames, *pdf_table_frames]
            for record in self._parse_frame_many(frame, context)
        ]
        if not parsed:
            return ParsedDocument(
                scheme_name="",
                report_month=context.report_month,
                holdings=[],
                warnings=[f"{self.amc_code}_holdings_not_found_in_document"],
                confidence_score=0.0,
            )
        return max(parsed, key=lambda record: len(record.holdings))

    def _parse_frame_many(self, frame: pd.DataFrame, context: ParseContext) -> list[ParsedDocument]:
        if frame is None or frame.empty:
            return []
        rows = frame.where(pd.notna(frame), None).values.tolist()
        headers = _find_headers(rows)
        if not headers:
            return []

        report_month = context.report_month or _find_report_month(
            [list(frame.columns), *rows]
        )
        records: list[ParsedDocument] = []
        for header_position, (header_index, columns) in enumerate(headers):
            next_header = headers[header_position + 1][0] if header_position + 1 < len(headers) else len(rows)
            grand_total_index = _find_grand_total_row(rows, header_index + 1, next_header)
            if grand_total_index is not None:
                next_header = min(next_header, grand_total_index + 1)
            preceding_start = headers[header_position - 1][0] + 1 if header_position else 0
            page_text_head = getattr(frame, "attrs", {}).get("page_text_head") or ""
            extra_context = [[line] for line in str(page_text_head).splitlines() if line.strip()]
            scheme_context_rows = [
                list(frame.columns),
                *extra_context,
                *rows[max(preceding_start, header_index - 15):header_index],
            ]
            scheme_name = self._find_scheme_name(scheme_context_rows)
            if not scheme_name:
                continue
            record_report_month = (
                _find_explicit_report_month(
                    [[scheme_name], *scheme_context_rows]
                )
                or report_month
            )
            holdings = _extract_rows(rows[header_index + 1:next_header], columns)
            if not holdings:
                continue
            if self.fractional_percent_cells:
                holdings = _normalize_fractional_percent_cells(holdings)
            total_percent = round(sum(float(row["percent_aum"]) for row in holdings), 6)
            warnings: list[str] = []
            if record_report_month is None:
                warnings.append("report_month_not_detected")
            if not 85.0 <= total_percent <= 115.0:
                warnings.append("percent_aum_total_out_of_band")
            records.append(
                ParsedDocument(
                    scheme_name=scheme_name,
                    report_month=record_report_month,
                    holdings=holdings,
                    metrics={"total_percent_aum": total_percent},
                    warnings=warnings,
                    confidence_score=_confidence(
                        holdings,
                        record_report_month,
                        total_percent,
                    ),
                )
            )
        return records

    def _find_scheme_name(self, rows: list[list[object]]) -> str:
        for row in reversed(rows):
            for cell in row:
                text = _clean(cell)
                low = text.lower()
                if not text or not any(marker in low for marker in self.scheme_markers):
                    continue
                if len(text) > 180:
                    continue
                if not any(token in low for token in ("fund", "fof", "etf", "plan")):
                    continue
                if re.match(r"^(?:grand\s+|sub\s*)?total\s*:", low):
                    continue
                if any(
                    token in low
                    for token in (
                        "asset management",
                        "mutual fund portfolio",
                        "monthly portfolio",
                        "master circular",
                        "pursuant to",
                        "securities in case of which",
                    )
                ):
                    continue
                return re.sub(r"\s+\([^)]{1,180}\)\s*$", "", text).strip()
        return ""


# Some portfolio disclosures carry a second, unrelated table further down the sheet
# (e.g. historical distribution/default disclosures) whose long, sentence-length column
# header incidentally contains a substring like "...as % to NAV)..." deep inside legal
# boilerplate. Without a length cap that row is misdetected as a second holdings header,
# and everything after it (including the NAV-per-unit table) gets parsed as bogus
# holdings for the same scheme, inflating its total well past 100%. Real column headers
# are always short, so cap substring matches to a plausible header length.
_HEADER_CELL_MAX_LEN = 40


def _find_headers(rows: list[list[object]]) -> list[tuple[int, dict[str, int]]]:
    headers: list[tuple[int, dict[str, int]]] = []
    for index, row in enumerate(rows):
        normalized = [normalize_column_name(cell) for cell in row]
        lowered = [_clean(cell).lower() for cell in row]
        instrument = _find_column(
            normalized,
            lowered,
            lambda norm, low: norm == "instrument_name"
            or (
                len(low) <= _HEADER_CELL_MAX_LEN
                and (
                    "name of the instrument" in low
                    or "name of instrument" in low
                    or "security name" in low
                    or "company name" in low
                    or "company" in low
                    or "scrip" in low
                    or "issuer" in low
                )
            ),
        )
        percent = _find_column(
            normalized,
            lowered,
            lambda norm, low: norm == "percent_aum"
            or (
                len(low) <= _HEADER_CELL_MAX_LEN
                and (
                    "% to nav" in low
                    or "% of nav" in low
                    or "% to net assets" in low
                    or "allocation" in low
                    or "weightage" in low
                )
            ),
        )
        if instrument is None or percent is None:
            continue
        headers.append(
            (
                index,
                {
                    "instrument": instrument,
                    "percent": percent,
                    "isin": _find_column(normalized, lowered, lambda norm, low: norm == "isin" or low == "isin"),
                    "sector": _find_column(
                        normalized,
                        lowered,
                        lambda norm, low: norm == "sector" or "industry" in low or "rating" in low,
                    ),
                },
            )
        )
    return headers


def _find_grand_total_row(rows: list[list[object]], start: int, end: int) -> int | None:
    """Bounds a holdings table at its closing "Grand Total" row so trailing,
    unrelated tables further down the same sheet (NAV-per-unit history, historical
    distribution disclosures, riskometer notes) never get swept into this scheme's
    holdings just because no other header appears before the end of the sheet."""
    for index in range(start, min(end, len(rows))):
        for cell in rows[index]:
            if _clean(cell).lower().startswith("grand total"):
                return index
    return None


def _extract_rows(rows: list[list[object]], columns: dict[str, int]) -> list[dict[str, Any]]:
    holdings: dict[str, dict[str, Any]] = {}
    for row in rows:
        percent = _number(_get(row, columns.get("percent")))
        name = normalize_instrument_name(_get(row, columns.get("instrument")))
        if percent is None or not 0 < percent <= 100 or not name:
            continue
        low = " ".join(name.lower().split())
        if any(marker == low or low.startswith(f"{marker} ") for marker in SUMMARY_MARKERS):
            continue
        isin_text = _clean(_get(row, columns.get("isin"))).upper()
        isin = isin_text if ISIN_PATTERN.fullmatch(isin_text) else None
        sector = normalize_instrument_name(_get(row, columns.get("sector"))) or None
        item = {
            "instrument_name": name,
            "isin": isin,
            "sector": sector,
            "percent_aum": round(percent, 6),
            "quantity": None,
            "market_value": None,
        }
        key = isin or re.sub(r"[^a-z0-9]+", " ", low).strip()
        previous = holdings.get(key)
        if not previous or float(item["percent_aum"]) > float(previous["percent_aum"]):
            holdings[key] = item
    return list(holdings.values())


def _normalize_fractional_percent_cells(
    holdings: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    total = sum(float(row.get("percent_aum") or 0.0) for row in holdings)
    if not holdings or not 0 < total <= 2.0:
        return holdings
    return [
        {
            **row,
            "percent_aum": round(float(row.get("percent_aum") or 0.0) * 100.0, 6),
        }
        for row in holdings
    ]


def _find_report_month(rows: list[list[object]]) -> date | None:
    months = {
        "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
        "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
    }
    for row in rows[:20]:
        for cell in row:
            match = DATE_PATTERN.search(_clean(cell))
            if match:
                return date(int(match.group("year")), months[match.group("month").lower()[:3]], 1)
    return None


def _find_explicit_report_month(rows: list[list[object]]) -> date | None:
    for row in rows:
        for cell in row:
            text = _clean(cell)
            if not re.search(r"\bas\s+(?:on|of)\b", text, re.IGNORECASE):
                continue
            match = DATE_PATTERN.search(text)
            if match:
                return _date_from_match(match)
    return None


def _date_from_match(match: re.Match[str]) -> date:
    months = {
        "jan": 1,
        "feb": 2,
        "mar": 3,
        "apr": 4,
        "may": 5,
        "jun": 6,
        "jul": 7,
        "aug": 8,
        "sep": 9,
        "oct": 10,
        "nov": 11,
        "dec": 12,
    }
    return date(
        int(match.group("year")),
        months[match.group("month").lower()[:3]],
        1,
    )


def _find_column(normalized: list[str], lowered: list[str], predicate: Any) -> int | None:
    return next((index for index, pair in enumerate(zip(normalized, lowered)) if predicate(*pair)), None)


def _get(row: list[object], index: int | None) -> object:
    return row[index] if index is not None and 0 <= index < len(row) else None


def _clean(value: object) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


def _number(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text or text.lower() in {"na", "n/a", "nan", "-", "--"}:
        return None
    try:
        result = float(text)
        return result if math.isfinite(result) else None
    except ValueError:
        return None


def _confidence(holdings: list[dict[str, Any]], report_month: date | None, total_percent: float) -> float:
    score = 55.0 + min(25.0, len(holdings) * 0.5)
    if report_month:
        score += 10.0
    if 85.0 <= total_percent <= 115.0:
        score += 10.0
    return round(min(score, 99.0), 2)
