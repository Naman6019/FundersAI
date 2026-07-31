"""Shared regex/string constants used across AMC adapter packages.

This module is the Phase 1 landing site for constants that were duplicated
across several adapter files. Constants here must be AMC-agnostic; AMC-specific
patterns live in the respective ``adapters/<amc>/patterns.py`` modules.

Adding a constant:
- If it is used by 2+ AMC adapters AND the meaning is identical, add here.
- If only one AMC uses it, keep it in that AMC's package.
- If 2+ AMCs use the *concept* but with different shapes (e.g., different
  scheme-name prefixes), keep AMC-specific and add a shared helper docstring
  here instead.
"""

from __future__ import annotations

import re

# --- ISIN detection -----------------------------------------------------------

#: Canonical ISIN: 2 alpha country code + 9 alphanumerics + 1 check digit.
#: Anchored form used by ``generic_portfolio_adapter`` (the most-tested
#: parsing surface). Tier 2 adapters historically used an un-anchored variant
#: (``\b[A-Z]{2}[A-Z0-9]{9}\d\b``); they should migrate to this constant
#: during their Phase 3 split.
ISIN_PATTERN: re.Pattern[str] = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}\d$")

#: Loose ISIN matcher for scan-style searches inside extracted text. Used when
#: looking for ISINs mentioned inline in holdings rows where context text may
#: carry extra characters around the ISIN itself.
ISIN_PATTERN_LOOSE: re.Pattern[str] = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b")

# --- Date detection -----------------------------------------------------------

#: Matches a calendar date like "31-Jan-2025", "as on 31 January 2025",
#: "as of 31-Mar 2025". Day is optional. Year must be 20xx.
DATE_PATTERN: re.Pattern[str] = re.compile(
    r"\b(?:as\s+(?:on|of)\s+)?(?P<day>\d{1,2})?[\s,./-]*"
    r"(?P<month>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"[\s,./-]+(?P<year>20\d{2})\b",
    re.IGNORECASE,
)

#: Map month-prefix strings (3+ chars) used by DATE_PATTERN to int month.
MONTH_ABBREVIATIONS: dict[str, int] = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# --- Scheme-name markers (default token set) ---------------------------------

#: Common substrings found inside scheme names. Used by the generic tabular
#: parser to filter out non-scheme cells (e.g., column headers, footer rows).
DEFAULT_SCHEME_TOKENS: tuple[str, ...] = ("fund", "fof", "etf", "plan")

#: Headings and prefixes that indicate the matched cell is *not* a scheme name
#: even if it contains a scheme token (e.g., "Asset Management", "Master Circular").
NON_SCHEME_HEADING_TOKENS: tuple[str, ...] = (
    "asset management",
    "mutual fund portfolio",
    "monthly portfolio",
    "master circular",
    "pursuant to",
    "securities in case of which",
)

#: Strings that mark a row as a total / grand-total / sub-total rather than
#: an individual holding. Compared case-insensitively after whitespace-collapse.
SUMMARY_MARKERS: tuple[str, ...] = (
    "grand total",
    "sub total",
    "subtotal",
    "total",
    "equity and equity related",
    "equity & equity related",
    "debt instruments",
    "money market instruments",
    "cash and cash equivalents",
    "mutual fund units",
    "treps",
)

#: Strings representing missing numeric values. Coerced to ``None`` when parsed.
NULL_NUMERIC_TOKENS: frozenset[str] = frozenset({"na", "n/a", "nan", "-", "--"})

#: Confidence score floor for successfully parsed holdings.
CONFIDENCE_BASE_SCORE: float = 55.0
#: Maximum bonus added to confidence per holding parsed.
CONFIDENCE_HOLDING_BONUS_CAP: float = 25.0
#: Bonus added to confidence when report_month is detected.
CONFIDENCE_REPORT_MONTH_BONUS: float = 10.0
#: Bonus added to confidence when the %AUM total is within [85, 115].
CONFIDENCE_TOTAL_BAND_BONUS: float = 10.0
#: Confidence score ceiling.
CONFIDENCE_MAX: float = 99.0
#: Acceptable %AUM total band.
TOTAL_PERCENT_MIN: float = 85.0
TOTAL_PERCENT_MAX: float = 115.0
