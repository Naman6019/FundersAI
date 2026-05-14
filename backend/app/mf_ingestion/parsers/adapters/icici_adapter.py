from __future__ import annotations

import re
from datetime import date, datetime

import pandas as pd

from app.mf_ingestion.constants import AMC_ICICI
from app.mf_ingestion.normalizers.column_normalizer import normalize_column_name, normalize_columns
from app.mf_ingestion.normalizers.instrument_normalizer import normalize_instrument_name
from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument

ISIN_PATTERN = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b")
MONTH_PATTERN = re.compile(
    r"portfolio\s+as\s+on\s+(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}\s*,\s*(?P<year>20\d{2})",
    re.IGNORECASE,
)
SUMMARY_ROW_MARKERS = (
    "sub total",
    "subtotal",
    "total",
    "grand total",
    "net assets",
    "equity & equity related instruments",
    "debt instruments",
    "units of mutual funds",
    "listed / awaiting listing",
    "unlisted",
    "cash and cash equivalents",
    "treps",
    "reverse repo",
)


class ICICIAdapter(BaseAMCAdapter):
    amc_code = AMC_ICICI

    def parse_holdings(
        self,
        excel_frames: list[pd.DataFrame],
        pdf_table_frames: list[pd.DataFrame],
        pdf_text: str,
        context: ParseContext,
    ) -> ParsedDocument:
        candidates: list[dict] = []
        for frame in excel_frames:
            parsed = _parse_icici_frame(frame, context)
            if parsed:
                candidates.append(parsed)

        for frame in pdf_table_frames:
            parsed = _parse_icici_frame(frame, context)
            if parsed:
                candidates.append(parsed)

        if not candidates:
            return ParsedDocument(
                scheme_name="",
                report_month=context.report_month,
                holdings=[],
                warnings=["icici_holdings_not_found_in_document"],
                confidence_score=0.0,
            )

        best = max(candidates, key=lambda item: item.get("selection_score", 0.0))
        return ParsedDocument(
            scheme_name=best.get("scheme_name") or "",
            report_month=best.get("report_month") or context.report_month,
            holdings=best.get("holdings", []),
            metrics=best.get("metrics", {}),
            warnings=best.get("warnings", []),
            confidence_score=float(best.get("confidence_score", 0.0)),
        )


def _parse_icici_frame(frame: pd.DataFrame, context: ParseContext) -> dict | None:
    if frame is None or frame.empty:
        return None

    raw_rows = frame.where(pd.notna(frame), None).values.tolist()
    if not raw_rows:
        return None

    columns = list(frame.columns)
    parsed_headers = normalize_columns(columns)
    uses_column_headers = "instrument_name" in parsed_headers and "percent_aum" in parsed_headers
    header_row_idx = -1
    if uses_column_headers:
        headers = parsed_headers
        data_rows = raw_rows
    else:
        header_row_idx, headers = _find_header_row(raw_rows)
        if header_row_idx is None:
            return None
        data_rows = raw_rows[header_row_idx + 1 :]

    scheme_name = _extract_scheme_name(columns, raw_rows)
    report_month = _detect_report_month_from_rows(raw_rows) or context.report_month
    holdings = _extract_holdings_from_rows(data_rows, headers)
    if not holdings:
        return None

    total_percent = round(sum(float(row.get("percent_aum") or 0.0) for row in holdings), 6)
    warnings: list[str] = []
    if report_month is None:
        warnings.append("report_month_not_detected")
    if not (90.0 <= total_percent <= 110.0):
        warnings.append("percent_aum_total_out_of_band")

    resolved_scheme = scheme_name or "ICICI Prudential Mutual Fund"
    confidence = _compute_confidence(holdings=holdings, report_month=report_month, total_percent=total_percent, scheme_name=resolved_scheme)
    return {
        "scheme_name": resolved_scheme,
        "report_month": report_month,
        "holdings": holdings,
        "metrics": {"total_percent_aum": total_percent},
        "warnings": warnings,
        "confidence_score": confidence,
        "selection_score": float(len(holdings)) + (20.0 if report_month else 0.0),
        "header_row_idx": header_row_idx,
    }


def _find_header_row(rows: list[list[object]]) -> tuple[int | None, list[str]]:
    for idx, row in enumerate(rows[:30]):
        headers = [normalize_column_name(cell) for cell in row]
        if "instrument_name" in headers and "percent_aum" in headers:
            return idx, headers
    return None, []


def _extract_scheme_name(columns: list[object], rows: list[list[object]]) -> str:
    primary_col = next((str(col).strip() for col in columns if str(col).strip() and "Unnamed" not in str(col)), "")
    if primary_col and primary_col.lower().startswith("icici prudential") and primary_col.lower() != "icici prudential mutual fund":
        return primary_col

    for row in rows[:8]:
        for cell in row:
            text = str(cell or "").strip()
            if not text:
                continue
            low = text.lower()
            if low.startswith("icici prudential") and "mutual fund" not in low and "portfolio as on" not in low:
                return text
    return ""


def _detect_report_month_from_rows(rows: list[list[object]]) -> date | None:
    for row in rows[:15]:
        for cell in row:
            text = str(cell or "").strip()
            if not text:
                continue
            match = MONTH_PATTERN.search(text)
            if not match:
                continue
            month = datetime.strptime(match.group("month")[:3], "%b").month
            year = int(match.group("year"))
            return date(year, month, 1)
    return None


def _extract_holdings_from_rows(rows: list[list[object]], headers: list[str]) -> list[dict]:
    holdings: list[dict] = []
    for row in rows:
        instrument_name = normalize_instrument_name(_get_row_cell(row, headers, "instrument_name"))
        if _is_summary_row(instrument_name):
            continue

        isin = _normalize_isin(_get_row_cell(row, headers, "isin"))
        if not isin:
            continue

        percent = _parse_percent(_get_row_cell(row, headers, "percent_aum"))
        if percent is None:
            continue

        quantity = _parse_number(_get_row_cell(row, headers, "quantity"))
        market_value = _parse_number(_get_row_cell(row, headers, "market_value"))
        sector = normalize_instrument_name(_get_row_cell(row, headers, "sector")) or None
        holdings.append(
            {
                "instrument_name": instrument_name,
                "isin": isin,
                "sector": sector,
                "percent_aum": percent,
                "quantity": quantity,
                "market_value": market_value,
            }
        )

    deduped: dict[str, dict] = {}
    for row in holdings:
        key = f"{str(row.get('instrument_name') or '').strip().lower()}|{str(row.get('isin') or '').strip().upper()}"
        if not key.strip("|"):
            continue
        existing = deduped.get(key)
        if not existing or float(row.get("percent_aum") or 0.0) > float(existing.get("percent_aum") or 0.0):
            deduped[key] = row
    return list(deduped.values())


def _get_row_cell(row: list[object], headers: list[str], key: str) -> object:
    for idx, header in enumerate(headers):
        if header != key:
            continue
        if idx >= len(row):
            continue
        value = row[idx]
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return value
    return None


def _parse_percent(value: object) -> float | None:
    parsed = _parse_number(value)
    if parsed is None:
        return None
    if 0 < parsed <= 1.5:
        return round(parsed * 100.0, 6)
    return round(parsed, 6)


def _parse_number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "").replace("%", "").strip()
    if text in {"-", "--", "na", "n/a", "nan"}:
        return None
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_isin(value: object) -> str | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    match = ISIN_PATTERN.search(text)
    if not match:
        return None
    return match.group(0)


def _is_summary_row(instrument_name: str) -> bool:
    low = re.sub(r"\s+", " ", str(instrument_name or "").strip().lower())
    if not low:
        return True
    return any(marker in low for marker in SUMMARY_ROW_MARKERS)


def _compute_confidence(holdings: list[dict], report_month: date | None, total_percent: float, scheme_name: str) -> float:
    if not holdings:
        return 0.0
    score = 55.0
    score += min(20.0, len(holdings) * 0.5)
    if report_month:
        score += 10.0
    if 90.0 <= total_percent <= 110.0:
        score += 10.0
    if "icici prudential" in (scheme_name or "").lower():
        score += 5.0
    return round(min(score, 99.0), 2)
