from app.mf_ingestion.normalizers.scheme_name_normalizer import (
    _build_relaxed_ilike_pattern,
    _normalize_family_scheme_name,
    _normalize_lookup_text,
    _select_best_scheme_candidate,
)


def test_build_relaxed_ilike_pattern_removes_plan_noise():
    pattern = _build_relaxed_ilike_pattern("ICICI Prudential Multi Asset Fund Direct Growth")
    assert "direct" not in pattern
    assert "growth" not in pattern
    assert "multi" in pattern
    assert "asset" in pattern


def test_build_relaxed_ilike_pattern_ignores_and_symbol_variants():
    pattern = _build_relaxed_ilike_pattern(
        "ICICI Prudential Banking & Financial Services Fund"
    )
    assert "and" not in pattern
    assert "banking%financial" in pattern


def test_select_best_scheme_candidate_fallback_without_direct_growth():
    candidates = [
        {"scheme_code": "1", "scheme_name": "ICICI Prudential Multi Asset Fund - IDCW"},
        {"scheme_code": "2", "scheme_name": "ICICI Prudential Multi Asset Fund - Regular Growth"},
    ]
    selected = _select_best_scheme_candidate("ICICI Multi Asset", candidates)
    assert selected is not None
    assert selected["scheme_code"] == "2"


def test_normalize_family_scheme_name_keeps_regular_as_brand_word():
    """Regression for GitHub issue #2: 'Regular' is a genuine plan-qualifier noise word
    in AMFI's '<Scheme Name> - <Plan> - <Option>' suffix (e.g. 'Savings Fund - Growth -
    Regular Plan'), but some schemes carry 'Regular' as part of their own brand name
    with no suffix at all (e.g. ABSL's raw factsheet title 'Aditya Birla Sun Life
    Regular Savings Fund'). Stripping it unconditionally collapsed two distinct ABSL
    schemes into one family and let 'Regular Savings Fund' inherit 'Savings Fund's
    benchmark."""
    raw_factsheet_name = "Aditya Birla Sun Life Regular Savings Fund"
    wrong_family_candidate = "Aditya Birla Sun Life Savings Fund - Growth - Regular Plan"
    correct_family_candidate = "Aditya Birla Sun Life Regular Savings Fund - Growth / Payment - Regular Plan"

    assert _normalize_family_scheme_name(raw_factsheet_name) != _normalize_family_scheme_name(
        wrong_family_candidate
    )
    assert "regular savings fund" in _normalize_family_scheme_name(raw_factsheet_name)
    assert "regular savings fund" in _normalize_family_scheme_name(correct_family_candidate)


def test_select_best_scheme_candidate_does_not_merge_regular_savings_into_savings():
    candidates = [
        {"scheme_code": "101317", "scheme_name": "Aditya Birla Sun Life Savings Fund - Growth - Regular Plan"},
        {"scheme_code": "119501", "scheme_name": "Aditya Birla Sun Life Savings Fund - Growth - Direct Plan"},
        {"scheme_code": "101816", "scheme_name": "Aditya Birla Sun Life Regular Savings Fund - REGULAR - MONTHLY IDCW"},
        {"scheme_code": "101818", "scheme_name": "Aditya Birla Sun Life Regular Savings Fund - Growth / Payment - Regular Plan"},
        {"scheme_code": "120550", "scheme_name": "Aditya Birla Sun Life Regular Savings Fund - DIRECT - MONTHLY IDCW"},
        {"scheme_code": "120705", "scheme_name": "Aditya Birla Sun Life Regular Savings Fund - Growth / Payment - Direct Plan"},
    ]
    selected = _select_best_scheme_candidate("Aditya Birla Sun Life Regular Savings Fund", candidates)
    assert selected is not None
    assert selected["scheme_code"] in {"101816", "101818", "120550", "120705"}


def test_normalize_family_scheme_name_does_not_split_compound_word_hyphens():
    # "Multi-Cap" is a compound word, not a "<Name> - <Plan>" segment boundary; adding a
    # real plan/option suffix afterward must not change the resulting family.
    assert _normalize_family_scheme_name(
        "Aditya Birla Sun Life Multi-Cap Fund"
    ) == _normalize_family_scheme_name("Aditya Birla Sun Life Multi-Cap Fund - Growth - Direct Plan")


def test_normalize_family_scheme_name_strips_unspaced_hyphen_qualifier_suffix():
    """Regression: mutual_fund_core_snapshot.scheme_name inconsistently omits whitespace
    around the plan-qualifier hyphen (e.g. "Fund-Direct Growth" instead of "Fund - Direct
    Plan"). Verified live against scheme_code 148921 ('...Multi-Cap Fund-Direct Growth')
    and 148635 ('...Fund-Regular Plan-Growth')."""
    assert _normalize_family_scheme_name(
        "Aditya Birla Sun Life Multi-Cap Fund-Direct Growth"
    ) == _normalize_family_scheme_name("Aditya Birla Sun Life Multi-Cap Fund")
    assert _normalize_family_scheme_name(
        "Aditya Birla Sun Life ESG Integration Strategy Fund-Regular Plan-Growth"
    ) == _normalize_family_scheme_name("Aditya Birla Sun Life ESG Integration Strategy Fund")


def test_build_relaxed_ilike_pattern_treats_etf_and_exchange_traded_fund_as_equivalent():
    """Regression against real mutual_fund_core_snapshot/factsheet fixtures surfaced while
    diagnosing UTI's unmapped candidates: the same AMC inconsistently spells out "Exchange
    Traded Fund" in some scheme names ("UTI Nifty Midcap 150 Exchange Traded Fund") and
    abbreviates to "ETF" in others ("UTI Nifty Bank ETF"), while the raw factsheet rows use
    yet another mix ("UTI NIFTY MIDCAP 150 ETF", "UTI Nifty Bank Exchange Traded Fund ETF").
    Stripping "etf"/"exchange"/"traded" as noise (like "fund" already is) lets both spellings
    resolve to the same relaxed pattern instead of requiring an exact wording match."""
    assert _build_relaxed_ilike_pattern("UTI NIFTY MIDCAP 150 ETF") == _build_relaxed_ilike_pattern(
        "UTI Nifty Midcap 150 Exchange Traded Fund"
    )
    assert _build_relaxed_ilike_pattern(
        "UTI Nifty Bank Exchange Traded Fund ETF"
    ) == _build_relaxed_ilike_pattern("UTI Nifty Bank ETF")


def test_build_relaxed_ilike_pattern_strips_mf_prefix_noise():
    """Regression: the raw factsheet row 'UTI MF- Gold Exchange Traded Fund ETF' carries an
    'MF-' AMC-abbreviation prefix that mutual_fund_core_snapshot's 'UTI GOLD Exchange Traded
    Fund' does not. 'mf' must be stripped as noise, not required to appear in the candidate."""
    assert _build_relaxed_ilike_pattern(
        "UTI MF- Gold Exchange Traded Fund ETF"
    ) == _build_relaxed_ilike_pattern("UTI GOLD Exchange Traded Fund")


def test_normalize_lookup_text_splits_glued_number_suffix():
    """Regression: the raw factsheet row 'UTI NIFTY200 QUALITY 30 INDEX FUND' glues the
    index number onto 'NIFTY' with no space, while mutual_fund_core_snapshot spells it
    'UTI Nifty 200 Quality 30 Index Fund'. An unspaced ilike pattern token ('nifty200')
    never matches the spaced canonical text, so letter/digit boundaries must be split."""
    assert _normalize_lookup_text("NIFTY200 QUALITY 30") == _normalize_lookup_text("NIFTY 200 QUALITY 30")


def test_normalize_lookup_text_strips_stray_symbols():
    """Regression: a raw factsheet row was extracted as 'UTI BANKING & PSU FUND@' with a
    stray trailing '@' (a PDF-extraction artifact). The old punctuation regex only stripped
    a fixed list of characters and left '@' glued to 'fund', producing an ilike token
    ('fund@') that could never match any real scheme_name and left the whole row unmapped."""
    assert _normalize_lookup_text("UTI BANKING & PSU FUND@") == _normalize_lookup_text("UTI BANKING & PSU FUND")


def test_normalize_lookup_text_strips_ulip_wrapper_prefix():
    """Regression: the raw factsheet row 'UTI Unit Linked Insurance Plan UTI Long Duration
    Fund' prefixes the real scheme name with a ULIP-wrapper disclosure phrase that repeats
    the AMC name ('...Plan UTI Long Duration Fund'). Stripping the phrase alone leaves a
    doubled 'uti uti' that still can't match mutual_fund_core_snapshot's single-'UTI'
    'UTI Long Duration Fund', so immediately-repeated words must also collapse."""
    assert _normalize_lookup_text(
        "UTI Unit Linked Insurance Plan UTI Long Duration Fund"
    ) == _normalize_lookup_text("UTI Long Duration Fund")


def test_normalize_lookup_text_collapses_immediately_repeated_words():
    assert _normalize_lookup_text("UTI UTI Long Duration Fund") == _normalize_lookup_text(
        "UTI Long Duration Fund"
    )
