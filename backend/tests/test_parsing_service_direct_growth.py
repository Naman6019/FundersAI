from __future__ import annotations

from app.mf_ingestion.services.parsing_service import _select_best_scheme_candidate


def test_select_best_scheme_candidate_prefers_direct_growth_variant():
    candidates = [
        {"scheme_code": "1001", "scheme_name": "ICICI Prudential Large Cap Fund - Regular Plan - Growth"},
        {"scheme_code": "1002", "scheme_name": "ICICI Prudential Large Cap Fund - Direct Plan - Growth"},
        {"scheme_code": "1003", "scheme_name": "ICICI Prudential Large Cap Fund - Direct Plan - IDCW"},
    ]
    best = _select_best_scheme_candidate("ICICI Prudential Large Cap Fund", candidates)
    assert best is not None
    assert best["scheme_code"] == "1002"


def test_select_best_scheme_candidate_returns_none_when_only_non_direct_variants():
    candidates = [
        {"scheme_code": "1001", "scheme_name": "ICICI Prudential Large Cap Fund - Regular Plan - Growth"},
        {"scheme_code": "1003", "scheme_name": "ICICI Prudential Large Cap Fund - Direct Plan - IDCW"},
    ]
    best = _select_best_scheme_candidate("ICICI Prudential Large Cap Fund", candidates)
    assert best is not None
    assert best["scheme_code"] == "1001"

