from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.services.asset_resolver import AssetResolution
from app.services.claim_check_contract import ClaimCheckRequest, ClaimFreshness, ClaimMetric, ClaimStatus, ClaimVerdict
from app.services import claim_check_service
from app.services.claim_check_service import ClaimCheckCache, ClaimCheckService, trusted_claim_check_proxy
from app.services.claim_evaluators import ClaimEvaluators
from app.services.claim_parser import ClaimParser
from app.routes.funds import claim_check_endpoint


AS_OF = "2026-09-03"


def _provenance() -> dict:
    return {
        "source": "official_amc_factsheet",
        "source_url": "https://www.exampleamc.com/factsheets/september-2026.pdf",
        "source_document_id": "factsheet-sep-2026",
        "as_of_date": AS_OF,
    }


class _Repository:
    def __init__(self, *, with_provenance: bool = True):
        payload = _provenance() if with_provenance else {}
        self.rows = {
            "ppfas": {
                "scheme_code": "ppfas",
                "scheme_name": "Parag Parikh Flexi Cap Fund Direct Growth",
                "expense_ratio": 0.62,
                "aum": 1000,
                "benchmark": "NIFTY 500 TRI",
                "risk_level": "Very High",
                "fund_manager": "Fund Manager A",
                "investment_objective": "Long-term capital growth",
                "provider_payload": payload,
            },
            "hdfc": {
                "scheme_code": "hdfc",
                "scheme_name": "HDFC Flexi Cap Fund Direct Growth",
                "expense_ratio": 0.85,
                "aum": 2000,
                "benchmark": "NIFTY 500 TRI",
                "risk_level": "Very High",
                "fund_manager": "Fund Manager B",
                "investment_objective": "Long-term capital growth",
                "provider_payload": payload,
            },
        }
        self.holdings = {
            "ppfas": [{
                "as_of_date": AS_OF,
                "security_name": "HDFC Bank Limited",
                "isin": "INE040A01034",
                "sector": "Financial Services",
                "weight_pct": 7.2,
                "source": "amc_disclosure",
                "provider_payload": payload,
            }],
            "hdfc": [{
                "as_of_date": AS_OF,
                "security_name": "HDFC Bank Limited",
                "isin": "INE040A01034",
                "sector": "Financial Services",
                "weight_pct": 5.8,
                "source": "amc_disclosure",
                "provider_payload": payload,
            }],
        }

    def get_fund_by_scheme_code(self, scheme_code: str):
        return self.rows.get(str(scheme_code))

    def get_latest_holdings(self, scheme_code: str):
        return self.holdings.get(str(scheme_code), [])

    def get_sector_rows(self, scheme_code: str):
        return [{
            "sector": "Financial Services",
            "weight_pct": 24.0,
            "source": "amc_disclosure",
            "provider_payload": _provenance(),
            "as_of_date": AS_OF,
        }]


class _Resolver:
    def __init__(self):
        self.calls = 0

    def resolve(self, value: str, *, asset_type: str):
        self.calls += 1
        if "ppfas" in value.casefold() or "parag" in value.casefold():
            return AssetResolution(value, "Parag Parikh Flexi Cap Fund Direct Growth", "mutual_fund", "ppfas", 0.98, "supported", "PPFAS")
        if "hdfc" in value.casefold():
            return AssetResolution(value, "HDFC Flexi Cap Fund Direct Growth", "mutual_fund", "hdfc", 0.98, "supported", "HDFC")
        return AssetResolution(value, None, "mutual_fund", None, 0.0, "not_found")


def _nav_history(start_nav: float, end_multiple: float) -> list[dict]:
    start = date(2023, 9, 3)
    # Enough age for a 3-year CAGR; AMFI evidence is the latest NAV date.
    return [
        {"nav_date": start.isoformat(), "nav": start_nav},
        {"nav_date": (start + timedelta(days=365 * 3 + 1)).isoformat(), "nav": start_nav * end_multiple},
    ]


def _service(*, provenance: bool = True) -> tuple[ClaimCheckService, _Resolver]:
    repository = _Repository(with_provenance=provenance)
    resolver = _Resolver()
    evaluator = ClaimEvaluators(
        repository,
        nav_history_loader=lambda code: _nav_history(100, 1.45) if code == "ppfas" else _nav_history(80, 1.28),
        today=lambda: date(2026, 9, 4),
    )
    return ClaimCheckService(repository, resolver=resolver, evaluators=evaluator, cache=ClaimCheckCache()), resolver


def test_phase_one_returns_a_supported_cost_claim_with_dated_official_evidence():
    service, _ = _service()

    response = service.check("PPFAS Flexi Cap is cheaper than HDFC Flexi Cap")

    claim = response.claims[0]
    assert claim.metric is ClaimMetric.EXPENSE_RATIO
    assert claim.status is ClaimStatus.EVALUATED
    assert claim.verdict is ClaimVerdict.SUPPORTED
    assert claim.freshness is ClaimFreshness.CURRENT
    assert claim.trackable is True
    assert len(claim.evidence) == 2
    assert all(item.as_of_date == AS_OF and item.source_url.startswith("https://") and item.source_fingerprint for item in claim.evidence)


def test_subjective_and_objective_claims_are_returned_as_separate_cards():
    service, _ = _service()

    response = service.check("PPFAS Flexi Cap is safer and cheaper than HDFC Flexi Cap")

    assert [claim.status for claim in response.claims] == [ClaimStatus.CLARIFICATION_REQUIRED, ClaimStatus.EVALUATED]
    assert response.claims[0].verdict is ClaimVerdict.UNVERIFIABLE
    assert response.claims[1].metric is ClaimMetric.EXPENSE_RATIO
    assert response.claims[1].verdict is ClaimVerdict.SUPPORTED


def test_missing_official_provenance_prevents_a_definitive_cost_verdict():
    service, _ = _service(provenance=False)

    response = service.check("PPFAS Flexi Cap is cheaper than HDFC Flexi Cap")

    claim = response.claims[0]
    assert claim.verdict is ClaimVerdict.UNVERIFIABLE
    assert claim.trackable is False
    assert claim.evidence == []
    assert "provenance" in claim.limitations[0]


def test_stale_official_evidence_is_reported_separately_from_the_factual_verdict():
    service, _ = _service()
    service.evaluators.today = lambda: date(2026, 12, 1)

    response = service.check("PPFAS Flexi Cap is cheaper than HDFC Flexi Cap")

    claim = response.claims[0]
    assert claim.verdict is ClaimVerdict.SUPPORTED
    assert claim.freshness is ClaimFreshness.STALE
    assert claim.values
    assert claim.evidence
    assert claim.limitations == []
    assert claim.trackable is True


def test_mismatched_official_reporting_months_block_a_comparison_verdict():
    service, _ = _service()
    service.evaluators.repository.rows["hdfc"]["provider_payload"] = {
        **_provenance(),
        "as_of_date": "2026-08-01",
    }

    claim = service.check("PPFAS Flexi Cap is cheaper than HDFC Flexi Cap").claims[0]

    assert claim.verdict is ClaimVerdict.UNVERIFIABLE
    assert claim.values
    assert len(claim.evidence) == 2
    assert "reporting period" in claim.limitations[0]


def test_normalized_static_value_must_match_its_field_specific_citation():
    service, _ = _service()
    service.evaluators.repository.rows["hdfc"]["provider_payload"] = {
        "amc_trace": {
            "expense_ratio": {
                **_provenance(),
                "value": 0.67,
                "report_month": AS_OF,
            }
        }
    }

    claim = service.check("What is the expense ratio of HDFC Flexi Cap?").claims[0]

    assert claim.verdict is ClaimVerdict.UNVERIFIABLE
    assert claim.values["HDFC Flexi Cap Fund Direct Growth"]["normalized_value"] == 0.85
    assert claim.values["HDFC Flexi Cap Fund Direct Growth"]["cited_source_value"] == 0.67
    assert "conflicts" in claim.limitations[0]


def test_static_string_and_risk_comparisons_use_the_requested_operator():
    service, _ = _service()
    service.evaluators.repository.rows["ppfas"]["risk_level"] = "High"

    benchmark = service.check("Do HDFC Flexi Cap and PPFAS Flexi Cap have the same benchmark?").claims[0]
    risk = service.check("PPFAS Flexi Cap has lower riskometer than HDFC Flexi Cap").claims[0]

    assert benchmark.verdict is ClaimVerdict.SUPPORTED
    assert risk.verdict is ClaimVerdict.SUPPORTED


def test_nav_cagr_is_deterministic_and_backed_by_current_amfi_dates():
    service, _ = _service()

    response = service.check("PPFAS Flexi Cap has higher 3 year CAGR than HDFC Flexi Cap")

    claim = response.claims[0]
    assert claim.metric is ClaimMetric.CAGR
    assert claim.verdict is ClaimVerdict.SUPPORTED
    assert claim.freshness is ClaimFreshness.CURRENT
    assert {item.source_name for item in claim.evidence} == {"AMFI NAV"}
    assert all("value" in value and "as_of_date" in value for value in claim.values.values())


def test_nav_comparison_uses_one_common_end_date_and_window():
    service, _ = _service()
    histories = {
        "ppfas": [
            {"nav_date": "2023-09-01", "nav": 100},
            {"nav_date": "2026-09-01", "nav": 130},
            {"nav_date": "2026-09-03", "nav": 300},
        ],
        "hdfc": [
            {"nav_date": "2023-09-01", "nav": 100},
            {"nav_date": "2026-09-01", "nav": 140},
        ],
    }
    service.evaluators.nav_history_loader = lambda code: histories[code]

    claim = service.check("PPFAS Flexi Cap has higher 3-year CAGR than HDFC Flexi Cap").claims[0]

    assert claim.verdict is ClaimVerdict.CONTRADICTED
    assert {item.as_of_date for item in claim.evidence} == {"2026-09-01"}
    assert {item["as_of_date"] for item in claim.values.values()} == {"2026-09-01"}


def test_holding_and_overlap_claims_require_official_holdings_provenance():
    service, _ = _service()

    holding = service.check("Does PPFAS Flexi Cap hold HDFC Bank?").claims[0]
    overlap = service.check("What is the holdings overlap between PPFAS Flexi Cap and HDFC Flexi Cap?").claims[0]

    assert holding.metric is ClaimMetric.HOLDS_STOCK
    assert holding.verdict is ClaimVerdict.SUPPORTED
    assert holding.values["Parag Parikh Flexi Cap Fund Direct Growth"]["weight_pct"] == 7.2
    assert overlap.metric is ClaimMetric.PORTFOLIO_OVERLAP
    assert overlap.verdict is ClaimVerdict.SUPPORTED
    assert overlap.values["total_overlap_weight_pct"] == 5.8


def test_holding_and_sector_comparisons_compare_weights_instead_of_presence():
    service, _ = _service()
    service.evaluators.repository.get_sector_rows = lambda code: [{
        "sector": "Financial Services",
        "weight_pct": 24.0 if code == "ppfas" else 28.0,
        "source": "amc_disclosure",
        "provider_payload": _provenance(),
        "as_of_date": AS_OF,
    }]

    holding = service.check("PPFAS Flexi Cap holds more HDFC Bank than HDFC Flexi Cap").claims[0]
    sector = service.check("Does HDFC Flexi Cap have greater financial-services exposure than PPFAS Flexi Cap?").claims[0]

    assert holding.metric is ClaimMetric.STOCK_EXPOSURE
    assert holding.verdict is ClaimVerdict.SUPPORTED
    assert sector.metric is ClaimMetric.SECTOR_EXPOSURE
    assert sector.verdict is ClaimVerdict.SUPPORTED


def test_sector_exposure_is_not_misrouted_as_stock_exposure():
    service, _ = _service()

    claim = service.check("PPFAS Flexi Cap has sector exposure to Financial Services").claims[0]

    assert claim.metric is ClaimMetric.SECTOR_EXPOSURE
    assert claim.verdict is ClaimVerdict.SUPPORTED
    assert claim.values["Parag Parikh Flexi Cap Fund Direct Growth"]["weight_pct"] == 24.0


def test_unsupported_advice_never_resolves_or_returns_a_definitive_verdict():
    service, resolver = _service()

    response = service.check("Which fund should I buy?")

    assert response.resolved_entities == []
    assert response.claims[0].status is ClaimStatus.UNSUPPORTED
    assert response.claims[0].verdict is ClaimVerdict.UNVERIFIABLE
    assert resolver.calls == 0


def test_repeated_identical_check_uses_the_read_only_cache():
    service, resolver = _service()

    first = service.check("PPFAS Flexi Cap is cheaper than HDFC Flexi Cap")
    second = service.check("  ppfas flexi cap is cheaper than hdfc flexi cap  ")

    assert resolver.calls == 2
    assert first.model_dump() == second.model_dump()


def test_source_change_refresh_can_bypass_the_read_only_cache():
    service, resolver = _service()

    service.check("PPFAS Flexi Cap is cheaper than HDFC Flexi Cap")
    service.check("PPFAS Flexi Cap is cheaper than HDFC Flexi Cap", use_cache=False)

    assert resolver.calls == 4


def test_direct_backend_route_requires_a_server_only_proxy_key(monkeypatch):
    monkeypatch.delenv("CLAIM_CHECK_INTERNAL_PROXY_KEY", raising=False)
    monkeypatch.setattr(claim_check_service, "CLAIM_CHECK_INTERNAL_PROXY_KEY", "phase-two-secret")

    assert trusted_claim_check_proxy(None) is False
    assert trusted_claim_check_proxy("wrong") is False
    assert trusted_claim_check_proxy("phase-two-secret") is True


def test_trusted_source_refresh_header_bypasses_the_backend_cache(monkeypatch):
    class _Service:
        use_cache = None

        def check(self, request, *, use_cache=True):
            self.use_cache = use_cache
            return {"ok": True}

    service = _Service()
    monkeypatch.setenv("CLAIM_CHECK_INTERNAL_PROXY_KEY", "phase-three-secret")

    response = claim_check_endpoint(
        ClaimCheckRequest(input="PPFAS Flexi Cap expense ratio"),
        "phase-three-secret",
        "bypass",
        service,
    )

    assert response == {"ok": True}
    assert service.use_cache is False


@pytest.mark.parametrize(
    "statement",
    [
        "PPFAS Flexi Cap will have higher returns than HDFC Flexi Cap next year.",
        "PPFAS Flexi Cap is going to have better returns than HDFC Flexi Cap.",
        "PPFAS Flexi Cap has guaranteed higher returns than HDFC Flexi Cap.",
        "Did HDFC Bank cause PPFAS Flexi Cap to outperform HDFC Flexi Cap?",
    ],
)
def test_predictions_guarantees_and_causal_claims_stop_before_resolution(statement):
    service, resolver = _service()

    claim = service.check(statement).claims[0]

    assert claim.status is ClaimStatus.UNSUPPORTED
    assert claim.verdict is ClaimVerdict.UNVERIFIABLE
    assert claim.values == {}
    assert claim.evidence == []
    assert resolver.calls == 0


@pytest.mark.parametrize(
    ("statement", "expected_entities"),
    [
        ("Is HDFC Flexi Cap larger than PPFAS Flexi Cap by AUM?", ("HDFC Flexi Cap", "PPFAS Flexi Cap")),
        ("Compare the 5-year CAGR of PPFAS Flexi Cap and HDFC Flexi Cap.", ("PPFAS Flexi Cap", "HDFC Flexi Cap")),
        ("Which has the higher Sharpe ratio, Axis Flexi Cap or HDFC Flexi Cap?", ("Axis Flexi Cap", "HDFC Flexi Cap")),
        ("Do HDFC Flexi Cap and PPFAS Flexi Cap have the same benchmark?", ("HDFC Flexi Cap", "PPFAS Flexi Cap")),
        ("Who manages PPFAS Flexi Cap?", ("PPFAS Flexi Cap",)),
        ("What is the expense ratio of HDFC Flexi Cap?", ("HDFC Flexi Cap",)),
        ("Compare Parag Flexi and HDFC Flexi Cap expense ratios.", ("Parag Flexi", "HDFC Flexi Cap")),
        ("HDFC Flexi Cap Direct Growth has a lower expense ratio than HDFC Flexi Cap Regular Growth.", ("HDFC Flexi Cap Direct Growth", "HDFC Flexi Cap Regular Growth")),
        ("Does scheme 122639 have a lower expense ratio than 118955?", ("scheme 122639", "118955")),
        ("Compare PPFAS Flexi Cap, HDFC Flexi Cap and Axis Flexi Cap by AUM.", ("PPFAS Flexi Cap", "HDFC Flexi Cap", "Axis Flexi Cap")),
        ("What is the investment objective of Parag Parikh Flexi Cap Fund?", ("Parag Parikh Flexi Cap Fund",)),
    ],
)
def test_rules_parser_extracts_only_fund_entities(statement, expected_entities):
    parsed = ClaimParser().parse(statement)

    entities = tuple(dict.fromkeys(entity for claim in parsed for entity in claim.entity_inputs))

    assert entities == expected_entities


def test_rules_parser_routes_manager_sector_and_holding_weight_language():
    parser = ClaimParser()

    manager = parser.parse("Who manages PPFAS Flexi Cap?")
    sector = parser.parse("Does HDFC Flexi Cap have greater financial-services exposure than PPFAS Flexi Cap?")
    holding = parser.parse("PPFAS Flexi Cap holds more HDFC Bank than HDFC Flexi Cap.")

    assert [claim.metric for claim in manager] == [ClaimMetric.FUND_MANAGER]
    assert [claim.metric for claim in sector] == [ClaimMetric.SECTOR_EXPOSURE]
    assert sector[0].target == "Financial Services"
    assert [claim.metric for claim in holding] == [ClaimMetric.STOCK_EXPOSURE]
    assert holding[0].target == "HDFC Bank"


@pytest.mark.parametrize("term", ["less risky", "lower risk", "stable"])
def test_risk_synonyms_request_a_metric_definition(term):
    parser = ClaimParser()

    parsed = parser.parse(f"PPFAS Flexi Cap is {term} than HDFC Flexi Cap")

    assert parsed[0].subject_term == term
    assert parsed[0].metric is None
