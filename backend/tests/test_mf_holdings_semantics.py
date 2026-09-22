"""Tests for semantic ISIN-identity validation.

The contract these pin, stated once: within a single source document, one ISIN must denote one
security. The check must catch that (sensitivity) without flagging the pervasive, legitimate
naming variance across AMCs (specificity). Both halves are tested, because a check that only
passes one of them is useless — either it misses corruption or it rejects every real document.

Measured against live data when written: 0 conflicts across 36 real AMC documents / 59,344
rows, and 33 conflicts on the known-corrupt AMFI payload.
"""
from __future__ import annotations

from app.services.mf_holdings_semantics import (
    issuer_tokens,
    maturity_compatible,
    normalise_isin,
    parse_coupon,
    parse_maturity,
    validate_isin_identity,
)


def _row(isin: str | None, name: str) -> dict:
    return {"isin": isin, "instrument_name": name}


# ─── Sensitivity: must catch real corruption ─────────────────────────────────

def test_unrelated_issuers_sharing_an_isin_are_a_conflict():
    """The exact AMFI failure mode: one ISIN attached to unrelated issuers."""
    rows = [
        _row("INE009A01021", "INFOSYS LTD."),
        _row("INE009A01021", "ITC LTD."),
        _row("INE009A01021", "COAL INDIA LTD."),
    ]
    result = validate_isin_identity(rows)

    assert result.is_consistent is False
    assert len(result.conflicts) == 1
    assert result.conflicts[0].kind == "issuer_tokens"
    assert result.review_issues() == ["isin_identity_issuer_tokens"]


def test_two_different_coupons_for_one_isin_is_a_conflict():
    """A bond has exactly one coupon, so two coupons cannot belong to one ISIN."""
    rows = [
        _row("INE000000001", "6.27% IKF Finance Ltd. (12/08/2027)"),
        _row("INE000000001", "9.40% IKF Finance Limited (12/08/2027)"),
    ]
    result = validate_isin_identity(rows)

    assert result.is_consistent is False
    assert result.conflicts[0].kind == "coupon"


def test_incompatible_maturities_for_one_isin_is_a_conflict():
    rows = [
        _row("INE000000002", "8.09% India Universal Trust AL2 - 21/09/2027"),
        _row("INE000000002", "8.09% India Universal Trust AL2 - 21/11/2027"),
    ]
    result = validate_isin_identity(rows)

    assert result.is_consistent is False
    assert result.conflicts[0].kind == "maturity"


# ─── Specificity: must NOT flag legitimate naming variance ───────────────────

def test_same_security_under_different_amc_spellings_is_not_a_conflict():
    """One G-Sec, five AMC spellings. This is the case that must not be rejected."""
    rows = [
        _row("IN0020250141", "06.36% GSEC Mat- 16/02/2031"),
        _row("IN0020250141", "6.36% CGL 2031"),
        _row("IN0020250141", "6.36% GOI 16-Feb-2031"),
        _row("IN0020250141", "6.36% GOI 16022031"),
        _row("IN0020250141", "GOI - 6.36% (16/02/2031)"),
        _row("IN0020250141", "6.36% Government of India 2031"),
    ]
    result = validate_isin_identity(rows)

    assert result.is_consistent is True
    assert result.conflicts == []
    assert result.label_variants == 1


def test_year_only_maturity_agrees_with_a_full_date_in_the_same_year():
    """Maturity must be compared at shared granularity, not as a string."""
    rows = [
        _row("IN0000000001", "7.18% Tamil Nadu SDL 26/07/2027"),
        _row("IN0000000001", "7.18% Tamil Nadu SDL 2027"),
    ]
    result = validate_isin_identity(rows)

    assert result.is_consistent is True
    assert result.conflicts == []


def test_split_vs_joined_word_forms_are_flagged_for_review_not_silently_accepted():
    """A known limitation, asserted so it cannot regress into silent acceptance.

    "Tamil Nadu" and "Tamilnadu" are one issuer spelled two ways, but they share no whole token.
    Accepting them would require a containment rule, and containment is unsound: it also accepts
    "MAHINDRA & MAHINDRA" as "MAHINDRA AND MAHINDRA FINANCIAL SERVICES", which are two different
    issuers. The check therefore flags this shape for review. That is the deliberate failure
    direction: a false positive costs one human glance, a false negative corrupts ISIN joins.
    """
    rows = [
        _row("IN3120170078", "7.18% Tamil Nadu SDL 26/07/2027"),
        _row("IN3120170078", "7.18% Tamilnadu State Development Loans (26/07/2027)"),
    ]
    result = validate_isin_identity(rows)

    assert result.is_consistent is False
    assert result.conflicts[0].kind == "issuer_tokens"

def test_garbled_label_sharing_one_token_is_not_a_conflict():
    """Groww prints a Silver ETF's issuer as "NIPPON INDIA MUTUALFUND" in one sheet.

    The ISIN, quantity and unit price all agree across rows (both imply Rs 223.21/unit), so the
    ISIN is right and only the label is wrong. It must not be reported as corruption.
    """
    rows = [
        _row("INF204KC1402", "NIPPON INDIA MUTUALFUND"),
        _row("INF204KC1402", "Nippon India MF- Nippon India Silver ETF"),
    ]
    result = validate_isin_identity(rows)

    assert result.is_consistent is True
    assert result.label_variants == 1


def test_acronym_style_label_variant_is_not_a_conflict():
    rows = [
        _row("INE020B01018", "REC LTD"),
        _row("INE020B01018", "REC Limited"),
    ]
    assert validate_isin_identity(rows).is_consistent is True


def test_strips_positions_with_two_dates_are_not_a_maturity_conflict():
    """A principal-and-coupon strips position legitimately prints two dates for one ISIN."""
    rows = [
        _row("IN000227C024", "6.76% GOI (MD22/02/2061)-Strips (C)-(MD22/02/2027)"),
        _row("IN000227C024", "GOI 22.02.2027 GOV"),
    ]
    result = validate_isin_identity(rows)

    assert result.is_consistent is True
    assert result.conflicts == []


def test_distinct_isins_with_distinct_names_are_clean():
    rows = [
        _row("INE090A01021", "ICICI Bank Limited"),
        _row("INE040A01034", "HDFC Bank Limited"),
        _row("INE002A01018", "Reliance Industries Limited"),
    ]
    result = validate_isin_identity(rows)

    assert result.is_consistent is True
    assert result.checked_isins == 3
    assert result.label_variants == 0


# ─── ISIN sentinel and helper behaviour ──────────────────────────────────────

def test_blank_isin_sentinels_are_skipped_not_grouped():
    """AMFI sends "(blank)"; grouping on it would flag unrelated companies."""
    rows = [
        _row("(blank)", "Container Corporation Of India Ltd."),
        _row("(blank)", "Infosys Ltd."),
        _row("N/A", "Coal India Ltd."),
        _row(None, "UPL Ltd."),
    ]
    result = validate_isin_identity(rows)

    assert result.is_consistent is True
    assert result.checked_isins == 0


def test_normalise_isin_recognises_common_sentinels():
    for sentinel in ["(blank)", "blank", "N/A", "na", "None", "NULL", "-", "--", "", "   "]:
        assert normalise_isin(sentinel) == "", f"{sentinel!r} should read as absent"
    assert normalise_isin("INE009A01021") == "INE009A01021"


def test_parse_coupon_handles_printing_variants():
    assert parse_coupon("6.36% GOI") == 6.36
    assert parse_coupon("06.36% GSEC") == 6.36
    assert parse_coupon("8,20% Bond") == 8.20
    assert parse_coupon("INF204KC1402 Silver ETF") is None


def test_parse_maturity_handles_printing_variants():
    assert parse_maturity("GOI 16-Feb-2031") == (2031, 2, 16)
    assert parse_maturity("GOI 16022031") == (2031, 2, 16)
    assert parse_maturity("GOI (16/02/2031)") == (2031, 2, 16)
    assert parse_maturity("CGL 2031") == (2031, None, None)
    assert parse_maturity("Nippon India Silver ETF") is None


def test_maturity_compatible_compares_at_shared_granularity():
    assert maturity_compatible((2031, 2, 16), (2031, None, None)) is True
    assert maturity_compatible((2031, 2, 16), (2031, 2, 16)) is True
    assert maturity_compatible((2031, 2, 16), (2033, 9, 22)) is False
    # An absent date on either side is not evidence of a conflict.
    assert maturity_compatible(None, (2031, 2, 16)) is True


def test_issuer_tokens_drop_stopwords_and_numbers():
    # "Mutual" and "Fund" are wrapper words, so both are dropped; only the brand survives.
    assert issuer_tokens("6.36% Government of India Ltd.") == set()
    assert issuer_tokens("Nippon India Mutual Fund") == {"nippon"}


def test_split_and_joined_name_forms_share_a_token_when_they_can():
    """Where the brand word survives intact, spacing variance is accepted."""
    rows_nospace = [
        _row("INF204KC1402", "NIPPON INDIA MUTUALFUND"),
        _row("INF204KC1402", "Nippon India MF- Nippon India Silver ETF"),
    ]
    assert validate_isin_identity(rows_nospace).is_consistent is True


def test_review_issue_codes_are_stable_and_deduplicated():
    rows = [
        _row("INE000000010", "INFOSYS LTD."),
        _row("INE000000010", "ITC LTD."),
        _row("INE000000011", "COAL INDIA LTD."),
        _row("INE000000011", "VOLTAS LTD."),
    ]
    result = validate_isin_identity(rows)

    assert result.is_consistent is False
    # Two conflicting ISINs, both of the same kind: the code must appear once.
    assert result.review_issues() == ["isin_identity_issuer_tokens"]
