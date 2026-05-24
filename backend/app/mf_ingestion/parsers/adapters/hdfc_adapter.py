from __future__ import annotations

import re
import math
from datetime import date

import pandas as pd

from app.mf_ingestion.constants import AMC_HDFC
from app.mf_ingestion.normalizers.column_normalizer import normalize_column_name
from app.mf_ingestion.normalizers.instrument_normalizer import normalize_instrument_name
from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument

SCHEME_PATTERN = re.compile(r"\b(HDFC\s+[A-Za-z0-9&,'\-\.\(\) ]{2,100}?(?:Fund|FOF|ETF))\b", re.IGNORECASE)
INLINE_NAME_PCT_PATTERN = re.compile(
    r"(?P<name>[A-Za-z][A-Za-z0-9&,'\-\.\(\)/ ]{2,}?)\s+(?P<pct>\d{1,2}\.\d{2})(?=\s+[A-Za-z]|$)"
)
PCT_ONLY_PATTERN = re.compile(r"^-?\d{1,2}\.\d{2}$")
INLINE_DATE_PATTERN = re.compile(
    r"\b(?P<day>\d{1,2})\s+(?P<month>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[,\s]+(?P<year>20\d{2})\b",
    re.IGNORECASE,
)
INLINE_DATE_PATTERN_MONTH_FIRST = re.compile(
    r"\b(?P<month>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(?P<day>\d{1,2}),\s*(?P<year>20\d{2})\b",
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
PAGE_STOP_MARKERS = (
    "sip performance",
    "portfolio turnover",
    "risk ratio",
    "quantitative data",
    "base expense",
    "total exp",
    "exit load",
    "benchmark",
    "name since",
)


class HDFCAdapter(BaseAMCAdapter):
    amc_code = AMC_HDFC

    def __init__(self) -> None:
        self._active_source_document_id: str | None = None
        self._last_scheme_name: str | None = None

    def parse_holdings(
        self,
        excel_frames: list[pd.DataFrame],
        pdf_table_frames: list[pd.DataFrame],
        pdf_text: str,
        context: ParseContext,
    ) -> ParsedDocument:
        if context.source_document_id != self._active_source_document_id:
            self._active_source_document_id = context.source_document_id
            self._last_scheme_name = None

        candidates: list[dict] = []
        for frame in excel_frames:
            parsed = _parse_hdfc_frame(frame, context, fallback_scheme=self._last_scheme_name)
            if parsed:
                candidates.append(parsed)
                self._last_scheme_name = parsed.get("scheme_name") or self._last_scheme_name

        for frame in pdf_table_frames:
            parsed = _parse_hdfc_frame(frame, context, fallback_scheme=self._last_scheme_name)
            if parsed:
                candidates.append(parsed)
                self._last_scheme_name = parsed.get("scheme_name") or self._last_scheme_name

        if not candidates:
            return ParsedDocument(
                scheme_name="",
                report_month=context.report_month,
                holdings=[],
                warnings=["hdfc_holdings_not_found_in_document"],
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


def _parse_hdfc_frame(frame: pd.DataFrame, context: ParseContext, fallback_scheme: str | None = None) -> dict | None:
    if frame is None or frame.empty:
        return None

    rows = frame.where(pd.notna(frame), None).values.tolist()
    if not rows:
        return None

    flattened = " ".join(str(cell or "") for row in rows[:20] for cell in row).lower()
    if not any(token in flattened for token in ("portfolio", "% to", "company", "instrument", "nav")):
        return None

    page_text_full = str(frame.attrs.get("page_text_full") or "")
    scheme_name = _extract_scheme_name(frame, rows, page_text_full=page_text_full) or (fallback_scheme or "")
    if scheme_name.strip().lower() == "hdfc mutual fund":
        scheme_name = fallback_scheme or ""
    if not scheme_name:
        return None

    header_row_idx, instrument_idx, percent_idx, sector_idx = _locate_header_and_columns(rows)
    data_rows = rows[header_row_idx + 1 :] if header_row_idx is not None else rows
    holdings = _extract_holdings(data_rows, instrument_idx, percent_idx, sector_idx)
    if not holdings:
        blob = _frame_blob_text(rows)
        holdings = _extract_holdings_from_blob(blob)
    if page_text_full and _page_text_scoped_to_scheme(page_text_full, scheme_name):
        holdings.extend(_extract_holdings_from_page_text(page_text_full))
        holdings = _dedupe_holdings(holdings)
    if not holdings:
        return None

    report_month = _extract_report_month(page_text_full, rows) or context.report_month
    total_percent = round(sum(float(row.get("percent_aum") or 0.0) for row in holdings), 6)
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


def _extract_scheme_name(frame: pd.DataFrame, rows: list[list[object]], page_text_full: str = "") -> str:
    page_head = str(frame.attrs.get("page_text_head") or "")
    if page_head:
        match = SCHEME_PATTERN.search(page_head)
        if match:
            return " ".join(match.group(1).split())

    for row in rows[:25]:
        for cell in row:
            text = " ".join(str(cell or "").replace("\n", " ").split())
            if not text:
                continue
            match = SCHEME_PATTERN.search(text)
            if match:
                return " ".join(match.group(1).split())
    if page_text_full:
        match = SCHEME_PATTERN.search(page_text_full)
        if match:
            return " ".join(match.group(1).split())
    return ""


def _page_text_scoped_to_scheme(page_text: str, scheme_name: str) -> bool:
    mentions = {
        " ".join(match.group(1).lower().split())
        for match in SCHEME_PATTERN.finditer(page_text or "")
    }
    if len(mentions) <= 1:
        return True
    normalized_scheme = " ".join(str(scheme_name or "").lower().split())
    return bool(normalized_scheme and mentions == {normalized_scheme})


def _locate_header_and_columns(rows: list[list[object]]) -> tuple[int | None, int | None, int | None, int | None]:
    for idx, row in enumerate(rows[:30]):
        normalized = [normalize_column_name(cell) for cell in row]
        lowered = [str(cell or "").strip().lower() for cell in row]

        instrument_idx = _find_first_index(
            normalized,
            lowered,
            lambda norm, low: norm == "instrument_name" or "company/instrument" in low or low == "company",
        )
        percent_idx = _find_first_index(
            normalized,
            lowered,
            lambda norm, low: norm == "percent_aum" or "% to nav" in low or "% to" in low,
        )
        if idx + 1 < len(rows):
            next_low = [str(cell or "").strip().lower() for cell in rows[idx + 1]]
            if any("% to" in low for low in lowered) and any("nav" == n or "nav" in n for n in next_low):
                nav_idx = _find_nav_column(next_low)
                if nav_idx is not None:
                    percent_idx = nav_idx

        if instrument_idx is not None and percent_idx is not None:
            sector_idx = _find_first_index(
                normalized,
                lowered,
                lambda norm, low: norm == "sector" or "industry" in low or "rating" in low,
            )
            if sector_idx is None and instrument_idx + 1 < len(row):
                sector_idx = instrument_idx + 1
            return idx, instrument_idx, percent_idx, sector_idx

    # Fallback for fragmented frames that carry data rows without headers.
    return None, 0, None, None


def _find_first_index(normalized: list[str], lowered: list[str], predicate) -> int | None:
    for idx, (norm, low) in enumerate(zip(normalized, lowered)):
        if predicate(norm, low):
            return idx
    return None


def _find_nav_column(next_low: list[str]) -> int | None:
    for idx, low in enumerate(next_low):
        if low == "nav" or low.endswith(" nav") or "nav" in low:
            return idx
    return None


def _extract_holdings(
    rows: list[list[object]],
    instrument_idx: int | None,
    percent_idx: int | None,
    sector_idx: int | None,
) -> list[dict]:
    holdings: list[dict] = []
    for row in rows:
        direct = _extract_structured_row_holding(row, instrument_idx, percent_idx, sector_idx)
        if direct:
            holdings.append(direct)
            continue

        text = _frame_blob_text([row])
        if text.count("\n") < 2:
            continue
        holdings.extend(_extract_holdings_from_blob(text))

    deduped: dict[str, dict] = {}
    for row in holdings:
        key = str(row.get("instrument_name") or "").strip().lower()
        if not key:
            continue
        existing = deduped.get(key)
        if not existing or float(row.get("percent_aum") or 0.0) > float(existing.get("percent_aum") or 0.0):
            deduped[key] = row
    return list(deduped.values())


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
    if "hdfc" in (scheme_name or "").lower():
        score += 5.0
    return round(min(score, 99.0), 2)


def _extract_structured_row_holding(
    row: list[object],
    instrument_idx: int | None,
    percent_idx: int | None,
    sector_idx: int | None,
) -> dict | None:
    numeric_values: list[float] = []
    numeric_indices: list[int] = []
    for idx, value in enumerate(row):
        parsed = _parse_number(value)
        if parsed is None:
            continue
        if parsed <= 0.0 or parsed > 100.0:
            continue
        numeric_values.append(parsed)
        numeric_indices.append(idx)
    if not numeric_values:
        return None

    if percent_idx is not None and percent_idx < len(row):
        percent = _parse_number(_safe_row_get(row, percent_idx))
        if percent is None:
            percent = _parse_number(_safe_row_get(row, percent_idx + 1))
    else:
        percent = numeric_values[-1]
    if percent is None or percent <= 0.0 or percent > 100.0:
        return None

    name_value = None
    if instrument_idx is not None:
        name_value = _safe_row_get(row, instrument_idx)
    if not name_value:
        for idx, value in enumerate(row):
            if idx in numeric_indices:
                continue
            text = normalize_instrument_name(value)
            if text and re.search(r"[A-Za-z]", text):
                name_value = text
                break

    instrument_name = normalize_instrument_name(name_value)
    if "\n" in str(name_value or ""):
        instrument_name = instrument_name.split("\n")[0].strip()
    if len(re.findall(r"\d{1,2}\.\d{2}", instrument_name)) >= 2:
        return None
    if _is_summary_or_noise_row(instrument_name):
        return None

    sector = None
    if sector_idx is not None and sector_idx < len(row):
        sector = normalize_instrument_name(_safe_row_get(row, sector_idx)) or None
        if sector and sector.lower() == instrument_name.lower():
            sector = None

    return {
        "instrument_name": instrument_name,
        "isin": None,
        "sector": sector,
        "percent_aum": round(percent, 6),
        "quantity": None,
        "market_value": None,
    }


def _frame_blob_text(rows: list[list[object]]) -> str:
    chunks: list[str] = []
    for row in rows:
        for cell in row:
            text = str(cell or "").strip()
            if not text:
                continue
            chunks.append(text)
    return "\n".join(chunks)


def _extract_holdings_from_blob(text: str) -> list[dict]:
    if not text:
        return []
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    holdings: list[dict] = []
    for line in lines:
        compact = " ".join(line.split())
        pairs = _extract_inline_name_pct_pairs(compact)
        if not pairs:
            continue
        for name, pct in pairs:
            holdings.append(
                {
                    "instrument_name": name,
                    "isin": None,
                    "sector": None,
                    "percent_aum": round(pct, 6),
                    "quantity": None,
                    "market_value": None,
                }
            )
    return holdings


def _extract_holdings_from_page_text(page_text: str) -> list[dict]:
    lines = [" ".join(line.strip().split()) for line in (page_text or "").splitlines()]
    lines = [line for line in lines if line]
    if not lines:
        return []

    holdings: list[dict] = []
    in_portfolio = False
    last_name: str | None = None

    for line in lines:
        low = line.lower()
        if not in_portfolio and ("portfolio" in low or "company/instrument" in low):
            in_portfolio = True
            continue
        if not in_portfolio:
            continue
        if any(marker in low for marker in PAGE_STOP_MARKERS):
            break
        if any(marker in low for marker in SUMMARY_ROW_MARKERS):
            continue
        if low in {"company", "industry+", "industry+ /rating", "% to nav", "nav"}:
            continue

        pairs = _extract_inline_name_pct_pairs(line)
        if pairs:
            for name, pct in pairs:
                holdings.append(
                    {
                        "instrument_name": name,
                        "isin": None,
                        "sector": None,
                        "percent_aum": round(pct, 6),
                        "quantity": None,
                        "market_value": None,
                    }
                )
                last_name = name
            continue

        if PCT_ONLY_PATTERN.fullmatch(line):
            pct = _parse_number(line)
            if last_name and pct is not None and 0.0 < pct <= 100.0:
                holdings.append(
                    {
                        "instrument_name": last_name,
                        "isin": None,
                        "sector": None,
                        "percent_aum": round(pct, 6),
                        "quantity": None,
                        "market_value": None,
                    }
                )
            continue

        if _looks_like_instrument_name_line(line):
            last_name = normalize_instrument_name(line)

    return holdings


def _looks_like_instrument_name_line(line: str) -> bool:
    if not line:
        return False
    low = line.lower()
    if any(marker in low for marker in SUMMARY_ROW_MARKERS):
        return False
    if re.fullmatch(r"[\d\.\-\(\)% ,]+", line):
        return False
    if not re.search(r"[A-Za-z]", line):
        return False
    return len(line) >= 4


def _dedupe_holdings(holdings: list[dict]) -> list[dict]:
    deduped: dict[str, dict] = {}
    for row in holdings:
        key = str(row.get("instrument_name") or "").strip().lower()
        if not key:
            continue
        existing = deduped.get(key)
        if not existing or float(row.get("percent_aum") or 0.0) > float(existing.get("percent_aum") or 0.0):
            deduped[key] = row
    return list(deduped.values())


def _extract_inline_name_pct_pairs(line: str) -> list[tuple[str, float]]:
    pairs: list[tuple[str, float]] = []
    for match in INLINE_NAME_PCT_PATTERN.finditer(line or ""):
        name = normalize_instrument_name(match.group("name"))
        pct = _parse_number(match.group("pct"))
        if pct is None or pct <= 0.0 or pct > 100.0:
            continue
        if _is_summary_or_noise_row(name):
            continue
        pairs.append((name, pct))
    return pairs


def _extract_report_month(page_text_full: str, rows: list[list[object]]) -> date | None:
    candidates = [page_text_full, _frame_blob_text(rows[:30])]
    for text in candidates:
        if not text:
            continue
        for pattern in (INLINE_DATE_PATTERN, INLINE_DATE_PATTERN_MONTH_FIRST):
            match = pattern.search(text)
            if not match:
                continue
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
