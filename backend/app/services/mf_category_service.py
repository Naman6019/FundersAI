"""Authoritative SEBI-category resolution for mutual fund schemes.

Why this exists:

`mutual_fund_core_snapshot.category` is NULL for most AMFI rows, which blocks public fund
pages: the catalog gate requires a SEBI category, and `mf_catalog_service.category()` can only
resolve a value that is already present. The 29 currently-published funds are not evidence the
pipeline works — their category came from a hand-curated JSON file
(`backend/config/catalog_registry_funds.json`). Publication was therefore bounded by manual
curation, not by data.

Deriving a category from the scheme *name* would be fabrication: a name that contains "Gilt" is
not proof the scheme is filed under a SEBI Gilt category. The authoritative source already
exists and is already downloaded by the pipeline — AMFI's NAVAll.txt carries the category as a
**section header** above each group of schemes:

    Open Ended Schemes(Debt Scheme - Gilt Fund)

    Bajaj Finserv Mutual Fund

    153206;INF0QA701AP9;-;Bajaj Finserv Gilt Fund;Direct Plan;Growth;1076.1554;21-Sep-2026

Every scheme row beneath a header belongs to that header's category until the next header.
`sync_mf.py` already parses the rows but discards the headers, which is why the category was
never populated.

Mapping policy: AMFI's inner label is *translated*, never guessed. Each distinct label is listed
explicitly below with the canonical value it becomes. A label that is not listed resolves to
None, which deliberately preserves the existing gate reason rather than inventing a category.
That is the honest failure direction: an unpublishable scheme costs coverage, a mislabelled one
publishes a deterministic-metric page under a false SEBI classification.
"""
from __future__ import annotations

import re

# The three AMFI scheme-family prefixes. Kept together so a future AMFI addition is one edit.
_SECTION_PREFIXES = ("Open Ended Schemes", "Close Ended Schemes", "Interval Fund Schemes")
_SECTION = re.compile(
    r"^\s*(?:" + "|".join(_SECTION_PREFIXES) + r")\s*\((.*)\)\s*$"
)

# AMFI's labels are inconsistent across releases: "Equity Scheme" vs "Equity Schemes",
# "Sectoral/ Thematic" vs "Sectoral Fund" vs "Thematic Fund". The canonical keys below collapse
# those variants so the table does not grow a row per spelling.
_CANONICAL_KEY = re.compile(r"[^a-z0-9&/]+")


def _key(label: str) -> str:
    """Normalise a label for lookup: case, spacing, plural and all punctuation.

    Every non-alphanumeric character is removed, including hyphens and slashes, so
    "Income/Debt Oriented Schemes - Gilt Fund" and "Income Debt Oriented Schemes Gilt Fund"
    reduce to one key. The Scheme/Schemes plural is folded because AMFI uses both spellings for
    the same family. A map key must therefore be written exactly as this produces it;
    `test_mf_category_service.py` asserts every key round-trips, so a typo fails CI instead of
    silently becoming an unmapped label at runtime.
    """
    lowered = str(label or "").strip().lower()
    lowered = lowered.replace("equity schemes", "equity scheme")
    lowered = lowered.replace("hybrid schemes", "hybrid scheme")
    lowered = lowered.replace("fund of funds scheme", "fund of funds")
    lowered = lowered.replace("exchange traded funds (etfs)", "etf")
    # "Index Funds" stays plural here: it is part of distinct family labels
    # ("Index Funds - Equity Funds" vs "Other Scheme - Index Funds"), so folding it would
    # collapse two different categories into one key.
    return _CANONICAL_KEY.sub("", lowered)


# ---------------------------------------------------------------------------
# AMFI label -> canonical SEBI category.
#
# Equity values match `mf_catalog_service.CATEGORIES` exactly, so an equity scheme that gains a
# category from this module becomes immediately eligible for a public page. Debt, hybrid and
# other values are new vocabulary and remain ineligible until the catalog's category list is
# extended deliberately — populating a category must not silently widen what gets published.
#
# Keys are the output of `_key()`, lowercased with all punctuation removed. They are pinned to
# their labels by `test_mf_category_service.py`, so a typo fails CI instead of becoming an
# unmapped label at runtime.
# ---------------------------------------------------------------------------
_CATEGORY_MAP: dict[str, str] = {
    # ── Equity: matches the existing publishable CATEGORIES ──────────────────
    "equityschemeflexicapfund": "Flexi Cap",
    "equityschemeelss": "ELSS",
    "equityschemeelsstaxsaverfund": "ELSS",
    "elss": "ELSS",
    "equityschemelargecapfund": "Large Cap",
    "equityschememidcapfund": "Mid Cap",
    "equityschemelarge&midcapfund": "Large & Mid Cap",
    "equityschememulticapfund": "Multi Cap",
    "equityschemesmallcapfund": "Small Cap",
    "equityschemefocusedfund": "Focused",
    "equityschemevaluefund": "Value",
    "equityschemecontrafund": "Contra",
    "equityschemedividendyieldfund": "Dividend Yield",
    "equityschemedividendyieldfund": "Dividend Yield",
    "equityschemesectoral/thematic": "Sectoral/Thematic",
    "equityschemesectoralfund": "Sectoral/Thematic",
    "equityschemethematicfund": "Sectoral/Thematic",
    "indexfundsequityfunds": "Index Fund",
    "otherschemeindexfunds": "Index Fund",
    # ── Equity: real SEBI categories not yet on the publishable list ─────────
    # ── Debt ────────────────────────────────────────────────────────────────
    "debtschemebankingandpsufund": "Debt - Banking and PSU",
    "debtschemecorporatebondfund": "Debt - Corporate Bond",
    "debtschemecreditriskfund": "Debt - Credit Risk",
    "debtschemedynamicbond": "Debt - Dynamic Bond",
    "debtschemegiltfund": "Debt - Gilt",
    "debtschemeliquidfund": "Debt - Liquid",
    "debtschemelongdurationfund": "Debt - Long Duration",
    "debtschemelowdurationfund": "Debt - Low Duration",
    "debtschememediumdurationfund": "Debt - Medium Duration",
    "debtschememediumtolongdurationfund": "Debt - Medium to Long Duration",
    "debtschememoneymarketfund": "Debt - Money Market",
    "debtschemeovernightfund": "Debt - Overnight",
    "debtschemeshortdurationfund": "Debt - Short Duration",
    "debtschemeultrashortdurationfund": "Debt - Ultra Short Duration",
    # Legacy AMFI debt buckets. "Income" is AMFI's own pre-2017 label for the debt-oriented
    # family, so translating it records AMFI's taxonomy rather than inferring one from a name.
    "income": "Debt - Income (legacy)",
    "gilt": "Debt - Gilt",
    "moneymarket": "Debt - Money Market",
    "growth": "Debt - Growth (legacy)",
    "income/debtorientedschemes10yearconstantmaturitygiltfund": "Debt - Gilt",
    "income/debtorientedschemesbankingandpsudebtfund": "Debt - Banking and PSU",
    "income/debtorientedschemescorporatebondfund": "Debt - Corporate Bond",
    "income/debtorientedschemescreditriskfund": "Debt - Credit Risk",
    "income/debtorientedschemesdynamictermfund": "Debt - Dynamic Bond",
    "income/debtorientedschemesfixedtermplan": "Debt - Fixed Term",
    "income/debtorientedschemesfloatinginterestratesfund": "Debt - Floater",
    "income/debtorientedschemesgiltfund": "Debt - Gilt",
    "income/debtorientedschemesliquidfund": "Debt - Liquid",
    "income/debtorientedschemeslongtermfund": "Debt - Long Duration",
    "income/debtorientedschemesmediumtermfund": "Debt - Medium Duration",
    "income/debtorientedschemesmediumtolongtermfund": "Debt - Medium to Long Duration",
    "income/debtorientedschemesmoneymarketfund": "Debt - Money Market",
    "income/debtorientedschemesovernightfund": "Debt - Overnight",
    "income/debtorientedschemesotherdebtscheme": "Debt - Other",
    "income/debtorientedschemessectoralfund": "Debt - Sectoral",
    "income/debtorientedschemesshorttermfund": "Debt - Short Duration",
    "income/debtorientedschemesultrashorttermfund": "Debt - Ultra Short Duration",
    "income/debtorientedschemesultrashorttoshorttermfund": "Debt - Ultra Short Duration",
    # ── Hybrid ──────────────────────────────────────────────────────────────
    "hybridschemeaggressivehybridfund": "Hybrid - Aggressive",
    "hybridschemearbitragefund": "Hybrid - Arbitrage",
    "hybridschemebalancedhybridfund": "Hybrid - Balanced",
    "hybridschemebalancedadvantagefund/dynamicassetallocation": "Hybrid - Balanced Advantage",
    "hybridschemeconservativehybridfund": "Hybrid - Conservative",
    "hybridschemedynamicassetallocationorbalancedadvantage": "Hybrid - Balanced Advantage",
    "hybridschemeequitysavings": "Hybrid - Equity Savings",
    "hybridschemeequitysavingsfund": "Hybrid - Equity Savings",
    "hybridschememultiassetallocation": "Hybrid - Multi Asset Allocation",
    "hybridschememultiassetallocationfund": "Hybrid - Multi Asset Allocation",
    # ── Passive wrappers ────────────────────────────────────────────────────
    "etfdebtetf": "ETF - Debt",
    "etfetfsinvestingoverseas": "ETF - Overseas",
    "etfequityetf": "ETF - Equity",
    "etfgoldetf": "ETF - Gold",
    "etfhybridetf": "ETF - Hybrid",
    "etfotheretf": "ETF - Other",
    "etfsilveretf": "ETF - Silver",
    "otherschemegoldetf": "ETF - Gold",
    "otherschemeotheretfs": "ETF - Other",
    "indexfundsdebtfunds": "Index Fund - Debt",
    "indexfundshybridfund": "Index Fund - Hybrid",
    # ── Fund of funds ───────────────────────────────────────────────────────
    "otherschemefofdomestic": "Fund of Funds - Domestic",
    "fundoffundsdomesticfundoffundsdomestic": "Fund of Funds - Domestic",
    "otherschemefofoverseas": "Fund of Funds - Overseas",
    "overseasfundoffundsfundoffundsinvestingoverseas": "Fund of Funds - Overseas",
    # ── Solution oriented ───────────────────────────────────────────────────
    "solutionorientedschemeretirementfund": "Solution Oriented - Retirement",
    "solutionorientedschemesretirementfund": "Solution Oriented - Retirement",
    "solutionorientedschemechildrensfund": "Solution Oriented - Children's",
    "childrensfundchildrensfund": "Solution Oriented - Children's",
    # ── Life cycle ──────────────────────────────────────────────────────────
    "lifecyclefundslifecyclefundwithmaturityof5years": "Life Cycle - 5 Year",
    "lifecyclefundslifecyclefundwithmaturityof10years": "Life Cycle - 10 Year",
    "lifecyclefundslifecyclefundwithmaturityof15years": "Life Cycle - 15 Year",
}


def parse_navall_categories(text: str) -> dict[str, str]:
    """Map each AMFI scheme code to the verbatim category header above it.

    Returns the raw AMFI section label (e.g. "Open Ended Schemes(Debt Scheme - Gilt Fund)"), not
    the canonical value, so the extraction stays a faithful record of what AMFI published and
    the translation is a separate, testable step.
    """
    categories: dict[str, str] = {}
    current: str | None = None

    for line in str(text or "").splitlines():
        stripped = line.strip().lstrip("\ufeff")
        if not stripped:
            continue

        match = _SECTION.match(stripped)
        if match:
            current = match.group(1).strip()
            continue

        # A data row begins with the numeric scheme code and is semicolon-delimited.
        if current is None or not stripped[0].isdigit() or ";" not in stripped:
            continue
        code = stripped.split(";", 1)[0].strip()
        if code.isdigit():
            categories[code] = current

    return categories


def sebi_category(amfi_label: str | None) -> str | None:
    """Translate an AMFI section label to a canonical category, or None if unmapped.

    None is meaningful and must be preserved by callers: it keeps the catalog gate reason in
    place instead of publishing under a guessed classification.
    """
    if not amfi_label:
        return None
    return _CATEGORY_MAP.get(_key(amfi_label))


def canonical_label_count() -> int:
    """Number of distinct canonical values the table can produce. Used by tests."""
    return len(set(_CATEGORY_MAP.values()))


def unmapped_labels(labels) -> list[str]:
    """Which of the supplied AMFI labels this table cannot translate. Used by tests."""
    return sorted({label for label in labels if label and sebi_category(label) is None})
