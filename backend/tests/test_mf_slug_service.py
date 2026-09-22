"""Tests for deterministic fund-slug derivation.

The generator previously produced `f"{slug(scheme_name)}-{code}"` without stripping share-class
metadata, so every scheme published after the initial curated batch got a URL like
`hdfc-elss-tax-saver-fund-direct-plan-growth-option-119060`. These tests pin the two properties
that matter: share-class noise is gone, and real name words are kept.

The distinction is the whole difficulty. "Growth" is noise in "… - Direct Plan - Growth Option",
but it is identity in "Nippon India Growth Fund". A naive strip of the word breaks the second,
so every case below is drawn from real scheme names.
"""
from __future__ import annotations

from app.services.mf_slug_service import assign_slugs, clean_fund_name, fund_slug


# ─── Share-class metadata is removed ─────────────────────────────────────────

def test_plan_and_option_metadata_is_stripped():
    cases = {
        "HDFC Flexi Cap Fund - Direct Plan - Growth Option": "hdfc-flexi-cap-fund",
        "Parag Parikh Flexi Cap Fund - Direct Plan - Growth": "parag-parikh-flexi-cap-fund",
        "BANDHAN Small Cap Fund - Direct Plan - Growth": "bandhan-small-cap-fund",
        "Aditya Birla Sun Life Large Cap Fund - Direct Plan - GROWTH": "aditya-birla-sun-life-large-cap-fund",
        # A doubled separator, seen on ICICI Prudential Liquid Fund.
        "ICICI Prudential Liquid Fund - - Direct Plan - Growth": "icici-prudential-liquid-fund",
    }
    for name, expected in cases.items():
        assert fund_slug(name) == expected, name


def test_repeated_share_class_words_are_fully_removed():
    """PGIM publishes "- Direct Plan - Direct Growth", which leaves a trailing "direct"."""
    assert fund_slug("PGIM India Flexi Cap Fund - Direct Plan - Direct Growth") == "pgim-india-flexi-cap-fund"
    assert fund_slug("Old Bridge Flexi Cap Fund - Direct Plan - Direct Growth") == "old-bridge-flexi-cap-fund"


def test_idcw_payout_and_reinvestment_variants_are_removed():
    cases = {
        "Tata Gold ETF Fund of Fund - Direct Plan - IDCW Payout Option": "tata-gold-etf-fund-of-fund",
        "Tata Silver ETF Fund of Fund - Regular Plan - IDCW Reinvestment Option": "tata-silver-etf-fund-of-fund",
        "Tata Nifty India Digital ETF Fund of Fund - Direct Plan - IDCW Payout Option":
            "tata-nifty-india-digital-etf-fund-of-fund",
    }
    for name, expected in cases.items():
        assert fund_slug(name) == expected, name


def test_doubled_option_token_is_removed():
    assert fund_slug("Axis Multi Asset Allocation Fund - Direct Plan - Growth Option Option") == (
        "axis-multi-asset-allocation-fund"
    )


def test_parentheticals_and_footnote_markers_are_removed():
    assert fund_slug("ICICI Prudential Large Cap Fund (erstwhile Bluechip Fund) - Direct Plan - Growth") == (
        "icici-prudential-large-cap-fund"
    )
    assert fund_slug("ICICI Prudential Value Fund (erstwhile Value Discovery Fund) - Direct Plan - Growth") == (
        "icici-prudential-value-fund"
    )


# ─── Real name words are preserved ───────────────────────────────────────────

def test_plan_as_part_of_a_fund_name_is_preserved():
    """"Fixed Term Plan" and "Plan A" are identity; only trailing residue is share-class noise."""
    cases = {
        "Axis Fixed Term Plan - Series 113 (1228 Days) - Direct Plan - Growth Option":
            "axis-fixed-term-plan-series-113",
        "SBI CHILDREN'S FUND - SAVINGS PLAN - Direct Plan - Growth": "sbi-children-s-fund-savings-plan",
        "Nippon India Dual Advantage Fixed Tenure Fund XI- Plan A - Direct Plan - Growth":
            "nippon-india-dual-advantage-fixed-tenure-fund-xi-plan-a",
    }
    for name, expected in cases.items():
        assert fund_slug(name) == expected, name


def test_growth_in_a_fund_name_is_preserved():
    """The exact case a naive word-strip would break."""
    assert fund_slug("Nippon India Growth Mid Cap Fund - Direct Plan - Growth Option") == (
        "nippon-india-growth-mid-cap-fund"
    )


def test_elss_and_tax_saver_names_are_preserved():
    assert fund_slug("HDFC ELSS - Tax Saver Fund - Direct Plan - Growth Option") == "hdfc-elss-tax-saver-fund"


def test_etf_names_without_share_class_are_unchanged_in_meaning():
    assert fund_slug("Motilal Oswal Nifty 50 ETF") == "motilal-oswal-nifty-50-etf"
    assert fund_slug("ICICI Prudential Gold ETF") == "icici-prudential-gold-etf"


def test_ampersand_becomes_and():
    assert fund_slug("ICICI Prudential Banking & Financial Services Fund - Direct Plan - Growth") == (
        "icici-prudential-banking-and-financial-services-fund"
    )


def test_a_name_that_cleans_to_nothing_still_yields_a_slug():
    assert fund_slug("- Direct Plan - Growth Option") == "fund"
    assert fund_slug("") == "fund"


def test_with_code_appends_the_amfi_code():
    assert fund_slug("HDFC Flexi Cap Fund - Direct Plan - Growth", "118955", with_code=True) == (
        "hdfc-flexi-cap-fund-118955"
    )


def test_clean_fund_name_exposes_the_display_portion():
    assert clean_fund_name("HDFC ELSS - Tax Saver Fund - Direct Plan - Growth Option") == (
        "HDFC ELSS - Tax Saver Fund"
    )


# ─── Collision resolution ────────────────────────────────────────────────────

def test_collision_resolves_by_age_and_is_deterministic():
    """Two share classes cleaning to one base must not receive the same URL."""
    rows = [
        {"scheme_code": "1", "amc_slug": "hdfc", "scheme_name": "HDFC Flexi Cap Fund - Direct Plan - Growth",
         "first_published_at": "2026-01-01T00:00:00+00:00"},
        {"scheme_code": "2", "amc_slug": "hdfc", "scheme_name": "HDFC Flexi Cap Fund - Regular Plan - Growth",
         "first_published_at": "2026-02-01T00:00:00+00:00"},
    ]
    assigned = assign_slugs(rows)

    assert assigned["1"] == "hdfc-flexi-cap-fund"
    assert assigned["2"] == "hdfc-flexi-cap-fund-2"
    assert len(set(assigned.values())) == 2


def test_existing_frozen_url_is_never_claimed_by_a_new_scheme():
    rows = [
        {"scheme_code": "9", "amc_slug": "hdfc", "scheme_name": "HDFC Flexi Cap Fund - Direct Plan - Growth"},
    ]
    assigned = assign_slugs(rows, taken={("hdfc", "hdfc-flexi-cap-fund"): "118955"})

    assert assigned["9"] == "hdfc-flexi-cap-fund-9"


def test_assignment_is_stable_across_re_runs():
    rows = [
        {"scheme_code": "1", "amc_slug": "hdfc", "scheme_name": "HDFC Flexi Cap Fund - Direct Plan - Growth",
         "first_published_at": "2026-01-01T00:00:00+00:00"},
        {"scheme_code": "2", "amc_slug": "hdfc", "scheme_name": "HDFC Flexi Cap Fund - Regular Plan - Growth",
         "first_published_at": "2026-02-01T00:00:00+00:00"},
    ]
    assert assign_slugs(rows) == assign_slugs(list(reversed(rows)))


def test_distinct_names_keep_distinct_slugs():
    rows = [
        {"scheme_code": "1", "amc_slug": "hdfc", "scheme_name": "HDFC Flexi Cap Fund - Direct Plan - Growth"},
        {"scheme_code": "2", "amc_slug": "hdfc", "scheme_name": "HDFC Mid Cap Fund - Direct Plan - Growth"},
    ]
    assigned = assign_slugs(rows)

    assert assigned["1"] == "hdfc-flexi-cap-fund"
    assert assigned["2"] == "hdfc-mid-cap-fund"
