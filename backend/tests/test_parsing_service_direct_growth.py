from __future__ import annotations

from app.mf_ingestion.services.parsing_service import (
    _normalize_family_scheme_name,
    _select_best_scheme_candidate,
)


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


def test_select_best_scheme_candidate_keeps_exact_etf_family_over_direct_fof():
    candidates = [
        {"scheme_code": "2001", "scheme_name": "ICICI Prudential Silver ETF"},
        {
            "scheme_code": "2002",
            "scheme_name": "ICICI Prudential Silver ETF FOF - Direct Plan - Growth",
        },
    ]

    best = _select_best_scheme_candidate("ICICI Prudential Silver ETF", candidates)

    assert best is not None
    assert best["scheme_code"] == "2001"


def test_family_name_normalization_removes_plan_noise_and_spacing_variants():
    assert _normalize_family_scheme_name(
        "Kotak Flexi Cap Fund - Direct Plan - Growth Option"
    ) == _normalize_family_scheme_name("Kotak Flexicap Fund")
