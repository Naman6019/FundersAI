from __future__ import annotations

import re
import math
from datetime import date

import pandas as pd

from app.mf_ingestion.constants import AMC_MOTILAL
from app.mf_ingestion.normalizers.column_normalizer import normalize_column_name
from app.mf_ingestion.normalizers.instrument_normalizer import normalize_instrument_name
from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument

SCHEME_PATTERN = re.compile(r"\b(Motilal\s+Oswal\s+[A-Za-z0-9&,'\-\.\(\) ]{2,100})\b", re.IGNORECASE)
AS_ON_DATE_PATTERN = re.compile(
    r"\b(?:as\s+on|as\s+of)\s+(?P<month>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(?P<day>\d{1,2}),\s*(?P<year>20\d{2})\b",
    re.IGNORECASE,
)
SUMMARY_ROW_MARKERS = (
    "sub total",
    "subtotal",
    "total",
    "grand total",
    "portfolio turnover",
    "risk ratio",
    "quantitative data",
    "industry allocation",
    "credit exposure",
    "equity",
    "debt",
    "cash and cash equivalents",
    "mutual fund units",
)


class MotilalAdapter(BaseAMCAdapter):
    amc_code = AMC_MOTILAL

    def parse_holdings(
        self,
        excel_frames: list[pd.DataFrame],
        pdf_table_frames: list[pd.DataFrame],
        pdf_text: str,
        context: ParseContext,
    ) -> ParsedDocument:
        candidates: list[dict] = []
        for frame in excel_frames:
            parsed = _parse_motilal_frame(frame, context)
            if parsed:
                candidates.append(parsed)

        if not candidates:
            return ParsedDocument(
                scheme_name="",
                report_month=context.report_month,
                holdings=[],
                warnings=["motilal_holdings_not_found_in_document"],
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


def _parse_motilal_frame(frame: pd.DataFrame, context: ParseContext) -> dict | None:
    if frame is None or frame.empty:
        return None

    rows = frame.where(pd.notna(frame), None).values.tolist()
    if not rows:
        return None

    scheme_name = _extract_scheme_name(frame, rows)
    if not scheme_name:
        return None

    header_row_idx, instrument_idx, percent_idx, sector_idx, isin_idx = _locate_header_and_columns(rows)
    if header_row_idx is None:
        return None
        
    data_rows = rows[header_row_idx + 1 :]
    holdings, total_percent = _extract_holdings(data_rows, instrument_idx, percent_idx, sector_idx, isin_idx)

    if not holdings:
        return None

    report_month = _extract_report_month(rows) or context.report_month
    warnings: list[str] = []
    if report_month is None:
        warnings.append("report_month_not_detected")
    if not (80.0 <= total_percent <= 120.0):
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
    # Scheme name is usually in the first few rows. e.g. 'Motilal Oswal Nifty 50 ETF \n'
    for row in rows[:15]:
        for cell in row:
            text = " ".join(str(cell or "").replace("\n", " ").split())
            if not text:
                continue
            match = SCHEME_PATTERN.search(text)
            if match and "Asset Management" not in text and "Mutual Fund" not in text and "MONTHLY PORTFOLIO" not in text and "Tower" not in text:
                return " ".join(match.group(1).split())
    return ""


def _extract_report_month(rows: list[list[object]]) -> date | None:
    for row in rows[:15]:
        for cell in row:
            text = " ".join(str(cell or "").replace("\n", " ").split())
            if not text:
                continue
            match = AS_ON_DATE_PATTERN.search(text)
            if match:
                try:
                    month_name = match.group("month")
                    month_number = _month_name_to_number(month_name)
                    year = int(match.group("year"))
                    return date(year, month_number, 1)
                except Exception:
                    continue
    return None


def _month_name_to_number(month_name: str) -> int:
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


def _locate_header_and_columns(rows: list[list[object]]) -> tuple[int | None, int | None, int | None, int | None, int | None]:
    for idx, row in enumerate(rows[:30]):
        normalized = [normalize_column_name(cell) for cell in row]
        lowered = [str(cell or "").strip().lower() for cell in row]

        instrument_idx = _find_first_index(
            normalized,
            lowered,
            lambda norm, low: norm == "instrument_name" or "name of the instrument" in low,
        )
        percent_idx = _find_first_index(
            normalized,
            lowered,
            lambda norm, low: norm == "percent_aum" or "% to net assets" in low,
        )
        isin_idx = _find_first_index(
            normalized,
            lowered,
            lambda norm, low: norm == "isin" or "isin" in low,
        )

        if instrument_idx is not None and percent_idx is not None:
            sector_idx = _find_first_index(
                normalized,
                lowered,
                lambda norm, low: norm == "sector" or "industry" in low or "rating" in low,
            )
            return idx, instrument_idx, percent_idx, sector_idx, isin_idx

    return None, None, None, None, None


def _find_first_index(normalized: list[str], lowered: list[str], predicate) -> int | None:
    for idx, (norm, low) in enumerate(zip(normalized, lowered)):
        if predicate(norm, low):
            return idx
    return None


def _extract_holdings(
    rows: list[list[object]],
    instrument_idx: int | None,
    percent_idx: int | None,
    sector_idx: int | None,
    isin_idx: int | None,
) -> tuple[list[dict], float]:
    holdings: list[dict] = []
    true_total_percent = 0.0

    for row in rows:
        if percent_idx is None or percent_idx >= len(row):
            continue
            
        percent = _parse_number(_safe_row_get(row, percent_idx))
        if percent is None or percent <= 0.0 or percent > 100.0:
            continue

        name_value = _safe_row_get(row, instrument_idx) if instrument_idx is not None else None
        if not name_value:
            continue
            
        instrument_name = normalize_instrument_name(name_value)
        instrument_name = instrument_name.encode("ascii", "ignore").decode("ascii")
        if "\n" in str(name_value or ""):
            instrument_name = instrument_name.split("\n")[0].strip()
        
        if not instrument_name or len(re.findall(r"\d{1,2}\.\d{2}", instrument_name)) >= 2:
            continue

        low_name = instrument_name.lower()
        if any(marker in low_name for marker in ("grand total", "grand_total", "total assets", "total equity", "total debt")):
            continue
        if low_name in ("equity", "debt", "mutual fund units"):
            continue

        if not any(marker in low_name for marker in ("sub total", "subtotal", "total", "grand total", "total value", "total market value")):
            true_total_percent += percent

        if _is_summary_or_noise_row(instrument_name):
            continue

        sector = None
        if sector_idx is not None and sector_idx < len(row):
            sector = normalize_instrument_name(_safe_row_get(row, sector_idx)) or None
            if sector:
                sector = sector.encode("ascii", "ignore").decode("ascii")
            if sector and sector.lower() == instrument_name.lower():
                sector = None

        isin = None
        if isin_idx is not None and isin_idx < len(row):
            isin = str(_safe_row_get(row, isin_idx) or "").strip()
            if isin and len(isin) == 12 and isin.isalnum():
                pass
            else:
                isin = None

        holdings.append(
            {
                "instrument_name": instrument_name,
                "isin": isin,
                "sector": sector,
                "percent_aum": round(percent, 6),
                "quantity": None,
                "market_value": None,
            }
        )

    deduped: dict[str, dict] = {}
    for row in holdings:
        key = str(row.get("instrument_name") or "").strip().lower()
        if not key:
            continue
        existing = deduped.get(key)
        if not existing or float(row.get("percent_aum") or 0.0) > float(existing.get("percent_aum") or 0.0):
            deduped[key] = row

    return list(deduped.values()), round(true_total_percent, 6)


def _safe_row_get(row: list[object], index: int) -> object:
    if index < 0 or index >= len(row):
        return None
    return row[index]


def _is_summary_or_noise_row(name: str) -> bool:
    low = re.sub(r"\s+", " ", str(name or "").strip().lower())
    if not low:
        return True
    if any(marker in low for marker in SUMMARY_ROW_MARKERS):
        return True
    if re.fullmatch(r"[\d\.\-\(\)% ,]+", low):
        return True
    return False


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
    score = 50.0
    score += min(25.0, len(holdings) * 0.5)
    if report_month:
        score += 10.0
    if 80.0 <= total_percent <= 120.0:
        score += 10.0
    if "motilal" in (scheme_name or "").lower():
        score += 5.0
    return round(min(score, 99.0), 2)
