from __future__ import annotations

from app.mf_ingestion.normalizers.scheme_name_normalizer import (
    _normalize_family_scheme_name,
    _select_best_scheme_candidate,
)
from app.mf_ingestion.services.parsing_service import KNOWN_PARSING_AMC_SCHEME_ALIASES


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


def test_edelweiss_aliases_cover_offshore_and_portfolio_only_variants():
    aliases = KNOWN_PARSING_AMC_SCHEME_ALIASES["edelweiss"]

    assert aliases["edelweiss asean equity offshore fund"] == (
        "140255",
        "edelweiss-asean-equity-off-shore-fund",
    )
    assert aliases["edelweiss us technology equity fof"][0] == "148063"
    assert aliases["edelweiss nifty 100 quality 30 index fnd"][0] == "149254"


def test_edelweiss_aliases_cover_new_official_etfs():
    aliases = KNOWN_PARSING_AMC_SCHEME_ALIASES["edelweiss"]

    assert aliases["edelweiss bse largemid (60:40) stable dividend 50 etf"] == (
        "154535",
        "edelweiss-bse-largemid-60-40-stable-dividend-50-etf",
    )
    assert aliases["edelweiss bse top 10 bank etf"][0] == "154524"
    assert aliases["edelweiss nifty metal etf"][0] == "154461"
