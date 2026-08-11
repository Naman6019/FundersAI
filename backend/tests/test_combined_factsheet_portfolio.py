from __future__ import annotations

from datetime import date
from types import SimpleNamespace

from app.mf_ingestion.parsers.combined_factsheet_portfolio import (
    _merge_portfolio_candidates,
    parse_combined_factsheet_page,
)


def test_merge_portfolio_candidates_unions_rows_instead_of_picking_one():
    """Direct unit test of the merge primitive: two candidate scans covering
    different, non-overlapping instruments should union into one combined set
    rather than the old behaviour of keeping only the single best-scoring
    candidate and discarding the rest."""
    candidate_a = (
        [
            {"instrument_name": "7.08% Karnataka State Govt(^)-Karnataka", "isin": None, "sector": "SOV", "percent_aum": 3.49, "quantity": None, "market_value": None},
            {"instrument_name": "7.49% Karnataka State Govt(^)-Karnataka", "isin": None, "sector": "SOV", "percent_aum": 2.94, "quantity": None, "market_value": None},
        ],
        6.43,
    )
    candidate_b = (
        [
            {"instrument_name": "PTC Siddhivinayak Securitisation Trust", "isin": None, "sector": "CRISIL AAA(SO)", "percent_aum": 1.10, "quantity": None, "market_value": None},
        ],
        1.10,
    )

    rows, total_percent = _merge_portfolio_candidates([candidate_a, candidate_b])

    names = {row["instrument_name"] for row in rows}
    assert names == {
        "7.08% Karnataka State Govt(^)-Karnataka",
        "7.49% Karnataka State Govt(^)-Karnataka",
        "PTC Siddhivinayak Securitisation Trust",
    }
    assert total_percent == 7.53


def test_merge_portfolio_candidates_collapses_a_key_to_one_candidates_account():
    """When two candidates both observed one row under the same instrument key
    (overlapping scan ranges re-observing the same physical row), the merge must
    not double-count it -- but it also must never pick *between* the two rows by
    comparing their values. Real documents can have two genuinely different bonds
    share both a normalized name and, coincidentally, the exact same percent_aum
    (observed live: two separate "TATA CAPITAL LTD" holdings in the same Kotak
    Bond Short Term Fund document, both 0.70% -- a naive value-aware dedup
    collapsed them into one, silently dropping a real holding). So for a single
    key, trust whichever *one* candidate's account of it to use in full, rather
    than reconciling field-by-field across candidates."""
    candidate_a = (
        [{"instrument_name": "TREPS / Reverse Repo Investments", "isin": None, "sector": None, "percent_aum": 2.20, "quantity": None, "market_value": None}],
        2.20,
    )
    candidate_b = (
        [{"instrument_name": "TREPS / Reverse Repo Investments", "isin": None, "sector": None, "percent_aum": 2.60, "quantity": None, "market_value": None}],
        2.60,
    )

    rows, total_percent = _merge_portfolio_candidates([candidate_a, candidate_b])

    assert len(rows) == 1
    assert rows[0]["percent_aum"] in (2.20, 2.60)
    assert total_percent == rows[0]["percent_aum"]


def test_merge_portfolio_candidates_keeps_two_different_rows_sharing_a_key_and_value():
    """Two different candidates each independently observing TWO rows under the
    same key with the SAME two values (e.g. both scans covering the same real
    two-row section of the table) must keep both rows, not collapse to one --
    this is the exact shape of the real "TATA CAPITAL LTD" collision."""
    rows_seen = [
        {"instrument_name": "TATA CAPITAL LTD. (^) CRISIL AAA", "isin": None, "sector": None, "percent_aum": 0.70, "quantity": None, "market_value": None},
        {"instrument_name": "TATA CAPITAL LTD. CRISIL AAA", "isin": None, "sector": None, "percent_aum": 0.70, "quantity": None, "market_value": None},
    ]
    candidate_a = (rows_seen, 1.40)
    candidate_b = (rows_seen, 1.40)

    rows, total_percent = _merge_portfolio_candidates([candidate_a, candidate_b])

    assert len(rows) == 2
    assert total_percent == 1.40


def test_kotak_two_column_layout_no_longer_drops_the_second_column():
    """Regression modeling the Kotak Bond Short Term Fund case: staged at 83% of
    AUM against a source PDF that sums to 100%. Root cause: a page whose real
    portfolio table is anchored by more than one "PORTFOLIO" marker (Kotak's
    two-column factsheet layout repeats table structure per column) hits a
    PORTFOLIO_STOP_MARKERS line ("Base Expense Ratio", printed between the two
    column blocks on the real page) partway through the first anchor's forward
    scan -- before it reaches the second column's rows. The second "PORTFOLIO"
    anchor starts after that stop point, so its own scan is what actually reaches
    those remaining rows. The old code picked whichever single anchor's (still
    incomplete) scan scored best via _portfolio_quality and discarded the other
    entirely; the fix unions every anchor's holdings so the table is recovered."""
    lines = [
        "KOTAK BOND SHORT TERM FUND",
        "An open ended short term debt scheme investing in instruments such that the",
        "PORTFOLIO",
        "Issuer/Instrument",
        "Rating",
        "% to Net Assets",
        "7.08% Karnataka State Govt Ltd",
        "SOV",
        "3.49",
        "Base Expense Ratio",
        "Regular Plan: 1.12%",
        "PORTFOLIO",
        "Issuer/Instrument",
        "Rating",
        "% to Net Assets",
        "L&T Metro Rail (Hyderabad) Ltd",
        "CRISIL AAA(CE)",
        "1.08",
        "Grand Total",
        "4.57",
    ]
    page_text = "\n".join(lines)

    parsed = parse_combined_factsheet_page(
        page_text,
        SimpleNamespace(source_document_id="doc-kotak-bond", source_url="local", report_month=date(2026, 6, 1)),
        scheme_prefixes=("kotak",),
        continue_after_grand_total=True,
    )

    assert parsed is not None
    names = {row["instrument_name"] for row in parsed.holdings}
    assert any("Karnataka" in name for name in names)
    assert any("L&T Metro Rail" in name for name in names)
    assert len(names) == 2
    assert parsed.metrics["total_percent_aum"] == 4.57
