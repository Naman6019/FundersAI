from app.mf_ingestion.normalizers.scheme_name_normalizer import match_scheme_name


def test_match_scheme_name_prefers_exact_match_over_token_subset():
    candidates = [
        "ICICI Prudential Large & Mid Cap Fund",
        "ICICI Prudential Large Cap Fund",
        "ICICI Prudential US Bluechip Equity Fund",
    ]
    match = match_scheme_name("ICICI Prudential Large Cap Fund", candidates)
    assert match.canonical_name == "ICICI Prudential Large Cap Fund"
    assert match.confidence == 100.0

