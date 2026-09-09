from __future__ import annotations

from app.mf_ingestion.sources.registry import SOURCES

# Live-checked in September 2026 against the factsheet each AMC actually has in R2,
# parsed with the real adapters. Every AMC below returned zero instrument-level
# holdings from its factsheet: the document is either a fund-summary one-pager or
# carries a Top-10 panel only. Their complete portfolios come from the separate
# monthly portfolio disclosure, so the factsheet must not be reused as one.
#
# Do not flip any of these back to True without re-running the factsheet through
# HoldingsParser and showing it yields real holdings -- setting it True makes
# discovery register the factsheet AS the portfolio_disclosure document, which
# silently replaces a real portfolio source with one that parses to nothing.
FACTSHEET_WITHOUT_HOLDINGS = frozenset(
    {
        "abakkus",
        "angel_one",
        "bajaj_finserv",
        "baroda_bnp",
        "groww",
        "jio_blackrock",
        "lic",
        "quant",
        "shriram",
        "taurus",
        "zerodha",
    }
)


def test_factsheets_verified_to_carry_no_holdings_are_not_reused_as_portfolios():
    reused = sorted(
        key
        for key in FACTSHEET_WITHOUT_HOLDINGS
        if SOURCES[key].factsheet_contains_holdings
    )
    assert reused == [], (
        "these AMCs were verified to publish factsheets with no instrument-level "
        f"holdings, so they cannot stand in for a portfolio disclosure: {reused}"
    )


def test_every_flagged_amc_is_still_registered():
    """Guards the list above against silently rotting into a no-op if an AMC key
    is renamed or dropped from the registry."""
    missing = sorted(FACTSHEET_WITHOUT_HOLDINGS - set(SOURCES))
    assert missing == []


def test_amcs_needing_a_separate_portfolio_document_have_a_page_to_find_it_on():
    """An AMC whose factsheet carries no holdings can only ever produce holdings
    from its portfolio disclosure, so it must have a discovery page for one."""
    unreachable = sorted(
        key
        for key, source in SOURCES.items()
        if not source.factsheet_contains_holdings and not source.portfolio_disclosure_page_url
    )
    assert unreachable == []
