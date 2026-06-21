from __future__ import annotations

import math
import re
from datetime import date
from typing import Any

import pandas as pd

from app.mf_ingestion.constants import AMC_NIPPON
from app.mf_ingestion.normalizers.column_normalizer import normalize_column_name
from app.mf_ingestion.normalizers.instrument_normalizer import normalize_instrument_name
from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument

ISIN_PATTERN = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b")
SCHEME_PATTERN = re.compile(r"\b(Nippon\s+India\s+[^(\n]{3,140}?(?:Fund|FOF|ETF))\b", re.IGNORECASE)
PORTFOLIO_DATE_PATTERN = re.compile(
    r"\bMonthly\s+Portfolio\s+Statement\s+as\s+on\s+"
    r"(?P<month>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+"
    r"(?P<day>\d{1,2}),?\s*(?P<year>20\d{2})\b",
    re.IGNORECASE,
)

SUMMARY_ROW_MARKERS = (
    "equity & equity related",
    "listed / awaiting listing",
    "debt instruments",
    "floating rate note",
    "government securities",
    "money market instruments",
    "mutual fund units",
    "sub total",
    "subtotal",
    "grand total",
    "total",
    "index",
)


class NipponAdapter(BaseAMCAdapter):
    amc_code = AMC_NIPPON

    def parse_holdings(
        self,
        excel_frames: list[pd.DataFrame],
        pdf_table_frames: list[pd.DataFrame],
        pdf_text: str,
        context: ParseContext,
    ) -> ParsedDocument:
        candidates: list[dict[str, Any]] = []
        for frame in excel_frames:
            parsed = _parse_nippon_frame(frame, context)
            if parsed:
                candidates.append(parsed)

        for frame in pdf_table_frames:
            parsed = _parse_nippon_frame(frame, context)
            if parsed:
                candidates.append(parsed)

        if not candidates:
            return ParsedDocument(
                scheme_name="",
                report_month=context.report_month,
                holdings=[],
                warnings=["nippon_holdings_not_found_in_document"],
                confidence_score=0.0,
            )

        best = max(candidates, key=lambda item: item.get("selection_score", 0.0))
        return ParsedDocument(
            scheme_name=str(best.get("scheme_name") or ""),
            report_month=best.get("report_month") or context.report_month,
            holdings=best.get("holdings", []),
            metrics=best.get("metrics", {}),
            warnings=best.get("warnings", []),
            confidence_score=float(best.get("confidence_score", 0.0)),
        )


def _parse_nippon_frame(frame: pd.DataFrame, context: ParseContext) -> dict[str, Any] | None:
    if frame is None or frame.empty:
        return None

    rows = frame.where(pd.notna(frame), None).values.tolist()
    if not rows:
        return None

    scheme_name = _extract_scheme_name(frame, rows)
    if not scheme_name:
        return None

    header_idx, columns = _locate_columns(rows)
    if header_idx is None:
        return None

    raw_components: list[dict[str, Any]] = []
    for row in rows[header_idx + 1 :]:
        percent = _parse_percent(_safe_get(row, columns.get("percent_aum")))
        if percent is None or percent <= 0.0 or percent > 100.0:
            continue

        instrument_name = normalize_instrument_name(_safe_get(row, columns.get("instrument_name")))
        if not instrument_name or _is_summary_or_noise_row(instrument_name):
            continue

        isin = _normalize_isin(_safe_get(row, columns.get("isin")))
        sector = normalize_instrument_name(_safe_get(row, columns.get("sector"))) or None
        quantity = _parse_number(_safe_get(row, columns.get("quantity")))
        market_value = _parse_number(_safe_get(row, columns.get("market_value")))

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

    unique_components = _dedupe_components(raw_components)
    holdings = [
        row
        for row in unique_components
        if row.get("isin") and float(row.get("percent_aum") or 0.0) > 0.0
    ]
    if not holdings:
        return None

    total_percent = round(sum(float(row.get("percent_aum") or 0.0) for row in unique_components), 6)
    report_month = _extract_report_month(rows) or context.report_month
    warnings: list[str] = []
    if report_month is None:
        warnings.append("report_month_not_detected")
    if not (85.0 <= total_percent <= 115.0):
        warnings.append("percent_aum_total_out_of_band")

    return {
        "scheme_name": scheme_name,
        "report_month": report_month,
        "holdings": holdings,
        "metrics": {"total_percent_aum": total_percent},
        "warnings": warnings,
        "confidence_score": _compute_confidence(holdings, report_month, total_percent, scheme_name),
        "selection_score": float(len(holdings)) + (20.0 if report_month else 0.0),
    }


def _extract_scheme_name(frame: pd.DataFrame, rows: list[list[object]]) -> str:
    column_values = list(frame.columns) if frame is not None else []
    for row in [column_values, *rows[:10]]:
        for cell in row:
            text = _clean_text(cell)
            if not text or "index" == text.lower():
                continue
            match = SCHEME_PATTERN.search(text)
            if match:
                return _clean_scheme_name(match.group(1))
    return ""


def _clean_scheme_name(value: str) -> str:
    cleaned = " ".join(str(value or "").replace("\n", " ").split()).strip()
    cleaned = re.sub(r"\s+\([^)]{1,160}\)\s*$", "", cleaned)
    return cleaned.strip()


def _extract_report_month(rows: list[list[object]]) -> date | None:
    for row in rows[:12]:
        for cell in row:
            text = _clean_text(cell)
            if not text:
                continue
            match = PORTFOLIO_DATE_PATTERN.search(text)
            if not match:
                continue
            try:
                month = _month_number(match.group("month"))
                year = int(match.group("year"))
                if year > 2030 or year < 2010:
                    continue
                return date(year, month, 1)
            except Exception:
                continue
    return None


def _locate_columns(rows: list[list[object]]) -> tuple[int | None, dict[str, int]]:
    for idx, row in enumerate(rows[:25]):
        normalized = [normalize_column_name(cell) for cell in row]
        lowered = [_clean_text(cell).lower() for cell in row]

        isin_idx = _find_index(normalized, lowered, lambda norm, low: norm == "isin" or low == "isin")
        instrument_idx = _find_index(
            normalized,
            lowered,
            lambda norm, low: norm == "instrument_name" or "name of the instrument" in low,
        )
        percent_idx = _find_index(
            normalized,
            lowered,
            lambda norm, low: norm == "percent_aum" or "% to nav" in low,
        )
        if isin_idx is None or instrument_idx is None or percent_idx is None:
            continue

        columns = {
            "isin": isin_idx,
            "instrument_name": instrument_idx,
            "percent_aum": percent_idx,
        }
        sector_idx = _find_index(
            normalized,
            lowered,
            lambda norm, low: norm == "sector" or "industry" in low or "rating" in low,
        )
        quantity_idx = _find_index(normalized, lowered, lambda norm, low: norm == "quantity" or "quantity" in low)
        market_value_idx = _find_index(
            normalized,
            lowered,
            lambda norm, low: norm == "market_value" or "market/fair value" in low or "market value" in low,
        )
        if sector_idx is not None:
            columns["sector"] = sector_idx
        if quantity_idx is not None:
            columns["quantity"] = quantity_idx
        if market_value_idx is not None:
            columns["market_value"] = market_value_idx
        return idx, columns
    return None, {}


def _find_index(normalized: list[str], lowered: list[str], predicate) -> int | None:
    for index, (norm, low) in enumerate(zip(normalized, lowered)):
        if predicate(norm, low):
            return index
    return None


def _safe_get(row: list[object], index: int | None) -> object | None:
    if index is None or index < 0 or index >= len(row):
        return None
    return row[index]


def _clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\xa0", " ").replace("\n", " ").split()).strip()


def _normalize_isin(value: object) -> str | None:
    text = _clean_text(value).upper()
    match = ISIN_PATTERN.search(text)
    return match.group(0) if match else None


def _parse_percent(value: object) -> float | None:
    parsed = _parse_number(value)
    if parsed is None:
        return None
    if 0.0 < parsed <= 1.0:
        parsed *= 100.0
    return round(parsed, 6)


def _parse_number(value: object) -> float | None:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        if isinstance(value, float) and math.isnan(value):
            return None
        return float(value)
    text = _clean_text(value).replace(",", "").replace("$", "").replace("%", "")
    if not text:
        return None
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group(0))
    except ValueError:
        return None


def _is_summary_or_noise_row(instrument_name: str) -> bool:
    text = _clean_text(instrument_name).lower()
    if not text:
        return True
    if len(text) <= 2:
        return True
    return any(marker in text for marker in SUMMARY_ROW_MARKERS)


def _dedupe_components(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for row in rows:
        name_key = str(row.get("instrument_name") or "").strip().lower()
        isin_key = str(row.get("isin") or "").strip().upper()
        key = f"{name_key}|{isin_key}"
        if not key.strip("|"):
            continue
        existing = deduped.get(key)
        if not existing or float(row.get("percent_aum") or 0.0) > float(existing.get("percent_aum") or 0.0):
            deduped[key] = row
    return list(deduped.values())


def _compute_confidence(holdings: list[dict[str, Any]], report_month: date | None, total_percent: float, scheme_name: str) -> float:
    score = 45.0
    if scheme_name:
        score += 15.0
    if report_month:
        score += 15.0
    if holdings:
        score += min(20.0, len(holdings) / 2.0)
    if 85.0 <= total_percent <= 115.0:
        score += 5.0
    return min(score, 99.0)


def _month_number(month_name: str) -> int:
    token = str(month_name or "").strip().lower()[:3]
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
    return int(months[token])
