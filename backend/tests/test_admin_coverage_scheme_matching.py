from app.mf_ingestion.services.parsing_service import (
    _build_relaxed_ilike_pattern,
    _select_best_scheme_candidate,
)


def test_build_relaxed_ilike_pattern_removes_plan_noise():
    pattern = _build_relaxed_ilike_pattern("ICICI Prudential Multi Asset Fund Direct Growth")
    assert "direct" not in pattern
    assert "growth" not in pattern
    assert "multi" in pattern
    assert "asset" in pattern


def test_select_best_scheme_candidate_fallback_without_direct_growth():
    candidates = [
        {"scheme_code": "1", "scheme_name": "ICICI Prudential Multi Asset Fund - IDCW"},
        {"scheme_code": "2", "scheme_name": "ICICI Prudential Multi Asset Fund - Regular Growth"},
    ]
    selected = _select_best_scheme_candidate("ICICI Multi Asset", candidates)
    assert selected is not None
    assert selected["scheme_code"] == "2"

