from __future__ import annotations

import re
from collections import Counter
from datetime import date

from app.mf_ingestion.normalizers.instrument_normalizer import normalize_instrument_name
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument
from app.mf_ingestion.parsers.pdf_text_parser import PDFTextParser

NUMBER_PATTERN = re.compile(r"^-?\d{1,3}(?:,\d{3})*(?:\.\d+)?%?$")
SECURITY_PATTERN = re.compile(
    # "trust" catches PTC (pass-through certificate) securitisation trusts and
    # InvIT-adjacent trust structures, e.g. "PTC SIDDHIVINAYAK SECURITISATION
    # TRUST" / "CUBE HIGHWAYS TRUST" -- common debt-fund holdings that otherwise
    # match none of the other markers and get silently misclassified as a sector
    # label instead of a holding row.
    r"(?:\b(?:ltd|limited|bank|bk|corporation|industries|enterprises|technologies|trust)\b|"
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
)
# These print as a bare category name directly followed by its own single
# percent_aum value, with no further row-level breakdown underneath -- e.g. "Net
# Current Assets/(Liabilities)" / "2.60", "Triparty Repo" / "0.22" (observed live
# in the real Kotak Bond Short Term Fund page: both were previously in
# SUMMARY_MARKERS and treated as pure section headers to discard, silently
# dropping the only row that ever carries their percentage -- the exact same
# class of bug already fixed for "TREPS" in generic_portfolio_adapter.py's
# SUMMARY_MARKERS, just not synced to this separate parser). Matched only via
# _is_standalone_category_holding, which also guards against a genuine
# "<category> - Total" redundant line for AMCs whose layout does break these out
# into their own row-level detail.
STANDALONE_CATEGORY_HOLDINGS = (
    "triparty repo",
    "treps",
    "cblo/repo/treps",
    "net current assets",
    "net current assets/(liabilities)",
    "net receivables",
    "net receivables/payables",
)
HEADER_MARKERS = (
    "issuer/instrument",
    "% to net assets",
    "scrip",
    "weightage (%)",
    "portfolio",
)
PORTFOLIO_STOP_MARKERS = (
    "base expense ratio",
    "scheme performance",
    "sip performance",
    "systematic investment plan",
    "performance -",
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
    records_by_scheme: dict[str, ParsedDocument] = {}
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
        existing = records_by_scheme.get(key)
        if existing is None or _record_quality(parsed) > _record_quality(existing):
            records_by_scheme[key] = parsed
    return list(records_by_scheme.values())


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
    portfolio_starts = _find_portfolio_starts(lines)
    if not scheme_name or not portfolio_starts:
        return None

    body_starts = list(portfolio_starts)
    if continue_after_grand_total:
        body_starts.extend(
            index
            for index, line in enumerate(lines[: max(portfolio_starts) + 1])
            if line.lower() in {"equity & equity related", "equity and equity related"}
        )
        body_starts.extend(
            index
            for index, line in enumerate(lines[: max(portfolio_starts) + 1])
            if line.lower().startswith("scan to invest now")
        )

    candidates = [
        _extract_portfolio_candidate(
            lines,
            body_start,
            continue_after_grand_total=continue_after_grand_total,
        )
        for body_start in sorted(set(body_starts))
    ]
    candidates = [candidate for candidate in candidates if candidate[0]]
    if not candidates:
        return None
    rows, total_percent = _merge_portfolio_candidates(candidates)

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


def _extract_portfolio_candidate(
    lines: list[str],
    body_start: int,
    *,
    continue_after_grand_total: bool,
) -> tuple[list[dict], float]:
    holdings: list[dict] = []
    current_sector: str | None = None
    pending: list[str] = []
    for line in lines[body_start + 1 :]:
        low = line.lower()
        if low.startswith("sector allocation"):
            pending.clear()
            continue
        if low.startswith(PORTFOLIO_STOP_MARKERS):
            break
        if low.startswith("grand total") and not continue_after_grand_total:
            break
        if any(marker in low for marker in HEADER_MARKERS):
            pending.clear()
            continue

        value = _number(line)
        if value is None:
            if _is_summary(low):
                pending.clear()
                if low.startswith("grand total"):
                    current_sector = None
                continue
            pending.append(line)
            # Wide enough for the longest real issuer names in these tables (e.g.
            # "NATIONAL BANK FOR FINANCING / INFRASTRUCTURE AND / DEVELOPMENT (^)"
            # spans 3 lines before its rating line) without spilling into the
            # previous row -- pending is cleared at every row/header boundary below,
            # so a wider cap can't leak content across rows.
            pending = pending[-6:]
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
        if _looks_like_security(normalized) or _is_standalone_category_holding(low_candidate):
            # Keep every row instead of deduping by normalized name: these tables
            # print no ISIN, so two genuinely different bonds from the same issuer
            # at the same rating (common -- multiple tranches/series) can share the
            # exact same printed text apart from a cosmetic "(^)" marker that
            # normalization treats as noise. Deduping by name silently dropped the
            # smaller of the two, understating the fund's true holdings coverage
            # (observed: Kotak Bond Short Term Fund staged at 83% of AUM against a
            # source PDF that sums to 100%).
            holdings.append(
                {
                    "instrument_name": normalized,
                    "isin": None,
                    "sector": current_sector,
                    "percent_aum": round(value, 6),
                    "quantity": None,
                    "market_value": None,
                }
            )
        elif len(normalized) <= 90:
            current_sector = normalized

    total_percent = round(sum(float(row["percent_aum"]) for row in holdings), 6)
    return holdings, total_percent


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


def _find_portfolio_starts(lines: list[str]) -> list[int]:
    starts: list[int] = []
    for index, line in enumerate(lines):
        low = line.lower()
        if low.startswith("portfolio (as on") or low.startswith("portfolio (as of"):
            starts.append(index)
            continue
        if low != "portfolio":
            continue
        evidence = " ".join(candidate.lower() for candidate in lines[index + 1 : index + 10])
        if "issuer/instrument" in evidence or "% to net assets" in evidence:
            starts.append(index)
    return starts


def _portfolio_quality(total_percent: float, holding_count: int) -> tuple[int, float, int]:
    return (
        int(85.0 <= total_percent <= 115.0),
        -abs(total_percent - 100.0),
        holding_count,
    )


def _merge_portfolio_candidates(candidates: list[tuple[list[dict], float]]) -> tuple[list[dict], float]:
    """Each body_start re-scans this page's single portfolio table from a different
    anchor line: the literal "Portfolio" heading, or -- for AMCs like Kotak whose
    factsheets print the table across side-by-side page columns -- extra anchors at
    "Equity & Equity Related" and "Scan to Invest Now" (see continue_after_grand_total
    callers). Picking only the single best-scoring candidate (the old `max(...,
    key=_portfolio_quality)`) throws away any row a weaker-scoring candidate captured
    that the winner missed -- e.g. a two-column layout where no single anchor's
    forward scan covers both columns, undercounting the true total (observed: Kotak
    Bond Short Term Fund staged at 83% of AUM against a source PDF that sums to
    100%). Merge every candidate's holdings instead of discarding whichever one
    scores worse -- but never compare rows *across* candidates to decide which to
    keep. Verified live against the real Kotak Bond Short Term Fund page: its two
    anchors ("Scan to Invest Now" and "PORTFOLIO", adjacent) each independently
    scan the *entire* table and produce identical results, so this isn't really a
    complementary-partial-coverage case at all. Deduping across candidates by
    instrument key -- or even by (key, value) pair -- broke on it anyway: these
    tables print no ISIN, so two *different* bonds from the same issuer at the
    same rating share a normalized name, and here two of them (two separate "TATA
    CAPITAL LTD" holdings) even coincidentally share the same percent_aum (0.70),
    so a value-aware pairwise dedup still collapsed them into one. Instead, decide
    per instrument key which *single* candidate's account of that key to trust --
    picking whichever candidate observed the most rows under that key -- and take
    all of that one candidate's rows for it. Candidates that scan the same table
    (the common case here) agree on the count and simply reproduce each other;
    a candidate whose scan range doesn't reach a given part of the table
    contributes a count of 0 for those keys and is skipped in favour of the one
    that does, still recovering genuinely complementary partial coverage without
    ever comparing two different real rows to each other."""
    rows_by_candidate = [rows for rows, _ in candidates]
    counts_by_candidate = [
        Counter(_scheme_key(str(row["instrument_name"])) for row in rows)
        for rows in rows_by_candidate
    ]
    all_keys = list(dict.fromkeys(key for counts in counts_by_candidate for key in counts))

    merged_rows: list[dict] = []
    for key in all_keys:
        best_index = max(range(len(rows_by_candidate)), key=lambda i: counts_by_candidate[i][key])
        merged_rows.extend(
            row
            for row in rows_by_candidate[best_index]
            if _scheme_key(str(row["instrument_name"])) == key
        )
    total_percent = round(sum(float(row["percent_aum"]) for row in merged_rows), 6)
    return merged_rows, total_percent


def _record_quality(record: ParsedDocument) -> tuple[int, float, int]:
    total_percent = float(record.metrics.get("total_percent_aum") or 0.0)
    return _portfolio_quality(total_percent, len(record.holdings))


def _candidate_name(pending: list[str]) -> str:
    meaningful = [
        line
        for line in pending
        if not any(marker in line.lower() for marker in HEADER_MARKERS)
    ]
    if not meaningful:
        return ""
    # Use the full pending window whenever any of it looks like a security --
    # SECURITY_PATTERN.search() matches anywhere in the string, so this doesn't
    # require the trigger word to be at the end. The previous shortest-width-first
    # loop returned as soon as e.g. just "CORPORATION LTD. (^) ICRA AAA" matched,
    # silently dropping the preceding "HOUSING & URBAN DEVELOPMENT" line that
    # actually identified the issuer -- real PDF observed: HOUSING & URBAN
    # DEVELOPMENT CORPORATION LTD. came out as just "CORPORATION LTD. (^) ICRA
    # AAA", losing the distinguishing part of the name.
    full = " ".join(meaningful)
    if _looks_like_security(full):
        return full
    return meaningful[-1]


def _looks_like_security(value: str) -> bool:
    return bool(SECURITY_PATTERN.search(value))


def _is_standalone_category_holding(value: str) -> bool:
    # Excludes anything containing "total" so a "<category> - Total" redundant
    # line (an AMC layout that DOES break the category into its own row-level
    # detail, unlike this one) isn't double-counted alongside the real rows.
    if "total" in value:
        return False
    return any(
        value == marker or value.startswith(f"{marker} ") or value.startswith(f"{marker}/")
        for marker in STANDALONE_CATEGORY_HOLDINGS
    )


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
