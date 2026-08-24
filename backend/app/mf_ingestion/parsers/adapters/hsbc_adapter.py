from __future__ import annotations

import re
from collections import defaultdict
from typing import Any

import pandas as pd

from app.mf_ingestion.constants import AMC_HSBC
from app.mf_ingestion.normalizers.instrument_normalizer import normalize_instrument_name
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument
from app.mf_ingestion.parsers.combined_factsheet_portfolio import parse_combined_factsheet_page
from app.mf_ingestion.parsers.pdf_text_parser import PDFTextParser


HOLDING_LINE_PATTERN = re.compile(
    r"^(?P<name>.+?)(?:\s+(?P<cap>Large Cap|Mid Cap|Small Cap|Unlisted))?\s+"
    r"(?P<weight>\d+\.\d+)%\s*$",
    re.IGNORECASE,
)

# HSBC's PDF uses positioned text rather than a machine-readable table. These markers
# cover issuers that do not carry a company suffix (SIDBI, NABARD and T-bills).
HSBC_EXTRA_SECURITY_PATTERNS = (
    "mutual fund", "gold", "gif", "eq ", "s1 dis", "sovereign", "treasury",
    "t-bill", "t bill", "commercial paper", "certificate of deposit", "repo",
    "sdl", "goi", "sidbi", "nabard", "aif", "zcb",
)
HSBC_EXCLUDED_SECURITY_NAMES = (
    "mutual fund units", "mutual fund", "money market instruments",
    "certificate of deposit", "commercial paper", "government securities",
    "corporate bonds / debentures", "reverse repo", "reverse repos",
    "treasury bills", "alternative investment funds (aif)",
)
HSBC_HEADER_FRAGMENTS = {
    "issuer", "rating", "sector", "market cap/ ratings", "market cap/ratings",
    "market cap/", "ratings", "industry/ rating", "industry/rating", "industry/",
    "% to net assets", "% to net", "% to", "net", "net assets", "assets", "asset",
    "(hedge)", "(unhedge)",
}
HSBC_STOP_MARKERS = ("total net assets as on", "total net assets as of", "total net assets")


class HSBCAdapter(GenericPortfolioAdapter):
    amc_code = AMC_HSBC
    scheme_markers = ("hsbc ",)

    def parse_pdf_file_many(self, file_path: str, context: ParseContext) -> list[ParsedDocument]:
        """Parse HSBC's one-scheme-per-page ``The Asset`` PDF.

        HSBC renders the portfolio as positioned text, so pdfplumber table frames contain
        chart columns and page numbers instead of scheme/issuer rows. Reading page text
        after the issuer header keeps the table bounded at Total Net Assets.
        """
        records: list[ParsedDocument] = []
        for page_text in PDFTextParser().extract_pages(file_path):
            prepared = _prepare_hsbc_page(page_text)
            if not prepared:
                continue
            scheme_name, prepared_text = prepared
            if _scheme_key(scheme_name) == _scheme_key("HSBC Arbitrage Fund"):
                parsed = _parse_arbitrage_page(prepared_text, scheme_name, context)
            else:
                parsed = parse_combined_factsheet_page(
                    prepared_text,
                    context,
                    scheme_prefixes=("HSBC",),
                    continue_after_grand_total=False,
                    extract_sector_allocations=False,
                    extra_security_patterns=HSBC_EXTRA_SECURITY_PATTERNS,
                    excluded_security_names=HSBC_EXCLUDED_SECURITY_NAMES,
                )
            if parsed and parsed.holdings:
                records.append(_add_sector_metrics(parsed))
        return records

    def parse_pdf_frame_many(self, frame: pd.DataFrame, context: ParseContext) -> list[ParsedDocument]:
        # Keep a safe fallback for review tools that pass an already extracted frame.
        generic_docs = super().parse_pdf_frame_many(frame, context)
        if generic_docs and any(doc.holdings for doc in generic_docs):
            return [_add_sector_metrics(doc) for doc in generic_docs]

        page_head = str(frame.attrs.get("page_text_head") or "").strip()
        scheme_name = next((line.strip() for line in page_head.split("\n") if line.strip()), "")
        holdings: list[dict[str, Any]] = []
        current_sector = "Equity"
        for _, row in frame.iterrows():
            row_str = "\n".join(
                str(value) for value in row if pd.notna(value) and str(value).strip()
            )
            for line in row_str.split("\n"):
                line = line.strip()
                if not line:
                    continue
                match = HOLDING_LINE_PATTERN.match(line)
                if match:
                    name = normalize_instrument_name(match.group("name"))
                    if not name or name.lower().startswith("total"):
                        continue
                    holdings.append(_holding(name, float(match.group("weight")), current_sector))
                elif len(line) > 2 and not re.search(r"\d+\.\d+%", line):
                    current_sector = line
        if not holdings:
            return []
        return [_add_sector_metrics(ParsedDocument(
            scheme_name=scheme_name,
            report_month=context.report_month,
            holdings=holdings,
        ))]


def _prepare_hsbc_page(page_text: str) -> tuple[str, str] | None:
    lines = [" ".join(str(line or "").split()) for line in str(page_text or "").splitlines()]
    lines = [line for line in lines if line]
    if "fund details" not in " ".join(lines).lower():
        return None

    heading = _find_scheme_heading(lines)
    if not heading:
        return None
    heading_index, scheme_name, heading_line_count = heading
    lines = lines[:heading_index] + [scheme_name] + lines[heading_index + heading_line_count:]

    issuer_index = _find_issuer_header(lines)
    if issuer_index is None:
        return None
    content_start = issuer_index + 1
    while content_start < len(lines) and _is_hsbc_header_fragment(lines[content_start]):
        content_start += 1

    prepared = lines[:issuer_index] + ["Portfolio", "Issuer/Instrument", "% to Net Assets"] + lines[content_start:]
    prepared = [
        f"Grand Total {line}" if line.lower().startswith(HSBC_STOP_MARKERS) else line
        for line in prepared
    ]
    return scheme_name, "\n".join(prepared)


def _find_scheme_heading(lines: list[str]) -> tuple[int, str, int] | None:
    for index, line in enumerate(lines[:40]):
        if not line.lower().startswith("hsbc "):
            continue
        parts = [line]
        if not _has_product_token(line):
            for candidate in lines[index + 1:index + 8]:
                if candidate.lower().startswith(("an ", "the ", "investment objective", "fund details")):
                    break
                parts.append(candidate)
                if _has_product_token(candidate):
                    break
        name = re.sub(r"\s*[\*\^$#@~§]+$", "", " ".join(parts)).strip()
        if _has_product_token(name):
            return index, name, len(parts)
    return None


def _find_issuer_header(lines: list[str]) -> int | None:
    for index, line in enumerate(lines):
        if line.lower() != "issuer":
            continue
        if "net asset" in " ".join(lines[index:index + 12]).lower():
            return index
    return None


def _is_hsbc_header_fragment(value: str) -> bool:
    low = " ".join(str(value or "").lower().split())
    return low in HSBC_HEADER_FRAGMENTS or low.startswith("% to net")


def _has_product_token(value: str) -> bool:
    return bool(re.search(r"\b(?:fund|fof|etf)\b", str(value or ""), flags=re.IGNORECASE))


def _parse_arbitrage_page(
    prepared_text: str,
    scheme_name: str,
    context: ParseContext,
) -> ParsedDocument | None:
    """Use only the total/hedge percentage in HSBC Arbitrage's 3-column table."""
    lines = [" ".join(line.split()) for line in prepared_text.splitlines() if " ".join(line.split())]
    start = next((index for index, line in enumerate(lines) if line.lower() == "portfolio"), None)
    if start is None:
        return None

    holdings: list[dict[str, Any]] = []
    current_sector: str | None = None
    pending: list[str] = []
    index = start + 1
    while index < len(lines):
        line = lines[index]
        if line.lower().startswith("grand total"):
            break
        if _is_hsbc_header_fragment(line):
            pending.clear()
            index += 1
            continue
        if _is_percent_line(line):
            values: list[float] = []
            while index < len(lines) and _is_percent_line(lines[index]):
                value = _parse_percent(lines[index])
                if value is not None:
                    values.append(value)
                index += 1
            name = normalize_instrument_name(" ".join(pending))
            pending.clear()
            if not name or not values:
                continue
            if _is_category_name(name):
                current_sector = name
                continue
            if _looks_like_hsbc_security(name):
                holdings.append(_holding(name, values[0], current_sector))
            else:
                current_sector = name
            continue
        pending.append(line)
        pending = pending[-6:]
        index += 1

    if not holdings:
        return None
    # The arbitrage sheet repeats the two mutual-fund rows in its debt block. Keep one
    # occurrence; this is a document-layout duplicate, not two separate securities.
    unique: dict[str, dict[str, Any]] = {}
    for row in holdings:
        key = _scheme_key(str(row.get("instrument_name") or ""))
        key = re.sub(r"\s+mutual fund$", "", key)
        previous = unique.get(key)
        if previous is None or float(row["percent_aum"]) > float(previous["percent_aum"]):
            unique[key] = row
    holdings = list(unique.values())
    total = round(sum(float(row["percent_aum"]) for row in holdings), 6)
    warnings = [] if 70.0 <= total <= 115.0 else ["percent_aum_total_out_of_band"]
    return ParsedDocument(
        scheme_name=scheme_name,
        report_month=context.report_month,
        holdings=holdings,
        metrics={"total_percent_aum": total},
        warnings=warnings,
        confidence_score=75.0 if warnings else 99.0,
    )


def _is_percent_line(value: str) -> bool:
    return bool(re.fullmatch(r"-?\d+(?:\.\d+)?%", str(value or "").strip()))


def _parse_percent(value: str) -> float | None:
    try:
        parsed = float(str(value).strip().rstrip("%"))
    except ValueError:
        return None
    return parsed if 0.0 < parsed <= 100.0 else None


def _is_category_name(value: str) -> bool:
    low = " ".join(str(value or "").lower().split())
    if low in HSBC_EXCLUDED_SECURITY_NAMES:
        return True
    return low in {
        "banks", "capital markets", "power", "money market instruments",
        "cash equivalent", "zcb", "invit s", "invit",
    }


def _looks_like_hsbc_security(value: str) -> bool:
    low = " ".join(str(value or "").lower().split())
    if _is_category_name(low):
        return False
    return any(
        marker in low
        for marker in ("limited", "ltd", "bank", "trust", "fund", "repo", "treasury", "goi", "sdl", "zcb", "aif")
    )


def _holding(name: str, percent: float, sector: str | None) -> dict[str, Any]:
    return {
        "instrument_name": name,
        "isin": None,
        "sector": sector,
        "percent_aum": round(percent, 6),
        "quantity": None,
        "market_value": None,
    }


def _add_sector_metrics(record: ParsedDocument) -> ParsedDocument:
    totals: defaultdict[str, float] = defaultdict(float)
    for row in record.holdings:
        sector = normalize_instrument_name(row.get("sector")) or "Other"
        totals[sector] += float(row.get("percent_aum") or 0.0)
    metrics = dict(record.metrics)
    if totals:
        allocations = [
            {"sector": sector, "weight_pct": round(weight, 6)}
            for sector, weight in sorted(totals.items())
        ]
        metrics["sector_allocations"] = allocations
        metrics["sector_allocation_total"] = round(sum(totals.values()), 6)
    return ParsedDocument(
        scheme_name=record.scheme_name,
        report_month=record.report_month,
        holdings=record.holdings,
        metrics=metrics,
        warnings=record.warnings,
        confidence_score=record.confidence_score,
    )


def _scheme_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()
