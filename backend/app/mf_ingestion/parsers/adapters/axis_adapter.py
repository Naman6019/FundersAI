from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Any

import fitz
import pandas as pd

from app.mf_ingestion.constants import AMC_AXIS
from app.mf_ingestion.normalizers.column_normalizer import normalize_column_name
from app.mf_ingestion.normalizers.instrument_normalizer import normalize_instrument_name
from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument

ISIN_PATTERN = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b")
PERCENT_LINE_PATTERN = re.compile(r"^-?\d{1,3}(?:\.\d+)?%$")
SCHEME_TITLE_PATTERN = re.compile(r"^AXIS\s+.+?(?:FUND|ETF|FOF|PLAN)\b", re.IGNORECASE)

PORTFOLIO_START_MARKERS = {
    "equity",
    "domestic equities",
    "international mutual fund units",
    "international exchange traded funds",
    "certificate of deposit",
    "commercial paper",
    "treasury bill",
    "state government bond",
    "government bond",
    "corporate bond",
    "securitised debt",
    "mutual fund units",
    "exchange traded funds",
}

SUMMARY_ROW_MARKERS = (
    "sub total",
    "subtotal",
    "total",
    "grand total",
    "net assets",
    "net current assets",
    "equity",
    "domestic equities",
    "debt instruments",
    "mutual fund units",
    "exchange traded funds",
    "international mutual fund units",
    "international exchange traded funds",
    "cash & other",
    "cash & equivalent",
    "cash and other",
    "cash & others",
    "debt, cash",
    "entry & exit",
    "large cap",
    "mid cap",
    "small cap",
    "industry",
    "market cap",
    "% of nav",
    "income distribution cum capital withdrawal",
    "idcw",
    "others",
    "certificate of deposit",
    "commercial paper",
    "treasury bill",
    "state government bond",
    "government bond",
    "corporate bond",
    "portfolio snapshot",
)

SCHEME_SEARCH_STOP_MARKERS = (
    "date of",
    "fund manager",
    "aum",
    "benchmark",
    "performance",
    "portfolio snapshot",
    "entry & exit load",
    "instrument type/issuer name",
)


class AxisAdapter(BaseAMCAdapter):
    amc_code = AMC_AXIS

    def parse_pdf_file_many(self, file_path: str, context: ParseContext) -> list[ParsedDocument]:
        documents: list[ParsedDocument] = []
        with fitz.open(file_path) as pdf:
            for page in pdf:
                parsed = _parse_axis_page_text(page.get_text("text") or "", context)
                if parsed:
                    documents.append(
                        ParsedDocument(
                            scheme_name=str(parsed.get("scheme_name") or ""),
                            report_month=parsed.get("report_month") or context.report_month,
                            holdings=parsed.get("holdings", []),
                            metrics=parsed.get("metrics", {}),
                            warnings=parsed.get("warnings", []),
                            confidence_score=float(parsed.get("confidence_score", 0.0)),
                        )
                    )
        return _dedupe_documents_by_scheme(documents)

    def parse_pdf_text_many(self, pdf_text: str, context: ParseContext) -> list[ParsedDocument]:
        return _parse_axis_pdf_text_many(pdf_text, context)

    def parse_holdings(
        self,
        excel_frames: list[pd.DataFrame],
        pdf_table_frames: list[pd.DataFrame],
        pdf_text: str,
        context: ParseContext,
    ) -> ParsedDocument:
        candidates: list[dict[str, Any]] = []

        if pdf_text:
            candidates.extend(_document_to_candidates(_parse_axis_pdf_text_many(pdf_text, context)))

        seen_pages: set[str] = set()
        for frame in [*excel_frames, *pdf_table_frames]:
            page_text = str(frame.attrs.get("page_text_full") or "") if frame is not None else ""
            page_number = str(frame.attrs.get("page_number") or "")
            page_key = f"{page_number}:{hash(page_text)}"
            if page_text and page_key not in seen_pages:
                seen_pages.add(page_key)
                parsed = _parse_axis_page_text(page_text, context)
                if parsed:
                    candidates.append(parsed)
                continue

            parsed = _parse_axis_frame(frame, context)
            if parsed:
                candidates.append(parsed)

        if not candidates:
            return ParsedDocument(
                scheme_name="",
                report_month=context.report_month,
                holdings=[],
                warnings=["axis_holdings_not_found_in_document"],
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


def _parse_axis_pdf_text_many(pdf_text: str, context: ParseContext) -> list[ParsedDocument]:
    lines = _clean_lines(pdf_text)
    candidates = _extract_axis_text_candidates(lines, context)
    documents = [
        ParsedDocument(
            scheme_name=str(candidate.get("scheme_name") or ""),
            report_month=candidate.get("report_month") or context.report_month,
            holdings=candidate.get("holdings", []),
            metrics=candidate.get("metrics", {}),
            warnings=candidate.get("warnings", []),
            confidence_score=float(candidate.get("confidence_score", 0.0)),
        )
        for candidate in candidates
    ]
    return _dedupe_documents_by_scheme(documents)


def _dedupe_documents_by_scheme(documents: list[ParsedDocument]) -> list[ParsedDocument]:
    by_scheme: dict[str, ParsedDocument] = {}
    for document in documents:
        key = _scheme_key(document.scheme_name)
        if not key:
            continue
        existing = by_scheme.get(key)
        if not existing or _document_selection_score(document) > _document_selection_score(existing):
            by_scheme[key] = document

    return sorted(by_scheme.values(), key=lambda item: item.scheme_name)


def _document_selection_score(document: ParsedDocument) -> float:
    total = float((document.metrics or {}).get("total_percent_aum") or 0.0)
    grand_total = (document.metrics or {}).get("grand_total_percent_aum")
    return _selection_score(document.holdings or [], total, grand_total)


def _parse_axis_page_text(page_text: str, context: ParseContext) -> dict[str, Any] | None:
    candidates = _extract_axis_text_candidates(_clean_lines(page_text), context)
    if not candidates:
        return None
    return max(candidates, key=lambda item: item.get("selection_score", 0.0))


def _extract_axis_text_candidates(lines: list[str], context: ParseContext) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for idx, line in enumerate(lines):
        if _normalize_line_key(line) != "grand total":
            continue

        grand_total = _parse_percent_line(_line_at(lines, idx + 1))
        start_idx = _find_holdings_start(lines, idx)
        if start_idx is None:
            continue

        scheme_name = _find_scheme_name_for_total(lines, idx, start_idx)
        if not scheme_name:
            continue

        parsed = _build_candidate_from_segment(
            scheme_name=scheme_name,
            segment=lines[start_idx:idx],
            grand_total=grand_total,
            context=context,
        )
        if parsed:
            candidates.append(parsed)
    return candidates


def _find_holdings_start(lines: list[str], grand_total_idx: int) -> int | None:
    lower_bound = max(0, grand_total_idx - 320)
    starts: list[int] = []
    for idx in range(lower_bound, grand_total_idx - 1):
        if not _is_portfolio_start_marker(lines[idx]):
            continue
        if _parse_percent_line(_line_at(lines, idx + 1)) is None:
            continue
        starts.append(idx)
    if not starts:
        return None
    return starts[0]


def _find_scheme_name_for_total(lines: list[str], grand_total_idx: int, start_idx: int) -> str:
    after_window = lines[grand_total_idx + 2 : min(len(lines), grand_total_idx + 150)]
    scheme = _first_axis_scheme_title(after_window)
    if scheme:
        return scheme

    before_window = lines[max(0, start_idx - 100) : start_idx]
    return _first_axis_scheme_title(reversed(before_window)) or ""


def _first_axis_scheme_title(lines: Any) -> str:
    for raw in lines:
        line = _clean_text(raw)
        if not line:
            continue
        if _is_scheme_search_stop(line):
            break
        if _looks_like_axis_scheme_title(line):
            return _normalize_scheme_title(line)
    return ""


def _build_candidate_from_segment(
    *,
    scheme_name: str,
    segment: list[str],
    grand_total: float | None,
    context: ParseContext,
) -> dict[str, Any] | None:
    raw_holdings: list[dict[str, Any]] = []
    buffer: list[str] = []

    for line in segment:
        percent = _parse_percent_line(line)
        if percent is None:
            if _should_keep_buffer_line(line):
                buffer.append(line)
            continue

        parsed = _holding_from_buffer(buffer, percent)
        if parsed:
            raw_holdings.append(parsed)
        buffer = []

    holdings = _dedupe_holdings(raw_holdings)
    if not holdings:
        return None

    computed_total = round(sum(float(row.get("percent_aum") or 0.0) for row in holdings), 6)
    validation_total = grand_total if grand_total is not None and _total_in_axis_band(grand_total) else computed_total
    warnings: list[str] = []

    if context.report_month is None:
        warnings.append("report_month_not_detected")
    if grand_total is None:
        warnings.append("grand_total_not_detected")
    if not _total_in_axis_band(validation_total):
        warnings.append("percent_aum_total_out_of_band")
        return None

    if _looks_crossed_scheme_block(scheme_name, holdings):
        warnings.append("axis_crossed_scheme_block")
        return None

    return {
        "scheme_name": scheme_name,
        "report_month": context.report_month,
        "holdings": holdings,
        "metrics": {
            "total_percent_aum": round(validation_total, 6),
            "computed_holdings_percent_aum": computed_total,
            "grand_total_percent_aum": grand_total,
        },
        "warnings": warnings,
        "confidence_score": _compute_confidence(holdings, context.report_month, validation_total, scheme_name),
        "selection_score": _selection_score(holdings, validation_total, grand_total),
    }


def _holding_from_buffer(buffer: list[str], percent: float) -> dict[str, Any] | None:
    cleaned = [_clean_text(line) for line in buffer]
    cleaned = [line for line in cleaned if line and not _is_non_holding_context(line)]
    if percent <= 0.0 or not cleaned:
        return None
    if _is_summary_or_noise_row(" ".join(cleaned)):
        return None

    split = _split_name_and_sector(cleaned)
    if not split:
        return None

    name, sector = split
    name = normalize_instrument_name(name)
    sector = normalize_instrument_name(sector) or None
    if _is_summary_or_noise_row(name):
        return None
    if sector and _is_summary_or_noise_row(sector):
        sector = None
    if sector and sector.lower() == "index":
        return None

    return {
        "instrument_name": name,
        "isin": None,
        "sector": sector,
        "percent_aum": round(percent, 6),
        "quantity": None,
        "market_value": None,
    }


def _split_name_and_sector(parts: list[str]) -> tuple[str, str | None] | None:
    if len(parts) < 2:
        return None

    sector_count = 1
    if len(parts) >= 3 and _line_continues_sector(parts[-2], parts[-1]):
        sector_count = 2

    name_parts = parts[:-sector_count]
    sector_parts = parts[-sector_count:]
    if not name_parts:
        return None
    return " ".join(name_parts), " ".join(sector_parts)


def _line_continues_sector(previous: str, current: str) -> bool:
    prev = previous.strip()
    cur = current.strip()
    if prev.endswith("&"):
        return True
    if cur.startswith("(") and cur.endswith(")"):
        return True
    return False


def _dedupe_holdings(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for row in rows:
        name_key = re.sub(r"\s+", " ", str(row.get("instrument_name") or "").strip().lower())
        sector_key = re.sub(r"\s+", " ", str(row.get("sector") or "").strip().lower())
        key = f"{name_key}|{sector_key}"
        if not name_key:
            continue
        existing = deduped.get(key)
        if not existing or float(row.get("percent_aum") or 0.0) > float(existing.get("percent_aum") or 0.0):
            deduped[key] = row
    return list(deduped.values())


def _parse_axis_frame(frame: pd.DataFrame, context: ParseContext) -> dict[str, Any] | None:
    if frame is None or frame.empty:
        return None

    rows = frame.where(pd.notna(frame), None).values.tolist()
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
        if percent is None or percent <= 0.0 or percent > 100.0:
            continue

        sector = normalize_instrument_name(_get_row_cell(row, headers, "sector")) or None
        raw_components.append(
            {
                "instrument_name": instrument_name,
                "isin": _normalize_isin(_get_row_cell(row, headers, "isin")),
                "sector": sector,
                "percent_aum": percent,
                "quantity": _parse_number(_get_row_cell(row, headers, "quantity")),
                "market_value": _parse_number(_get_row_cell(row, headers, "market_value")),
            }
        )

    holdings = _dedupe_holdings(raw_components)
    if not holdings:
        return None

    total_percent = round(sum(float(row.get("percent_aum") or 0.0) for row in holdings), 6)
    if not _total_in_axis_band(total_percent):
        return None

    resolved_scheme = scheme_name or "Axis Mutual Fund"
    return {
        "scheme_name": resolved_scheme,
        "report_month": report_month,
        "holdings": holdings,
        "metrics": {"total_percent_aum": total_percent},
        "warnings": [] if report_month else ["report_month_not_detected"],
        "confidence_score": _compute_confidence(holdings, report_month, total_percent, resolved_scheme),
        "selection_score": _selection_score(holdings, total_percent, total_percent),
    }


def _find_header_row(rows: list[list[object]]) -> tuple[int | None, list[str]]:
    for idx, row in enumerate(rows[:50]):
        normalized = [_normalize_axis_header_cell(cell) for cell in row]
        has_instrument = "instrument_name" in normalized or any("instrument" in str(cell).lower() for cell in row)
        has_percent = "percent_aum" in normalized or any("% of nav" in str(cell).lower() or "% to nav" in str(cell).lower() for cell in row)
        if has_instrument and has_percent:
            return idx, normalized
    return None, []


def _normalize_axis_header_cell(cell: object) -> str:
    base = normalize_column_name(cell)
    raw = str(cell or "").strip().lower()
    if "name of the instrument" in raw or "instrument" in raw or "issuer" in raw:
        return "instrument_name"
    if "isin" in raw:
        return "isin"
    if "% of nav" in raw or "% to nav" in raw or "% to net assets" in raw or "% to aum" in raw:
        return "percent_aum"
    if "rating" in raw or "industry" in raw:
        return "sector"
    if "quantity" in raw:
        return "quantity"
    if "market value" in raw:
        return "market_value"
    return base


def _get_row_cell(row: list[object], headers: list[str], key: str) -> object:
    for idx, header in enumerate(headers):
        if header != key or idx >= len(row):
            continue
        value = row[idx]
        if value is None:
            continue
        if str(value).strip():
            return value
    return None


def _extract_scheme_name(rows: list[list[object]]) -> str:
    for row in rows[:40]:
        for cell in row:
            text = _clean_text(cell)
            if _looks_like_axis_scheme_title(text):
                return _normalize_scheme_title(text)
    return ""


def _extract_report_month(rows: list[list[object]]) -> date | None:
    for row in rows[:40]:
        for idx, cell in enumerate(row):
            text = str(cell or "").strip()
            if "as on" not in text.lower() and not re.search(r"\b20\d{2}\b", text):
                continue
            for tail in [cell, *row[idx + 1 :]]:
                resolved = _parse_date_value(tail)
                if resolved:
                    return resolved
    return None


def _parse_date_value(value: object) -> date | None:
    if value in (None, ""):
        return None
    if hasattr(value, "year") and hasattr(value, "month"):
        return date(int(value.year), int(value.month), 1)

    text = str(value).strip().replace("/", "-")
    if not text:
        return None

    match = re.search(r"\b\d{4}-\d{2}-\d{2}\b", text)
    if match:
        text = match.group(0)
    for pattern in ("%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y", "%d-%B-%Y", "%B %d, %Y", "%b %Y", "%B %Y"):
        try:
            parsed = datetime.strptime(text, pattern)
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            continue
    return None


def _clean_lines(text: str) -> list[str]:
    return [_clean_text(line) for line in str(text or "").splitlines() if _clean_text(line)]


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def _line_at(lines: list[str], index: int) -> str:
    if 0 <= index < len(lines):
        return lines[index]
    return ""


def _normalize_line_key(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower())


def _parse_percent_line(value: object) -> float | None:
    text = _clean_text(value)
    if not PERCENT_LINE_PATTERN.fullmatch(text):
        return None
    return _parse_number(text)


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
        return num if math.isfinite(num) else None
    text = str(value).strip().replace(",", "").replace("%", "")
    if not text or text.lower() in {"-", "--", "na", "n/a", "nan"}:
        return None
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _normalize_isin(value: object) -> str | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    match = ISIN_PATTERN.search(text)
    return match.group(0) if match else None


def _is_portfolio_start_marker(value: str) -> bool:
    return _normalize_line_key(value).strip(":") in PORTFOLIO_START_MARKERS


def _is_summary_or_noise_row(name: str) -> bool:
    low = _normalize_line_key(name).strip(":")
    if not low:
        return True
    if any(low == marker or low.startswith(f"{marker} ") for marker in SUMMARY_ROW_MARKERS):
        return True
    if re.fullmatch(r"[\d.\-()% ,]+", low):
        return True
    return False


def _is_non_holding_context(value: str) -> bool:
    low = _normalize_line_key(value)
    if low in {"mp", "g", "portfolio", "portfolio snapshot"}:
        return True
    if low.startswith("regular plan") or low.startswith("direct plan"):
        return True
    if low.startswith("idcw") or "income distribution" in low:
        return True
    return False


def _should_keep_buffer_line(value: str) -> bool:
    text = _clean_text(value)
    if not text:
        return False
    if _normalize_line_key(text) == "grand total":
        return False
    return True


def _looks_like_axis_scheme_title(value: str) -> bool:
    text = _clean_text(value)
    if not text.startswith("AXIS "):
        return False
    if " - " in text and not text.upper().endswith("PLAN"):
        return False
    if "..." in text:
        return False
    return bool(SCHEME_TITLE_PATTERN.search(text))


def _normalize_scheme_title(value: str) -> str:
    text = re.sub(r"\s+\(Formerly.*$", "", _clean_text(value), flags=re.IGNORECASE)
    text = re.split(r"\s{2,}", text)[0].strip(" -")
    return text.title().replace(" Etf", " ETF").replace(" Fof", " FOF").replace(" Sdl", " SDL").replace(" Aaa", " AAA")


def _is_scheme_search_stop(value: str) -> bool:
    low = _normalize_line_key(value)
    return any(marker in low for marker in SCHEME_SEARCH_STOP_MARKERS)


def _scheme_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _total_in_axis_band(total: float | None) -> bool:
    return total is not None and 95.0 <= float(total) <= 105.0


def _looks_crossed_scheme_block(scheme_name: str, holdings: list[dict[str, Any]]) -> bool:
    low_scheme = str(scheme_name or "").lower()
    if "money market" in low_scheme:
        equity_names = {"reliance industries limited", "eternal limited", "infosys limited", "bharti airtel limited"}
        names = {str(row.get("instrument_name") or "").strip().lower() for row in holdings}
        if len(equity_names & names) >= 2:
            return True
    return False


def _compute_confidence(holdings: list[dict[str, Any]], report_month: date | None, total_percent: float, scheme_name: str) -> float:
    if not holdings:
        return 0.0
    score = 55.0
    score += min(20.0, len(holdings) * 0.4)
    if report_month:
        score += 10.0
    if _total_in_axis_band(total_percent):
        score += 10.0
    if "axis" in (scheme_name or "").lower():
        score += 5.0
    return round(min(score, 99.0), 2)


def _selection_score(holdings: list[dict[str, Any]], total_percent: float, grand_total: float | None) -> float:
    score = float(len(holdings))
    if _total_in_axis_band(total_percent):
        score += 50.0
    if grand_total is not None:
        score += 10.0
    return score


def _document_to_candidates(documents: list[ParsedDocument]) -> list[dict[str, Any]]:
    return [
        {
            "scheme_name": document.scheme_name,
            "report_month": document.report_month,
            "holdings": document.holdings,
            "metrics": document.metrics,
            "warnings": document.warnings,
            "confidence_score": document.confidence_score,
            "selection_score": _selection_score(
                document.holdings,
                float((document.metrics or {}).get("total_percent_aum") or 0.0),
                (document.metrics or {}).get("grand_total_percent_aum"),
            ),
        }
        for document in documents
    ]
