"""Deterministic identity checks for Kotak's monthly HTML factsheet archive.

Kotak publishes one HTML page per scheme family.  A page can cover multiple
AMFI plan/option children, so it must not be sent through the existing
single-scheme fuzzy resolver.  This module only produces reviewable identity
evidence; it never stages holdings or changes a promoted mapping.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Iterable
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup

from app.mf_ingestion.agents.validation import detect_factsheet_content_month


KOTAK_ARCHIVE_PATH = re.compile(
    r"/factsheet/(?P<month>[a-z]+)_(?P<year>20\d{2})/",
    re.IGNORECASE,
)
KOTAK_SCHEME_PATTERN = re.compile(
    r"\b(?P<name>Kotak\s+[A-Za-z0-9&,'(). -]{2,140}?(?:Fund|FOF|ETF))\b",
    re.IGNORECASE,
)
KOTAK_CONTENT_MONTH_PATTERN = re.compile(
    r"\b(?:data\s+)?as\s+on\s+(?:"
    r"(?P<day_first>\d{1,2})(?:st|nd|rd|th)?\s+(?P<month_first>[a-z]+),?\s+(?P<year_first>20\d{2})"
    r"|(?P<month_second>[a-z]+)\s+(?P<day_second>\d{1,2})(?:st|nd|rd|th)?,?\s+(?P<year_second>20\d{2})"
    r")\b",
    re.IGNORECASE,
)
AMFI_ISIN_PATTERN = re.compile(r"^[A-Z]{3}[A-Z0-9]{8}\d$")
_TRAILING_PLAN_TOKENS = {
    "direct",
    "regular",
    "plan",
    "growth",
    "idcw",
    "dividend",
    "payout",
    "payment",
    "reinvestment",
    "option",
    "cumulative",
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "annual",
    "yearly",
    "bonus",
}


@dataclass(frozen=True)
class KotakFactsheetPage:
    url: str
    title: str
    report_month: date


@dataclass(frozen=True)
class KotakPageInspection:
    page: KotakFactsheetPage
    scheme_name: str | None
    content_month: date | None
    has_portfolio: bool
    issues: tuple[str, ...]


@dataclass(frozen=True)
class AMFISchemeIdentity:
    scheme_code: str
    scheme_name: str
    isin_primary: str | None
    isin_reinvestment: str | None
    nav_date: date | None

    @property
    def isins(self) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                value
                for value in (self.isin_primary, self.isin_reinvestment)
                if value
            )
        )


@dataclass(frozen=True)
class KotakIdentityResolution:
    page: KotakPageInspection
    normalized_family_name: str | None
    status: str
    issues: tuple[str, ...]
    amfi_children: tuple[AMFISchemeIdentity, ...]


def parse_kotak_archive_month(url: str) -> date | None:
    match = KOTAK_ARCHIVE_PATH.search(urlsplit(str(url or "")).path + "/")
    if not match:
        return None
    try:
        return datetime.strptime(
            f"{match.group('month')} {match.group('year')}", "%B %Y"
        ).date().replace(day=1)
    except ValueError:
        return None


def discover_kotak_factsheet_pages(
    archive_html: str,
    archive_url: str,
) -> list[KotakFactsheetPage]:
    """Return only scheme pages under the selected official monthly archive."""
    archive_month = parse_kotak_archive_month(archive_url)
    if not archive_month:
        return []
    root_path = urlsplit(archive_url).path.rstrip("/") + "/kotak/"
    archive_host = (urlsplit(archive_url).hostname or "").lower()
    pages: list[KotakFactsheetPage] = []
    seen: set[str] = set()
    soup = BeautifulSoup(archive_html or "", "html.parser")
    for anchor in soup.select("a[href]"):
        href = str(anchor.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:")):
            continue
        url = urljoin(archive_url, href)
        parsed = urlsplit(url)
        if (parsed.hostname or "").lower() != archive_host:
            continue
        if not parsed.path.lower().startswith(root_path.lower()):
            continue
        if not parsed.path.lower().endswith((".html", ".htm")):
            continue
        if url in seen:
            continue
        title = " ".join(anchor.get_text(" ", strip=True).split())
        # The archive navigation contains market views, fund-manager pages, and
        # plan-performance pages beside scheme factsheets.  A source page must
        # identify a Kotak Fund/FOF/ETF in its own visible menu title; URL shape
        # alone is insufficient.
        if not KOTAK_SCHEME_PATTERN.search(title):
            continue
        seen.add(url)
        pages.append(
            KotakFactsheetPage(
                url=url,
                title=title or parsed.path.rsplit("/", 1)[-1],
                report_month=archive_month,
            )
        )
    return sorted(pages, key=lambda item: (item.title.lower(), item.url))


def inspect_kotak_factsheet_page(
    page: KotakFactsheetPage,
    html: str,
    *,
    expected_month: date | None = None,
) -> KotakPageInspection:
    soup = BeautifulSoup(html or "", "html.parser")
    text = "\n".join(soup.stripped_strings)
    scheme_name = _extract_kotak_scheme_name(soup, text)
    content_month = _detect_kotak_content_month(text)
    lower = text.lower()
    has_portfolio = (
        "portfolio" in lower
        and "issuer/instrument" in lower
        and ("% to net assets" in lower or "% to nav" in lower)
    )
    issues: list[str] = []
    if not scheme_name:
        issues.append("kotak_html_scheme_name_missing")
    if not content_month:
        issues.append("kotak_html_content_month_missing")
    elif expected_month and content_month != expected_month:
        issues.append(
            "kotak_html_content_month_mismatch:"
            f"{content_month.isoformat()}!={expected_month.isoformat()}"
        )
    if not has_portfolio:
        issues.append("kotak_html_portfolio_table_missing")
    return KotakPageInspection(
        page=page,
        scheme_name=scheme_name,
        content_month=content_month,
        has_portfolio=has_portfolio,
        issues=tuple(issues),
    )


def parse_amfi_navall_kotak_identities(payload: str) -> list[AMFISchemeIdentity]:
    """Parse Kotak scheme/ISIN rows from an immutable NAVAll response body."""
    identities: list[AMFISchemeIdentity] = []
    current_amc = ""
    for raw_line in str(payload or "").splitlines():
        line = raw_line.strip()
        if not line:
            continue
        fields = line.split("|")
        if len(fields) != 6:
            fields = line.split(";")
        if len(fields) != 6:
            if "mutual fund" in line.lower() and "|" not in line and ";" not in line:
                current_amc = line
            continue
        if "kotak" not in current_amc.lower():
            continue
        code, isin_primary, isin_reinvestment, scheme_name, _nav, nav_date = (
            value.strip() for value in fields
        )
        if not code.isdigit() or not scheme_name:
            continue
        identities.append(
            AMFISchemeIdentity(
                scheme_code=code,
                scheme_name=scheme_name,
                isin_primary=_valid_isin(isin_primary),
                isin_reinvestment=_valid_isin(isin_reinvestment),
                nav_date=_parse_nav_date(nav_date),
            )
        )
    return identities


def resolve_kotak_page_identity(
    page: KotakPageInspection,
    amfi_identities: Iterable[AMFISchemeIdentity],
) -> KotakIdentityResolution:
    issues = list(page.issues)
    normalized_family_name = normalize_kotak_family_name(page.scheme_name)
    if not normalized_family_name:
        return KotakIdentityResolution(
            page=page,
            normalized_family_name=None,
            status="needs_review",
            issues=tuple(dict.fromkeys([*issues, "kotak_amfi_family_name_missing"])),
            amfi_children=(),
        )
    children = tuple(
        sorted(
            (
                item
                for item in amfi_identities
                if normalize_kotak_family_name(item.scheme_name) == normalized_family_name
            ),
            key=lambda item: item.scheme_code,
        )
    )
    if not children:
        issues.append("kotak_amfi_exact_family_match_missing")
    elif any(not child.isins for child in children):
        issues.append("kotak_amfi_child_isin_missing")

    return KotakIdentityResolution(
        page=page,
        normalized_family_name=normalized_family_name,
        status="verified" if not issues else "needs_review",
        issues=tuple(dict.fromkeys(issues)),
        amfi_children=children,
    )


def normalize_kotak_family_name(value: str | None) -> str:
    text = str(value or "").lower().replace("&", " and ")
    tokens = re.sub(r"[^a-z0-9]+", " ", text).split()
    # AMFI adds plan/option details at the end.  Removing only terminal markers
    # keeps branded words such as "Regular" in "Kotak Regular Savings Fund".
    while len(tokens) > 1 and tokens[-1] in _TRAILING_PLAN_TOKENS:
        tokens.pop()
    return " ".join(tokens)


def _extract_kotak_scheme_name(soup: BeautifulSoup, text: str) -> str | None:
    for heading in soup.select("h1, h2, h3, title"):
        match = KOTAK_SCHEME_PATTERN.search(heading.get_text(" ", strip=True))
        if match:
            return " ".join(match.group("name").split())
    for line in text.splitlines():
        match = KOTAK_SCHEME_PATTERN.search(line)
        if match:
            return " ".join(match.group("name").split())
    return None


def _detect_kotak_content_month(text: str) -> date | None:
    """Prefer the page's explicit month-end label over a broad date frequency vote."""
    match = KOTAK_CONTENT_MONTH_PATTERN.search(text or "")
    if match:
        day = match.group("day_first") or match.group("day_second")
        month = match.group("month_first") or match.group("month_second")
        year = match.group("year_first") or match.group("year_second")
        try:
            return datetime.strptime(f"{day} {month} {year}", "%d %B %Y").date().replace(day=1)
        except ValueError:
            pass
    return detect_factsheet_content_month(text)


def _valid_isin(value: str) -> str | None:
    candidate = str(value or "").strip().upper()
    return candidate if AMFI_ISIN_PATTERN.fullmatch(candidate) else None


def _parse_nav_date(value: str) -> date | None:
    try:
        return datetime.strptime(str(value or "").strip(), "%d-%b-%Y").date()
    except ValueError:
        return None
