"""Tests for authoritative SEBI-category resolution.

Two things these pin, both of which failed during development:

1. **Extraction.** AMFI's category is a section header, not a column. Every data row must inherit
   the header above it, and a row before any header must not be given one.
2. **Translation.** Every key in the map must be exactly what `_key()` produces. The first
   version wrote keys with hyphens ("debtscheme-giltfund") while `_key()` stripped them
   ("debtschemegiltfund"), so 96 of 101 real labels silently resolved to None. A round-trip
   assertion makes that class of typo fail here instead of in production.

The mapping is asserted against labels that actually occur in AMFI's published NAVAll.txt, not
against invented strings, so the table cannot drift away from reality unnoticed.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.services.mf_catalog_service import CATEGORIES
from app.services.mf_category_service import (
    _CATEGORY_MAP,
    _key,
    canonical_label_count,
    parse_navall_categories,
    sebi_category,
    unmapped_labels,
)

# Every distinct category label AMFI published in its 2026-09-21 NAVAll.txt, captured verbatim.
# Regenerate by re-downloading NAVAll.txt; never edit by hand.
_FIXTURE = Path(__file__).resolve().parent / "fixtures" / "amfi_category_labels.json"
_FIXTURE_DATA = json.loads(_FIXTURE.read_text(encoding="utf-8"))
REAL_ROWS = _FIXTURE_DATA["labels"]
REAL_LABELS = [row["label"] for row in REAL_ROWS]


# ─── The key round-trip guard ────────────────────────────────────────────────

def test_every_map_key_is_exactly_what_the_normaliser_produces():
    """A key that does not round-trip can never match, so the entry is dead code.

    This is the bug that shipped first: 96 of 101 real labels resolved to None because the keys
    were written with hyphens and the normaliser removed them.
    """
    for key in _CATEGORY_MAP:
        assert _key(key) == key, (
            f"Map key {key!r} does not survive _key() (produces {_key(key)!r}). "
            "Write the key exactly as _key() emits it."
        )


def test_fixture_is_a_usable_amfi_label_snapshot():
    assert "amfiindia.com" in _FIXTURE_DATA["source"]
    assert _FIXTURE_DATA["capturedOn"] == "2026-09-21"
    assert len(REAL_LABELS) >= 100


def test_every_real_amfi_label_is_mapped():
    unmapped = unmapped_labels(REAL_LABELS)
    assert unmapped == [], f"Unmapped real AMFI labels: {unmapped}"


def test_no_map_key_is_a_dead_entry():
    """Every mapping key must correspond to a real label, so the table has no invented rows."""
    real_keys = {_key(label) for label in REAL_LABELS}
    dead = sorted(set(_CATEGORY_MAP) - real_keys)
    assert dead == [], f"Map contains keys no real AMFI label produces: {dead}"


def test_fixture_category_values_match_the_live_map():
    """The fixture records what each label resolves to; the live map must agree.

    A drift here means the translation changed without the fixture being regenerated, which
    would leave the recorded expectation describing a mapping that no longer exists.
    """
    for row in REAL_ROWS:
        assert sebi_category(row["label"]) == row["category"], row["label"]


# ─── Extraction ──────────────────────────────────────────────────────────────

_SAMPLE = "\ufeffScheme Code;ISIN Div Payout/ ISIN Growth;ISIN Div Reinvestment;Scheme Name;Plan;Option;Net Asset Value;Date\n" \
    "Open Ended Schemes(Debt Scheme - Gilt Fund)\n" \
    "\n" \
    "Bajaj Finserv Mutual Fund\n" \
    "\n" \
    "153206;INF0QA701AP9;-;Bajaj Finserv Gilt Fund;Direct Plan;Growth;1076.1554;21-Sep-2026\n" \
    "153211;INF0QA701AM6;-;Bajaj Finserv Gilt Fund;Regular Plan;Growth;1061.3343;21-Sep-2026\n" \
    "\n" \
    "Bandhan Mutual Fund\n" \
    "\n" \
    "118464;INF194K01Q29;-;Bandhan Gilt Fund;Direct Plan;Growth;40.8426;21-Sep-2026\n" \
    "Open Ended Schemes(Equity Scheme - Flexi Cap Fund)\n" \
    "\n" \
    "Parag Parikh Mutual Fund\n" \
    "\n" \
    "122639;INF879O01019;-;Parag Parikh Flexi Cap Fund;Direct Plan;Growth;89.7169;21-Sep-2026\n"


def test_rows_inherit_the_header_above_them():
    categories = parse_navall_categories(_SAMPLE)

    assert categories == {
        "153206": "Debt Scheme - Gilt Fund",
        "153211": "Debt Scheme - Gilt Fund",
        "118464": "Debt Scheme - Gilt Fund",
        "122639": "Equity Scheme - Flexi Cap Fund",
    }


def test_a_row_before_any_header_is_not_given_a_category():
    """Without a preceding header there is no category, and none must be invented."""
    payload = (
        "153206;INF0QA701AP9;-;Bajaj Finserv Gilt Fund;Direct Plan;Growth;1076.1554;21-Sep-2026\n"
        "Open Ended Schemes(Debt Scheme - Gilt Fund)\n"
        "118464;INF194K01Q29;-;Bandhan Gilt Fund;Direct Plan;Growth;40.8426;21-Sep-2026\n"
    )
    categories = parse_navall_categories(payload)

    assert "153206" not in categories
    assert categories["118464"] == "Debt Scheme - Gilt Fund"


def test_header_is_stored_verbatim_not_translated():
    """Extraction stays a faithful record of AMFI's text; translation is a separate step."""
    categories = parse_navall_categories(_SAMPLE)
    assert categories["122639"] == "Equity Scheme - Flexi Cap Fund"
    assert sebi_category(categories["122639"]) == "Flexi Cap"


def test_empty_and_junk_payloads_are_safe():
    assert parse_navall_categories("") == {}
    assert parse_navall_categories("garbage\nwithout headers\n") == {}


# ─── Translation ─────────────────────────────────────────────────────────────

def test_equity_labels_translate_to_the_publishable_category_list():
    """An equity scheme must land on a value the catalog gate already accepts.

    This is what makes the new batch immediately publishable without widening the gate.
    """
    equity_expectations = {
        "Equity Scheme - Flexi Cap Fund": "Flexi Cap",
        "Equity Schemes - Flexi Cap Fund": "Flexi Cap",
        "Equity Scheme - Large Cap Fund": "Large Cap",
        "Equity Scheme - Mid Cap Fund": "Mid Cap",
        "Equity Scheme - Small Cap Fund": "Small Cap",
        "Equity Scheme - Large & Mid Cap Fund": "Large & Mid Cap",
        "Equity Scheme - ELSS": "ELSS",
        "Equity Schemes - ELSS- Tax Saver Fund": "ELSS",
        "Equity Scheme - Sectoral/ Thematic": "Sectoral/Thematic",
        "Equity Schemes - Sectoral Fund": "Sectoral/Thematic",
        "Equity Schemes - Thematic Fund": "Sectoral/Thematic",
        "Index Funds - Equity Funds": "Index Fund",
        "Other Scheme - Index Funds": "Index Fund",
    }
    for label, expected in equity_expectations.items():
        assert sebi_category(label) == expected, label
        assert expected in CATEGORIES, f"{expected} is not a publishable category"


def test_plural_and_spelling_variants_collapse_to_one_value():
    """AMFI writes "Equity Scheme" and "Equity Schemes" for the same family."""
    assert sebi_category("Equity Scheme - Flexi Cap Fund") == sebi_category("Equity Schemes - Flexi Cap Fund")
    assert sebi_category("Hybrid Scheme - Aggressive Hybrid Fund") == sebi_category(
        "Hybrid Schemes - Aggressive Hybrid Fund"
    )
    # "Sectoral/ Thematic" and "Sectoral Fund" are the same SEBI family.
    assert sebi_category("Equity Scheme - Sectoral/ Thematic") == sebi_category("Equity Schemes - Sectoral Fund")


def test_non_equity_values_are_new_vocabulary_not_publishable():
    """Debt/hybrid populate the column without silently widening what gets published."""
    for label in [
        "Debt Scheme - Gilt Fund",
        "Hybrid Scheme - Arbitrage Fund",
        "Exchange Traded Funds (ETFs) - Gold ETF",
        "Other Scheme - FoF Domestic",
    ]:
        value = sebi_category(label)
        assert value is not None
        assert value not in CATEGORIES, f"{value} must not be publishable yet"


def test_unmapped_or_missing_label_returns_none():
    """None keeps the gate reason in place; it must never fall back to a guess."""
    assert sebi_category(None) is None
    assert sebi_category("") is None
    assert sebi_category("Some Future AMFI Category - Unknown") is None


def test_legacy_income_labels_are_recorded_as_amfi_taxonomy():
    assert sebi_category("Income") == "Debt - Income (legacy)"
    assert sebi_category("Growth") == "Debt - Growth (legacy)"
    assert sebi_category("Money Market") == "Debt - Money Market"
    assert sebi_category("Gilt") == "Debt - Gilt"


def test_canonical_count_is_stable():
    """Guards against an accidental collapse of distinct categories into one value."""
    assert canonical_label_count() == len(set(_CATEGORY_MAP.values()))
    assert canonical_label_count() >= 40
