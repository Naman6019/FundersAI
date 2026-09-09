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


def test_portfolio_holdings_heading_anchors_a_table():
    """Only "Portfolio" used to anchor a holdings table, which is Kotak's and
    Motilal's layout and nobody else's. Measured against live R2 factsheets, every
    other AMC that publishes a full portfolio in its factsheet prints a different
    heading -- their pages matched on scheme name and were then discarded for want
    of a start anchor, so the whole factsheet lane returned zero holdings for them.
    "Portfolio Holdings" is the Helios/Zerodha spelling."""
    lines = [
        "Helios Flexi Cap Fund",
        "An open ended dynamic equity scheme investing across market capitalisation",
        "Portfolio Holdings",
        "Name of Instrument",
        "% of Net Assets",
        "HDFC Bank Ltd",
        "5.10",
        "Bharti Airtel Ltd",
        "4.20",
        "Grand Total",
        "9.30",
    ]

    parsed = parse_combined_factsheet_page(
        "\n".join(lines),
        SimpleNamespace(source_document_id="doc-helios", source_url="local", report_month=date(2026, 7, 1)),
        scheme_prefixes=("helios",),
    )

    assert parsed is not None
    assert parsed.scheme_name == "Helios Flexi Cap Fund"
    names = {row["instrument_name"] for row in parsed.holdings}
    assert names == {"HDFC Bank Ltd", "Bharti Airtel Ltd"}
    assert parsed.metrics["total_percent_aum"] == 9.30


def test_bare_instrument_column_header_anchors_a_table_without_a_heading():
    """Several AMCs print the "Portfolio" heading as a graphic, so the extracted
    text jumps straight from the scheme name to the column header. The instrument
    column header is itself proof the table has started, so it anchors on its own
    -- without this, those pages yield nothing at all."""
    lines = [
        "Quantum Ethical Fund",
        "An open ended equity scheme following ethical principles",
        "Name of Instrument",
        "% to Net Assets",
        "Infosys Ltd",
        "6.40",
        "Tata Consultancy Services Ltd",
        "3.60",
        "Grand Total",
        "10.00",
    ]

    parsed = parse_combined_factsheet_page(
        "\n".join(lines),
        SimpleNamespace(source_document_id="doc-quantum", source_url="local", report_month=date(2026, 7, 1)),
        scheme_prefixes=("quantum",),
    )

    assert parsed is not None
    names = {row["instrument_name"] for row in parsed.holdings}
    assert names == {"Infosys Ltd", "Tata Consultancy Services Ltd"}


def test_evidence_window_reaches_past_a_date_stamp_under_the_heading():
    """The corroboration window used to stop nine lines after the heading. AMCs
    that print a date stamp and a footnote between the heading and the column
    header push the evidence past that, so the heading was rejected."""
    lines = [
        "Canara Robeco Multi Asset Allocation Fund",
        "Portfolio",
        "(as at July 31, 2026)",
        "Note 1",
        "Note 2",
        "Note 3",
        "Note 4",
        "Note 5",
        "Note 6",
        "Note 7",
        "% to Net Assets",
        "Reliance Industries Ltd",
        "7.15",
        "Grand Total",
        "7.15",
    ]

    parsed = parse_combined_factsheet_page(
        "\n".join(lines),
        SimpleNamespace(source_document_id="doc-canara", source_url="local", report_month=date(2026, 7, 1)),
        scheme_prefixes=("canara robeco", "canara"),
    )

    assert parsed is not None
    assert any("Reliance Industries" in row["instrument_name"] for row in parsed.holdings)


def test_bare_heading_without_table_evidence_is_not_a_portfolio_start():
    """The relaxed heading list must still not fire on contents pages and section
    dividers, which is what the corroboration check is for. A "Holdings" line with
    no table underneath it must not open a scan."""
    lines = [
        "Taurus Flexi Cap Fund",
        "Holdings",
        "Refer page 12 for the complete portfolio",
        "Fund Manager: Someone",
        "Inception Date: 01-Jan-2020",
    ]

    parsed = parse_combined_factsheet_page(
        "\n".join(lines),
        SimpleNamespace(source_document_id="doc-taurus", source_url="local", report_month=date(2026, 7, 1)),
        scheme_prefixes=("taurus",),
    )

    assert parsed is None


def test_dated_heading_anchors_a_table():
    """AMCs date the heading in place -- "Scheme Portfolio as on 31st July 2026" is the
    same heading as "Portfolio". Only the parenthesised "Portfolio (as on ...)" form was
    special-cased, so Choice's factsheet tables were skipped entirely."""
    lines = [
        "Choice Nifty 50 Index Fund",
        "Scheme Portfolio as on 31st July 2026",
        "Name of Instrument/Issuer",
        "% to AUM",
        "HDFC Bank Ltd.",
        "10.21",
        "ICICI Bank Ltd.",
        "9.17",
        "Grand Total",
        "19.38",
    ]

    parsed = parse_combined_factsheet_page(
        "\n".join(lines),
        SimpleNamespace(source_document_id="doc-choice", source_url="local", report_month=date(2026, 7, 1)),
        scheme_prefixes=("choice",),
    )

    assert parsed is not None
    names = {row["instrument_name"] for row in parsed.holdings}
    assert names == {"HDFC Bank Ltd.", "ICICI Bank Ltd."}


def test_qualified_instrument_column_header_still_anchors():
    """The column header is matched as a prefix: AMCs qualify it their own way, and an
    exact match skipped "Name of Instrument/Issuer" tables."""
    lines = [
        "Choice Overnight Fund",
        "Name of Instrument/Issuer",
        "% to AUM",
        "TREPS / Reverse Repo Investments",
        "99.25",
    ]

    parsed = parse_combined_factsheet_page(
        "\n".join(lines),
        SimpleNamespace(source_document_id="doc-choice-on", source_url="local", report_month=date(2026, 7, 1)),
        scheme_prefixes=("choice",),
    )

    assert parsed is not None
    assert len(parsed.holdings) == 1


def test_scheme_name_is_found_below_the_table():
    """PDF text extraction does not preserve visual order. On Choice's factsheet the
    portfolio table lands at line 83 and the scheme name only at line 245, so an
    80-line scan found the page nameless and discarded a complete portfolio."""
    lines = [
        "Scheme Portfolio as on 31st July 2026",
        "Name of Instrument/Issuer",
        "% to AUM",
        "Reliance Industries Ltd.",
        "7.15",
        "Grand Total",
        "7.15",
        *[f"filler line {n}" for n in range(120)],
        "Choice Nifty 50 Index Fund",
    ]

    parsed = parse_combined_factsheet_page(
        "\n".join(lines),
        SimpleNamespace(source_document_id="doc-late-name", source_url="local", report_month=date(2026, 7, 1)),
        scheme_prefixes=("choice",),
    )

    assert parsed is not None
    assert parsed.scheme_name == "Choice Nifty 50 Index Fund"


def test_the_first_scheme_name_on_a_page_still_wins():
    """Widening the scan must not change any page that already resolved a name: the
    first match wins, so a later mention cannot displace the page's own heading."""
    lines = [
        "Kotak Bond Short Term Fund",
        "PORTFOLIO",
        "Issuer/Instrument",
        "% to Net Assets",
        "7.08% Karnataka State Govt Ltd",
        "3.49",
        *[f"filler {n}" for n in range(100)],
        "Kotak Flexicap Fund",
    ]

    parsed = parse_combined_factsheet_page(
        "\n".join(lines),
        SimpleNamespace(source_document_id="doc-kotak", source_url="local", report_month=date(2026, 6, 1)),
        scheme_prefixes=("kotak",),
    )

    assert parsed is not None
    assert parsed.scheme_name == "Kotak Bond Short Term Fund"
