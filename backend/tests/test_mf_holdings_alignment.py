from __future__ import annotations

from app.services.mf_holdings_alignment import validate_holdings_alignment


def _row(company: str, isin: str | None, pct: float = 1.0) -> dict:
    return {
        "MF_ID": "28",
        "Scheme_Name": "UTI - Arbitrage Fund",
        "Company_Name": company,
        "ISIN": isin,
        "Security_Type": "EQUITY SHARES",
        "MarketValuePercentage": pct,
    }


def test_aligned_payload_is_usable():
    rows = [
        _row("OIL & NATURAL GAS CORPORATION LTD.", "INE213A01029", 0.83),
        _row("LARSEN AND TOUBRO LIMITED", "INE018A01030", 4.42),
        _row("INFOSYS LTD.", "INE009A01021", 3.20),
        _row("ITC LTD.", "INE154A01025", 2.52),
    ]
    result = validate_holdings_alignment(rows)

    assert result.is_usable is True
    assert result.isin_name_conflicts == 0
    assert result.checked_isins == 4
    assert result.issues == []


def test_misaligned_payload_is_rejected():
    """The exact Apr-Jun 2026 corruption: one ISIN paired with many companies."""
    rows = [
        _row("ITC LTD.", "INE009A01021", -1.36),
        _row("INFOSYS LTD.", "INE009A01021", 3.20),
        _row("COAL INDIA LTD.", "INE009A01021", 0.96),
        _row("VOLTAS LTD.", "INE009A01021", 0.0),
        _row("AUROBINDO PHARMA LTD.", "INE009A01021", -0.79),
    ]
    result = validate_holdings_alignment(rows)

    assert result.is_usable is False
    assert "isin_company_name_conflict" in result.issues
    assert result.isin_name_conflicts == 1
    assert result.checked_isins == 1


def test_realistic_widespread_misalignment_is_rejected():
    """Corruption spreads across many ISINs, not one; the threshold must catch that."""
    rows = []
    companies = ["ITC LTD.", "INFOSYS LTD.", "COAL INDIA LTD.", "VOLTAS LTD.",
                 "NMDC LTD.", "UPL LTD.", "HERO MOTOCORP LTD.", "OIL INDIA LTD."]
    isins = ["INE009A01021", "INE018A01030", "INE154A01025", "INE101A01026"]
    for i, company in enumerate(companies):
        rows.append(_row(company, isins[i % len(isins)], 1.0))
    result = validate_holdings_alignment(rows)

    assert result.is_usable is False
    assert "isin_company_name_conflict" in result.issues


def test_cosmetic_name_variation_for_one_issuer_is_not_a_conflict():
    """The same issuer printed with different punctuation/suffixes must not look like corruption."""
    rows = [
        _row("RELIANCE INDUSTRIES LTD.", "INE002A01018", 5.0),
        _row("RELIANCE INDUSTRIES LIMITED", "INE002A01018", 5.0),
        _row("INFOSYS LTD.", "INE009A01021", 3.2),
        _row("ITC LTD.", "INE154A01025", 2.5),
        _row("LARSEN AND TOUBRO LIMITED", "INE018A01030", 4.4),
        _row("MAHINDRA & MAHINDRA LTD.", "INE101A01026", 2.5),
        _row("COAL INDIA LTD.", "INE522F01014", 0.96),
        _row("TECH MAHINDRA LTD", "INE669C01036", 0.81),
    ]
    result = validate_holdings_alignment(rows)

    assert result.is_usable is True
    assert result.isin_name_conflicts == 0


def test_genuinely_different_issuers_sharing_an_isin_are_rejected():
    """A single unrelated issuer clash is still corruption and must not be written through."""
    rows = [
        _row("INFOSYS LTD.", "INE009A01021", 3.2),
        _row("ITC LTD.", "INE009A01021", 2.5),
    ]
    result = validate_holdings_alignment(rows)

    assert result.is_usable is False
    assert "isin_company_name_conflict" in result.issues
    assert result.isin_name_conflicts == 1


def test_empty_payload_is_not_usable():
    result = validate_holdings_alignment([])

    assert result.is_usable is False
    assert "holdings_empty" in result.issues


def test_null_isins_are_counted_but_do_not_by_themselves_reject():
    """Some real rows legitimately carry no ISIN; that is a coverage gap, not corruption."""
    rows = [
        _row("SOME UNLISTED DEBENTURE", None, 1.0),
        _row("INFOSYS LTD.", "INE009A01021", 3.2),
        _row("ITC LTD.", "INE154A01025", 2.5),
        _row("LARSEN AND TOUBRO LIMITED", "INE018A01030", 4.4),
        _row("MAHINDRA & MAHINDRA LTD.", "INE101A01026", 2.5),
    ]
    result = validate_holdings_alignment(rows)

    assert result.is_usable is True
    assert result.null_isin_rows == 1
    assert result.checked_isins == 4


def test_payload_with_no_isin_column_is_flagged_but_usable_for_display():
    rows = [
        _row("INFOSYS LTD.", None, 3.2),
        _row("ITC LTD.", None, 2.5),
        _row("LARSEN AND TOUBRO LIMITED", None, 4.4),
    ]
    result = validate_holdings_alignment(rows)

    assert result.is_usable is True
    assert "isin_column_absent" in result.issues


def test_negative_weights_are_counted():
    """Derivative positions legitimately print negative percentages."""
    rows = [
        _row("INFOSYS LTD.", "INE009A01021", -1.4),
        _row("ITC LTD.", "INE154A01025", 2.5),
        _row("LARSEN AND TOUBRO LIMITED", "INE018A01030", 4.4),
        _row("MAHINDRA & MAHINDRA LTD.", "INE101A01026", 2.5),
    ]
    result = validate_holdings_alignment(rows)

    assert result.is_usable is True
    assert result.negative_weight_rows == 1


def test_literal_blank_isin_sentinel_is_treated_as_absent():
    """LIC sends the string "(blank)" for a missing ISIN; that is not a shared ISIN.

    Treating it as real grouped Container Corporation and Infosys under one ISIN and reported
    false corruption against an otherwise clean payload.
    """
    rows = [
        _row("Container Corporation Of India Ltd.", "(blank)", 4.7),
        _row("Infosys Ltd.", "(blank)", 3.2),
        _row("ITC LTD.", "INE154A01025", 2.5),
        _row("LARSEN AND TOUBRO LIMITED", "INE018A01030", 4.4),
        _row("MAHINDRA & MAHINDRA LTD.", "INE101A01026", 2.5),
    ]
    result = validate_holdings_alignment(rows)

    assert result.is_usable is True
    assert result.isin_name_conflicts == 0
    assert result.null_isin_rows == 2


def test_other_blank_sentinels_are_also_treated_as_absent():
    for sentinel in ["(blank)", "blank", "N/A", "NA", "None", "NULL", "-", "--"]:
        rows = [
            _row("Infosys Ltd.", sentinel, 3.2),
            _row("ITC LTD.", "INE154A01025", 2.5),
        ]
        result = validate_holdings_alignment(rows)
        assert result.is_usable is True, f"sentinel {sentinel!r} should read as absent"
        assert result.null_isin_rows == 1, f"sentinel {sentinel!r} should count as null"
