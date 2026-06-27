from __future__ import annotations

import re
import math
from datetime import date, datetime

import pandas as pd

from app.mf_ingestion.constants import AMC_SBI
from app.mf_ingestion.normalizers.column_normalizer import normalize_column_name
from app.mf_ingestion.normalizers.instrument_normalizer import normalize_instrument_name
from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument

ISIN_PATTERN = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b")
SUMMARY_ROW_MARKERS = (
    "sub total",
    "subtotal",
    "total",
    "grand total",
    "net assets",
    "equity & equity related",
    "debt instruments",
    "mutual fund units",
)


class SBIAdapter(BaseAMCAdapter):
    amc_code = AMC_SBI

    def parse_excel_frame_many(self, frame: pd.DataFrame, context: ParseContext) -> list[ParsedDocument]:
        return [_to_parsed_document(item, context) for item in _parse_sbi_frame_many(frame, context)]

    def parse_pdf_frame_many(self, frame: pd.DataFrame, context: ParseContext) -> list[ParsedDocument]:
        return self.parse_excel_frame_many(frame, context)

    def parse_holdings(
        self,
        excel_frames: list[pd.DataFrame],
        pdf_table_frames: list[pd.DataFrame],
        pdf_text: str,
        context: ParseContext,
    ) -> ParsedDocument:
        candidates: list[dict] = []
        for frame in excel_frames:
            candidates.extend(_parse_sbi_frame_many(frame, context))

        for frame in pdf_table_frames:
            candidates.extend(_parse_sbi_frame_many(frame, context))

        if not candidates:
            return ParsedDocument(
                scheme_name="",
                report_month=context.report_month,
                holdings=[],
                warnings=["sbi_holdings_not_found_in_document"],
                confidence_score=0.0,
            )

        best = max(candidates, key=lambda item: item.get("selection_score", 0.0))
        return _to_parsed_document(best, context)


def _to_parsed_document(parsed: dict, context: ParseContext) -> ParsedDocument:
    return ParsedDocument(
        scheme_name=parsed.get("scheme_name") or "",
        report_month=parsed.get("report_month") or context.report_month,
        holdings=parsed.get("holdings", []),
        metrics=parsed.get("metrics", {}),
        warnings=parsed.get("warnings", []),
        confidence_score=float(parsed.get("confidence_score", 0.0)),
    )


def _parse_sbi_frame(frame: pd.DataFrame, context: ParseContext) -> dict | None:
    candidates = _parse_sbi_frame_many(frame, context)
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.get("selection_score", 0.0))


def _parse_sbi_frame_many(frame: pd.DataFrame, context: ParseContext) -> list[dict]:
    if frame is None or frame.empty:
        return []

    raw_rows = frame.where(pd.notna(frame), None).values.tolist()
    if not raw_rows:
        return []

    headers = _find_all_header_rows(raw_rows)
    if len(headers) <= 1:
        parsed = _parse_sbi_segment(raw_rows, context)
        return [parsed] if parsed else []

    candidates: list[dict] = []
    for index, (header_row_idx, _header_values) in enumerate(headers):
        next_header_idx = headers[index + 1][0] if index + 1 < len(headers) else len(raw_rows)
        segment_start = _segment_start_for_header(raw_rows, header_row_idx)
        parsed = _parse_sbi_segment(raw_rows[segment_start:next_header_idx], context)
        if parsed:
            candidates.append(parsed)
    return candidates


def _parse_sbi_segment(rows: list[list[object]], context: ParseContext) -> dict | None:
    scheme_name = _extract_scheme_name(rows)
    report_month = _extract_report_month(rows) or context.report_month
    header_row_idx, headers = _find_header_row(rows)
    if header_row_idx is None:
        return None

    raw_components = []
    for row in rows[header_row_idx + 1 :]:
        instrument_name = normalize_instrument_name(_get_row_cell(row, headers, "instrument_name"))
        if _is_summary_or_noise_row(instrument_name):
            continue

        percent = _parse_percent(_get_row_cell(row, headers, "percent_aum"))
        if percent is None or not (-100.0 <= percent <= 100.0) or percent == 0:
            continue

        isin = _normalize_isin(_get_row_cell(row, headers, "isin"))
        sector = normalize_instrument_name(_get_row_cell(row, headers, "sector")) or None
        quantity = _parse_number(_get_row_cell(row, headers, "quantity"))
        market_value = _parse_number(_get_row_cell(row, headers, "market_value"))

        raw_components.append(
            {
                "instrument_name": instrument_name,
                "isin": isin,
                "sector": sector,
                "percent_aum": percent,
                "quantity": quantity,
                "market_value": market_value,
            }
        )

    if not raw_components:
        return None

    raw_total = sum(float(row.get("percent_aum") or 0.0) for row in raw_components)
    max_percent = max(float(row.get("percent_aum") or 0.0) for row in raw_components)
    # Excel percentage-formatted cells can arrive as fractions. SBI's April 2026
    # workbook also has true sub-1% values, so scale only the clear fraction case.
    if raw_total <= 2.0 and max_percent <= 0.2:
        raw_components = [
            {
                **row,
                "percent_aum": round(float(row.get("percent_aum") or 0.0) * 100.0, 6),
            }
            for row in raw_components
        ]

    # Deduplicate components
    deduped: dict[str, dict] = {}
    for row in raw_components:
        name_key = str(row.get('instrument_name') or '').strip().lower()
        isin_key = str(row.get('isin') or '').strip().upper()
        key = f"{name_key}|{isin_key}"
        if not key.strip("|"):
            continue
        existing = deduped.get(key)
        if not existing or float(row.get("percent_aum") or 0.0) > float(existing.get("percent_aum") or 0.0):
            deduped[key] = row
    
    unique_components = list(deduped.values())
    holdings = [row for row in unique_components if row.get("isin") and float(row.get("percent_aum") or 0.0) > 0.0]

    total_percent = round(sum(float(row.get("percent_aum") or 0.0) for row in unique_components), 6)
    warnings: list[str] = []
    if report_month is None:
        warnings.append("report_month_not_detected")
    if not (90.0 <= total_percent <= 110.0):
        warnings.append("percent_aum_total_out_of_band")

    resolved_scheme = scheme_name or "SBI Mutual Fund"
    return {
        "scheme_name": resolved_scheme,
        "report_month": report_month,
        "holdings": holdings,
        "metrics": {"total_percent_aum": total_percent},
        "warnings": warnings,
        "confidence_score": _compute_confidence(holdings, report_month, total_percent, resolved_scheme),
        "selection_score": float(len(holdings)) + (20.0 if report_month else 0.0),
    }


def _find_all_header_rows(rows: list[list[object]]) -> list[tuple[int, list[str]]]:
    headers: list[tuple[int, list[str]]] = []
    for idx, row in enumerate(rows):
        normalized = [_normalize_sbi_header_cell(cell) for cell in row]
        has_instrument = "instrument_name" in normalized or any("instrument" in str(cell).lower() for cell in row)
        has_percent = "percent_aum" in normalized or any("% to aum" in str(cell).lower() for cell in row)
        if has_instrument and has_percent:
            headers.append((idx, normalized))
    return headers


def _segment_start_for_header(rows: list[list[object]], header_row_idx: int) -> int:
    for idx in range(header_row_idx - 1, max(header_row_idx - 10, -1), -1):
        row_text = " ".join(str(cell or "") for cell in rows[idx]).lower()
        if "scheme name" in row_text:
            return idx
        if "portfolio statement as on" in row_text:
            continue
        if "sbi " in row_text and "fund" in row_text:
            return idx
    return max(header_row_idx - 8, 0)


def _extract_scheme_name(rows: list[list[object]]) -> str:
    for row in rows[:30]:
        for idx, cell in enumerate(row):
            text = " ".join(str(cell or "").replace("\n", " ").split())
            if not text:
                continue
            if "scheme name" in text.lower():
                for tail in row[idx + 1 :]:
                    candidate = " ".join(str(tail or "").replace("\n", " ").split())
                    if candidate:
                        return candidate
    return ""


def _extract_report_month(rows: list[list[object]]) -> date | None:
    for row in rows[:30]:
        for idx, cell in enumerate(row):
            text = str(cell or "").strip()
            if "portfolio statement as on" not in text.lower():
                continue
            for tail in row[idx + 1 :]:
                resolved = _parse_date_value(tail)
                if resolved:
                    return resolved
            resolved = _parse_date_value(cell)
            if resolved:
                return resolved
    return None


def _parse_date_value(value: object) -> date | None:
    if value in (None, ""):
        return None
    if hasattr(value, "year") and hasattr(value, "month"):
        return date(int(value.year), int(value.month), 1)

    text = str(value).strip()
    if not text:
        return None
    text = text.replace("/", "-")
    match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if match:
        text = match.group(0)
    for pattern in ("%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y", "%d-%B-%Y"):
        try:
            parsed = datetime.strptime(text, pattern)
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            continue
    return None


def _find_header_row(rows: list[list[object]]) -> tuple[int | None, list[str]]:
    for idx, row in enumerate(rows[:40]):
        normalized = [_normalize_sbi_header_cell(cell) for cell in row]
        has_instrument = "instrument_name" in normalized or any("instrument" in str(cell).lower() for cell in row)
        has_percent = "percent_aum" in normalized or any("% to aum" in str(cell).lower() for cell in row)
        if has_instrument and has_percent:
            return idx, normalized
    return None, []


def _normalize_sbi_header_cell(cell: object) -> str:
    base = normalize_column_name(cell)
    raw = str(cell or "").strip().lower()
    if "name of the instrument" in raw or "instrument / issuer" in raw:
        return "instrument_name"
    if "isin" in raw:
        return "isin"
    if "% to aum" in raw or "% to nav" in raw or "% to net assets" in raw:
        return "percent_aum"
    if "rating" in raw or "industry" in raw:
        return "sector"
    if "quantity" in raw:
        return "quantity"
    if "market value" in raw:
        return "market_value"
    return base


def _extract_holdings(rows: list[list[object]], headers: list[str]) -> list[dict]:
    holdings: list[dict] = []
    for row in rows:
        instrument_name = normalize_instrument_name(_get_row_cell(row, headers, "instrument_name"))
        if _is_summary_or_noise_row(instrument_name):
            continue

        percent = _parse_percent(_get_row_cell(row, headers, "percent_aum"))
        if percent is None:
            continue
        if not (0.0 < percent <= 100.0):
            continue

        isin = _normalize_isin(_get_row_cell(row, headers, "isin"))
        # Keep overlap-ready portfolio rows only.
        if not isin:
            continue
        sector = normalize_instrument_name(_get_row_cell(row, headers, "sector")) or None
        quantity = _parse_number(_get_row_cell(row, headers, "quantity"))
        market_value = _parse_number(_get_row_cell(row, headers, "market_value"))

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


def _is_summary_or_noise_row(name: str) -> bool:
    low = re.sub(r"\s+", " ", str(name or "").strip().lower())
    if not low:
        return True
    if any(marker in low for marker in SUMMARY_ROW_MARKERS):
        return True
    if re.fullmatch(r"[\d\.\-\(\)% ,]+", low):
        return True
    return False


def _normalize_isin(value: object) -> str | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    match = ISIN_PATTERN.search(text)
    if not match:
        return None
    return match.group(0)


def _parse_percent(value: object) -> float | None:
    parsed = _parse_number(value)
    if parsed is None:
        return None
    return round(parsed, 6)


def _parse_number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        num = float(value)
        if not math.isfinite(num):
            return None
        return num
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "").replace("%", "").strip()
    if text in {"-", "--", "na", "n/a", "nan"}:
        return None
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    try:
        parsed = float(text)
        if not math.isfinite(parsed):
            return None
        return parsed
    except ValueError:
        return None


def _compute_confidence(holdings: list[dict], report_month: date | None, total_percent: float, scheme_name: str) -> float:
    if not holdings:
        return 0.0
    score = 55.0
    score += min(20.0, len(holdings) * 0.4)
    if report_month:
        score += 10.0
    if 90.0 <= total_percent <= 110.0:
        score += 10.0
    if "sbi" in (scheme_name or "").lower():
        score += 5.0
    return round(min(score, 99.0), 2)
