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
AS_ON_DATE_PATTERN = re.compile(
    r"\b(?:as\s+on|as\s+of)\s+(?P<month>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(?P<day>\d{1,2}),\s*(?P<year>20\d{2})\b",
    re.IGNORECASE,
)
AS_ON_DATE_PATTERN_DAY_FIRST = re.compile(
    r"\b(?:as\s+on|as\s+of)\s+(?P<day>\d{1,2})\s+(?P<month>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)[,\s]+(?P<year>20\d{2})\b",
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
PDF_MIN_PORTFOLIO_PAGE = 7
PAGE_REJECT_MARKERS = (
    "contents",
    "glossary",
    "market review",
)
PORTFOLIO_TABLE_MARKERS = (
    "portfolio",
    "company/instrument",
    "% to nav",
    "% to\nnav",
    "equity & equity related",
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

    page_number = _frame_page_number(frame)
    if page_number is not None and page_number < PDF_MIN_PORTFOLIO_PAGE:
        return None

    raw_rows = frame.where(pd.notna(frame), None).values.tolist()
    columns = list(frame.columns)
    # Include columns as the first row to ensure header is not lost
    rows = [columns] + raw_rows if raw_rows else [columns]
    
    if not rows:
        return None

    page_text_full = str(frame.attrs.get("page_text_full") or "")
    flattened = " ".join(str(cell or "") for row in rows[:20] for cell in row).lower()
    page_low = page_text_full.lower()
    looks_like = _looks_like_hdfc_portfolio_page(flattened, page_low)
    if not looks_like:
        return None

    scheme_name = _extract_scheme_name(frame, rows, page_text_full=page_text_full) or (fallback_scheme or "")
    if scheme_name.strip().lower() == "hdfc mutual fund":
        scheme_name = fallback_scheme or ""
    if not scheme_name:
        return None

    header_row_idx, instrument_idx, percent_idx, sector_idx = _locate_header_and_columns(rows)
    data_rows = rows[header_row_idx + 1 :] if header_row_idx is not None else rows
    holdings, total_percent = _extract_holdings(data_rows, instrument_idx, percent_idx, sector_idx)
    
    word_holdings = _extract_holdings_from_page_words(frame.attrs.get("page_words") or [])
    if len(word_holdings) > len(holdings) and len(word_holdings) > 5:
        holdings = word_holdings
        total_percent = round(sum(float(row.get("percent_aum") or 0.0) for row in holdings), 6)
        
    if not holdings:
        blob = _frame_blob_text(rows)
        holdings = _extract_holdings_from_blob(blob)
        total_percent = round(sum(float(row.get("percent_aum") or 0.0) for row in holdings), 6)

    if page_text_full and _page_text_scoped_to_scheme(page_text_full, scheme_name):
        holdings.extend(_extract_holdings_from_page_text(page_text_full))
        holdings = _dedupe_holdings(holdings)
        total_percent = round(sum(float(row.get("percent_aum") or 0.0) for row in holdings), 6)
    
    if not holdings:
        return None

    report_month = _extract_report_month(page_text_full, rows) or context.report_month
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


def _frame_page_number(frame: pd.DataFrame) -> int | None:
    raw = frame.attrs.get("page_number")
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def _looks_like_hdfc_portfolio_page(table_text: str, page_text: str) -> bool:
    combined = f"{page_text} {table_text}".lower()
    if any(marker in combined for marker in PAGE_REJECT_MARKERS) and "portfolio" not in table_text:
        return False
    has_portfolio_marker = any(marker in combined for marker in PORTFOLIO_TABLE_MARKERS)
    has_columns = ("company" in combined or "instrument" in combined) and ("% to" in combined or "nav" in combined)
    has_inline_holdings = "portfolio" in combined and bool(_extract_inline_name_pct_pairs(combined))
    return has_portfolio_marker and (has_columns or has_inline_holdings)


def _extract_holdings_from_page_words(words: list[dict]) -> list[dict]:
    if not words:
        return []

    holdings: list[dict] = []
    for bounds in ((198.0, 278.0, 346.0, 365.0), (376.0, 463.0, 531.0, 552.0)):
        holdings.extend(_extract_holdings_from_word_column(words, bounds))
    return _dedupe_holdings(holdings)


def _extract_holdings_from_word_column(words: list[dict], bounds: tuple[float, float, float, float]) -> list[dict]:
    name_x0, sector_x0, percent_x0, x1_limit = bounds
    candidates = []
    for word in words:
        try:
            x0 = float(word.get("x0") or 0.0)
            top = float(word.get("top") or 0.0)
        except (TypeError, ValueError):
            continue
        if top < 135.0 or top > 705.0:
            continue
        if x0 < name_x0 or x0 > x1_limit:
            continue
        candidates.append(word)

    candidates.sort(key=lambda w: float(w.get("top") or 0.0))
    lines: list[list[dict]] = []
    current_group: list[dict] = []
    current_top: float | None = None
    
    for word in candidates:
        top = float(word.get("top") or 0.0)
        if current_top is None:
            current_top = top
            current_group.append(word)
        elif abs(top - current_top) < 5.0:
            current_group.append(word)
        else:
            lines.append(current_group)
            current_group = [word]
            current_top = top
            
    if current_group:
        lines.append(current_group)

    holdings: list[dict] = []
    pending_name = ""
    for line_words in lines:
        ordered = sorted(line_words, key=lambda item: float(item.get("x0") or 0.0))
        percent_words = [word for word in ordered if float(word.get("x0") or 0.0) >= percent_x0]
        percent = _parse_number("".join(str(word.get("text") or "") for word in percent_words))
        
        left_words = [word for word in ordered if float(word.get("x0") or 0.0) < percent_x0]
        if not left_words:
            continue
            
        best_gap = -1.0
        split_idx = len(left_words)
        for i in range(len(left_words) - 1):
            w1 = left_words[i]
            w2 = left_words[i+1]
            x1_1 = float(w1.get("x1") or float(w1.get("x0") or 0.0) + len(str(w1.get("text") or ""))*5.0)
            x0_2 = float(w2.get("x0") or 0.0)
            gap = x0_2 - x1_1
            if gap > best_gap:
                best_gap = gap
                split_idx = i + 1
        
        if best_gap < 4.0:
            name_w = left_words
            sector_w = []
        else:
            name_w = left_words[:split_idx]
            sector_w = left_words[split_idx:]
            
        instrument_name = _clean_word_text([str(w.get("text") or "") for w in name_w])
        sector = _clean_word_text([str(w.get("text") or "") for w in sector_w]) or None

        if percent is None:
            if instrument_name:
                low_nm = instrument_name.lower().strip()
                is_section = any(m in low_nm for m in (
                    "equity & equity", "debt & debt", "reit", "units issued",
                    "government securities", "money market", "mutual fund unit",
                    "listed / awaiting", "regular plan", "direct plan",
                )) or low_nm in ("company", "instrument", "company/instrument")
                if not is_section:
                    if pending_name:
                        pending_name += " " + instrument_name
                    else:
                        pending_name = instrument_name
            continue
            
        if percent <= 0.0 or percent > 100.0:
            pending_name = ""
            continue

        if not instrument_name or _is_summary_or_noise_row(instrument_name):
            pending_name = ""
            continue
        if any(marker in instrument_name.lower() for marker in ("regular plan", "direct plan", "nav per", "expense ratio", "instrument", "company/instrument", "company")):
            pending_name = ""
            continue

        if pending_name:
            instrument_name = pending_name + " " + instrument_name
            pending_name = ""

        holdings.append(
            {
                "instrument_name": instrument_name,
                "isin": None,
                "sector": sector,
                "percent_aum": round(percent, 6),
                "quantity": None,
                "market_value": None,
            }
        )
    return holdings


def _clean_word_text(tokens: list[str]) -> str:
    cleaned = [str(token or "").strip() for token in tokens if str(token or "").strip()]
    if not cleaned:
        return ""
    one_char_count = sum(1 for token in cleaned if len(token) == 1)
    if len(cleaned) >= 4 and one_char_count / len(cleaned) > 0.65:
        text = "".join(cleaned)
        text = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", text)
    else:
        text = " ".join(cleaned)
    text = text.encode("ascii", "ignore").decode("ascii")
    return normalize_instrument_name(text)


def _extract_scheme_name(frame: pd.DataFrame, rows: list[list[object]], page_text_full: str = "") -> str:
    for column in frame.columns:
        text = " ".join(str(column or "").replace("\n", " ").split())
        if not text or "Unnamed" in text:
            continue
        match = SCHEME_PATTERN.search(text)
        if match:
            return " ".join(match.group(1).split())

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
) -> tuple[list[dict], float]:
    holdings: list[dict] = []
    true_total_percent = 0.0
    pending_name = ""

    for row in rows:
        # Extract direct percent
        numeric_values = []
        for idx, value in enumerate(row):
            parsed = _parse_number(value)
            if parsed is not None and 0.0 < parsed <= 100.0:
                numeric_values.append(parsed)
        
        if percent_idx is not None and percent_idx < len(row):
            percent = _parse_number(_safe_row_get(row, percent_idx))
            if percent is None:
                percent = _parse_number(_safe_row_get(row, percent_idx + 1))
        else:
            percent = numeric_values[-1] if numeric_values else None

        if percent is None or percent <= 0.0 or percent > 100.0:
            # Buffer name from row without percent
            name_val = None
            if instrument_idx is not None:
                name_val = _safe_row_get(row, instrument_idx)
            if not name_val:
                for idx, value in enumerate(row):
                    if idx in ([percent_idx, percent_idx + 1] if percent_idx is not None else []):
                        continue
                    text = normalize_instrument_name(value)
                    if text and re.search(r"[A-Za-z]", text):
                        name_val = text
                        break
            if name_val:
                clean_name = normalize_instrument_name(name_val).encode("ascii", "ignore").decode("ascii")
                if "\n" in clean_name:
                    clean_name = clean_name.split("\n")[0].strip()
                if pending_name:
                    pending_name += " " + clean_name
                else:
                    pending_name = clean_name
            continue

        # Extract instrument name
        name_value = None
        if instrument_idx is not None:
            name_value = _safe_row_get(row, instrument_idx)
        if not name_value:
            for idx, value in enumerate(row):
                if idx in ([percent_idx, percent_idx + 1] if percent_idx is not None else []):
                    continue
                text = normalize_instrument_name(value)
                if text and re.search(r"[A-Za-z]", text):
                    name_value = text
                    break
        
        instrument_name = normalize_instrument_name(name_value)
        instrument_name = instrument_name.encode("ascii", "ignore").decode("ascii")
        if "\n" in str(name_value or ""):
            instrument_name = instrument_name.split("\n")[0].strip()
            
        if pending_name:
            instrument_name = pending_name + " " + instrument_name
            pending_name = ""
        
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

        holdings.append(
            {
                "instrument_name": instrument_name,
                "isin": None,
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
    compact = re.sub(r"[^a-z0-9]+", "", low)
    if "subtotal" in compact or "grandtotal" in compact:
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
        if not in_portfolio and (
            "company/instrument" in low
            or low.startswith("company ")
            or "equity & equity related" in low
            or "debt & debt related" in low
        ):
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
        if not key or _is_summary_or_noise_row(key):
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
        for pattern in (AS_ON_DATE_PATTERN, AS_ON_DATE_PATTERN_DAY_FIRST):
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
