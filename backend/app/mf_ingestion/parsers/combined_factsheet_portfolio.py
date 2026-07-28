from __future__ import annotations

import re
from datetime import date

from app.mf_ingestion.normalizers.instrument_normalizer import normalize_instrument_name
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument
from app.mf_ingestion.parsers.pdf_text_parser import PDFTextParser

NUMBER_PATTERN = re.compile(r"^-?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?$")
SECURITY_PATTERN = re.compile(
    r"(?:\b(?:ltd|limited|bank|bk|corporation|industries|enterprises|technologies)\b|"
    r"\b(?:etf|reit|invIT|index-[A-Z0-9]+|direct growth|goi|sdl|g-sec|t[\s-]?bill)\b|"
    r"\d+(?:\.\d+)?%\s+)",
    re.IGNORECASE,
)
SUMMARY_MARKERS = (
    "grand total",
    "total",
    "sub total",
    "subtotal",
    "equity & equity related",
    "equity & equity related - total",
    "equity and equity related",
    "mutual fund units",
    "mutual fund units - total",
    "futures",
    "triparty repo",
    "treps",
    "cblo/repo/treps",
    "net current assets",
    "net receivables",
)
HEADER_MARKERS = (
    "issuer/instrument",
    "% to net assets",
    "scrip",
    "weightage (%)",
    "portfolio",
)


def parse_combined_factsheet_pdf(
    file_path: str,
    context: ParseContext,
    *,
    scheme_prefixes: tuple[str, ...],
    continue_after_grand_total: bool = False,
    extract_sector_allocations: bool = False,
) -> list[ParsedDocument]:
    pages = PDFTextParser().extract_pages(file_path)
    records: list[ParsedDocument] = []
    seen: set[str] = set()
    for page_text in pages:
        parsed = parse_combined_factsheet_page(
            page_text,
            context,
            scheme_prefixes=scheme_prefixes,
            continue_after_grand_total=continue_after_grand_total,
            extract_sector_allocations=extract_sector_allocations,
        )
        if not parsed or not parsed.holdings:
            continue
        key = _scheme_key(parsed.scheme_name)
        if key in seen:
            continue
        seen.add(key)
        records.append(parsed)
    return records


def parse_combined_factsheet_page(
    page_text: str,
    context: ParseContext,
    *,
    scheme_prefixes: tuple[str, ...],
    continue_after_grand_total: bool = False,
    extract_sector_allocations: bool = False,
) -> ParsedDocument | None:
    lines = [_clean(line) for line in str(page_text or "").splitlines()]
    lines = [line for line in lines if line]
    scheme_name = _find_scheme_name(lines, scheme_prefixes)
    portfolio_start = _find_portfolio_start(lines)
    if not scheme_name or portfolio_start is None:
        return None
    body_start = portfolio_start
    if continue_after_grand_total:
        equity_starts = [
            index
            for index, line in enumerate(lines[:portfolio_start])
            if line.lower() in {"equity & equity related", "equity and equity related"}
        ]
        if equity_starts:
            body_start = equity_starts[-1]

    holdings: dict[str, dict] = {}
    current_sector: str | None = None
    pending: list[str] = []
    for line in lines[body_start + 1 :]:
        low = line.lower()
        if low.startswith("sector allocation"):
            break
        if low.startswith("grand total") and not continue_after_grand_total:
            break
        if any(marker in low for marker in HEADER_MARKERS):
            pending.clear()
            continue

        value = _number(line)
        if value is None:
            pending.append(line)
            pending = pending[-3:]
            continue

        candidate = _candidate_name(pending)
        pending.clear()
        if not candidate or not 0 < value <= 100:
            continue

        normalized = normalize_instrument_name(candidate)
        low_candidate = normalized.lower()
        if _is_summary(low_candidate):
            if low_candidate.startswith("grand total"):
                current_sector = None
            continue
        if _looks_like_security(normalized):
            key = _scheme_key(normalized)
            item = {
                "instrument_name": normalized,
                "isin": None,
                "sector": current_sector,
                "percent_aum": round(value, 6),
                "quantity": None,
                "market_value": None,
            }
            previous = holdings.get(key)
            if not previous or value > float(previous["percent_aum"]):
                holdings[key] = item
        elif len(normalized) <= 90:
            current_sector = normalized

    rows = list(holdings.values())
    if not rows:
        return None
    total_percent = round(sum(float(row["percent_aum"]) for row in rows), 6)
    warnings: list[str] = []
    if not 70.0 <= total_percent <= 115.0:
        warnings.append("percent_aum_total_out_of_band")
    sector_allocations: list[dict] = []
    if extract_sector_allocations:
        sector_allocations, sector_issue = _extract_sector_allocations(lines)
        if sector_issue:
            warnings.append(sector_issue)
    metrics = {"total_percent_aum": total_percent}
    if sector_allocations:
        metrics["sector_allocations"] = sector_allocations
        metrics["sector_allocation_total"] = round(
            sum(float(row["weight_pct"]) for row in sector_allocations),
            6,
        )
    return ParsedDocument(
        scheme_name=scheme_name,
        report_month=context.report_month or _find_report_month(lines),
        holdings=rows,
        metrics=metrics,
        warnings=warnings,
        confidence_score=_confidence(rows, context.report_month, total_percent),
    )


def _find_scheme_name(lines: list[str], prefixes: tuple[str, ...]) -> str:
    lowered_prefixes = tuple(prefix.lower() for prefix in prefixes)
    for line in lines[:80]:
        low = line.lower()
        if not low.startswith(lowered_prefixes):
            continue
        if not any(token in low for token in (" fund", " etf", " fof")):
            continue
        if len(line) > 150 or any(token in low for token in ("mutual fund", "managed by", "performance")):
            continue
        return line
    return ""


def _find_portfolio_start(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        low = line.lower()
        if low == "portfolio" or low.startswith("portfolio (as on") or low.startswith("portfolio (as of"):
            return index
    return None


def _candidate_name(pending: list[str]) -> str:
    meaningful = [
        line
        for line in pending
        if not any(marker in line.lower() for marker in HEADER_MARKERS)
    ]
    if not meaningful:
        return ""
    for width in range(1, min(3, len(meaningful)) + 1):
        candidate = " ".join(meaningful[-width:])
        if _looks_like_security(candidate):
            return candidate
    return meaningful[-1]


def _looks_like_security(value: str) -> bool:
    return bool(SECURITY_PATTERN.search(value))


def _is_summary(value: str) -> bool:
    return any(value == marker or value.startswith(f"{marker} ") for marker in SUMMARY_MARKERS)


def _number(value: str) -> float | None:
    text = value.replace(",", "").replace("%", "").strip()
    if not NUMBER_PATTERN.fullmatch(value.replace(",", "").strip()):
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _find_report_month(lines: list[str]) -> date | None:
    pattern = re.compile(
        r"\b(?:as\s+on\s+)?(?P<day>\d{1,2})[-\s]+"
        r"(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[-\s,]+"
        r"(?P<year>20\d{2})\b",
        re.IGNORECASE,
    )
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
    for line in lines:
        match = pattern.search(line)
        if match:
            return date(int(match.group("year")), months[match.group("month").lower()[:3]], 1)
    return None


def _extract_sector_allocations(
    lines: list[str],
) -> tuple[list[dict], str | None]:
    marker = next(
        (
            index
            for index, line in enumerate(lines)
            if line.lower().startswith("sector allocation")
            and any(
                "industry classification as recommended by amfi" in candidate.lower()
                for candidate in lines[index : index + 15]
            )
        ),
        None,
    )
    if marker is None:
        return [], None

    evidence_window = lines[marker : marker + 15]
    industry_index = next(
        (
            marker + offset
            for offset, line in enumerate(evidence_window)
            if "industry classification as recommended by amfi" in line.lower()
        ),
        None,
    )
    if industry_index is None:
        return [], None

    index = industry_index + 1
    while index < len(lines) and not _is_percent_line(lines[index]):
        index += 1

    weights: list[float] = []
    while index < len(lines) and _is_percent_line(lines[index]):
        value = _number(lines[index])
        if value is not None and 0 < value <= 100:
            weights.append(round(value, 6))
        index += 1

    raw_names: list[str] = []
    stop_markers = (
        "base expense ratio",
        "total ter",
        "exit load",
        "minimum application amount",
        "scheme performance",
        "sip performance",
        "performance -",
    )
    while index < len(lines):
        line = lines[index]
        low = line.lower()
        if low.startswith(stop_markers):
            break
        if line and not _is_percent_line(line):
            raw_names.append(line)
            merged_names = _merge_sector_name_lines(raw_names)
            next_line = lines[index + 1] if index + 1 < len(lines) else ""
            if (
                len(merged_names) == len(weights)
                and not _is_sector_name_continuation(merged_names[-1], next_line)
            ):
                break
            if len(merged_names) > len(weights):
                break
        index += 1

    names = _merge_sector_name_lines(raw_names)
    if not weights or len(names) != len(weights):
        return [], "sector_allocation_count_mismatch"

    total = round(sum(weights), 6)
    if not 5.0 <= total <= 105.0:
        return [], "sector_allocation_total_out_of_band"

    return [
        {"sector": normalize_instrument_name(_repair_sector_name(name)), "weight_pct": weight}
        for name, weight in zip(names, weights)
        if normalize_instrument_name(_repair_sector_name(name))
    ], None


def _is_percent_line(value: str) -> bool:
    return str(value or "").strip().endswith("%") and _number(value) is not None


def _merge_sector_name_lines(lines: list[str]) -> list[str]:
    merged: list[str] = []
    for line in lines:
        cleaned = _clean(line)
        if not cleaned:
            continue
        if merged and _is_sector_name_continuation(merged[-1], cleaned):
            separator = " " if merged[-1].endswith("&") else (
                "" if merged[-1][-1:].isalnum() else " "
            )
            merged[-1] = f"{merged[-1]}{separator}{cleaned}"
        else:
            merged.append(cleaned)
    return merged


def _is_sector_name_continuation(previous: str, current: str) -> bool:
    cleaned = _clean(current)
    return bool(cleaned) and (cleaned[:1].islower() or previous.endswith("&"))


def _repair_sector_name(value: str) -> str:
    repaired = re.sub(r"\bSo(?:ti)?ware\b", "Software", value, flags=re.IGNORECASE)
    repaired = re.sub(
        r"\bPharmaceu(?:ti)?cals\b",
        "Pharmaceuticals",
        repaired,
        flags=re.IGNORECASE,
    )
    return repaired


def _confidence(holdings: list[dict], report_month: date | None, total_percent: float) -> float:
    score = 55.0 + min(25.0, len(holdings) * 0.5)
    if report_month:
        score += 10.0
    if 70.0 <= total_percent <= 115.0:
        score += 10.0
    return round(min(score, 99.0), 2)


def _clean(value: object) -> str:
    return " ".join(
        str(value or "")
        .replace("\u001f", "ti")
        .replace("\u008f", "ti")
        .replace("\u008b", "ft")
        .replace("\u008e", "ft")
        .replace("\ufb01", "fi")
        .replace("\ufb02", "fl")
        .split()
    )


def _scheme_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()
