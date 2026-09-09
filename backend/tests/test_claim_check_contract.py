from __future__ import annotations

import json
import tomllib
from pathlib import Path

from app.services.claim_check_contract import (
    ClaimFreshness,
    ClaimMetric,
    ClaimStatus,
    ClaimVerdict,
    SUBJECTIVE_TERM_CLARIFICATIONS,
    needs_definition_claim,
)


DATASET_DIR = Path(__file__).resolve().parents[1] / "evals" / "fund_truth_check_v1"


def _load_cases() -> list[dict]:
    return [json.loads(line) for line in (DATASET_DIR / "cases.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]


def test_subjective_terms_require_a_metric_definition_not_a_factual_verdict() -> None:
    claim = needs_definition_claim("PPFAS is safer than HDFC.", "safer")

    assert claim.status is ClaimStatus.CLARIFICATION_REQUIRED
    assert claim.verdict is ClaimVerdict.UNVERIFIABLE
    assert claim.freshness is ClaimFreshness.UNKNOWN
    assert claim.clarification is not None
    assert [choice.value for choice in claim.clarification.choices] == [
        "max_drawdown",
        "volatility",
        "riskometer",
    ]


def test_phase_zero_metric_contract_is_restricted_to_supported_claims() -> None:
    assert {metric.value for metric in ClaimMetric} == {
        "expense_ratio", "aum", "cagr", "rolling_return", "sharpe_ratio",
        "max_drawdown", "volatility", "riskometer", "benchmark", "fund_manager",
        "holds_stock", "stock_exposure", "sector_exposure", "holdings_concentration",
        "portfolio_overlap", "investment_objective",
    }
    assert set(SUBJECTIVE_TERM_CLARIFICATIONS) == {
        "safer", "safe", "less risky", "lower risk", "stable", "consistent", "diversified",
    }


def test_evaluation_fixture_is_large_and_reports_its_real_review_state() -> None:
    manifest = tomllib.loads((DATASET_DIR / "manifest.toml").read_text(encoding="utf-8"))
    cases = _load_cases()

    assert manifest["dataset_version"] == "fund_truth_check_v1"
    assert manifest["review"]["human_review_required_before_production_gate"] is True
    assert manifest["review"]["case_count_target_minimum"] <= len(cases) <= manifest["review"]["case_count_target_maximum"]
    assert {case["review_status"] for case in cases} <= {"agent_reviewed", "pending_human_review", "reviewed"}

    # The manifest must count what the fixture actually contains, so the counts
    # cannot drift into overstating how much of the set is approved.
    assert manifest["review"]["agent_reviewed_case_count"] == sum(case["review_status"] == "agent_reviewed" for case in cases)
    assert manifest["review"]["reviewed_case_count"] == sum(case["review_status"] == "reviewed" for case in cases)


def test_every_case_carries_a_review_block_and_only_approved_ones_claim_an_expected_result() -> None:
    for case in _load_cases():
        review = case["review"]
        approved = case["review_status"] in {"agent_reviewed", "reviewed"}
        assert isinstance(review["observed"], dict), case["id"]
        if approved:
            assert review["reviewed_at"] and review["reviewer"], case["id"]
            assert review["expected_status"] and review["expected_verdict"], case["id"]
        else:
            # An unapproved case must not smuggle in an expected result.
            assert review["expected_status"] is None, case["id"]
            assert review["expected_verdict"] is None, case["id"]
            assert review["blocked_on"], case["id"]


def test_approved_refusal_and_clarification_cases_never_expect_a_factual_verdict() -> None:
    forbidden = {"unsupported", "clarification_required", "entity_resolution_required"}
    approved = [case for case in _load_cases() if case["review_status"] in {"agent_reviewed", "reviewed"}]

    assert approved, "the reviewed batch must not be empty"
    for case in approved:
        assert case["review"]["expected_status"] in forbidden, case["id"]
        assert case["review"]["expected_verdict"] == ClaimVerdict.UNVERIFIABLE.value, case["id"]
        assert case["review"]["expected_freshness"] == ClaimFreshness.UNKNOWN.value, case["id"]
        assert case["review"]["expected_evidence"] == [], case["id"]


def test_no_case_produced_a_factual_verdict_where_the_contract_forbids_one() -> None:
    """The one hard safety gate, asserted against the recorded live responses."""
    forbidden_statuses = {"unsupported", "clarification_required", "entity_resolution_required"}
    definitive_verdicts = {ClaimVerdict.SUPPORTED.value, ClaimVerdict.CONTRADICTED.value, ClaimVerdict.MIXED.value}
    for case in _load_cases():
        assert case["review"]["safety_gate_pass"] is True, case["id"]
        assert all(
            status not in forbidden_statuses or verdict not in definitive_verdicts
            for status, verdict in zip(
                case["review"]["observed"]["claim_statuses"],
                case["review"]["observed"]["verdicts"],
            )
        ), case["id"]


def test_recorded_eval_is_non_vacuous() -> None:
    verdicts = [verdict for case in _load_cases() for verdict in case["review"]["observed"]["verdicts"]]

    assert ClaimVerdict.SUPPORTED.value in verdicts
    assert ClaimVerdict.CONTRADICTED.value in verdicts


def test_known_routing_defects_are_recorded_rather_than_silently_passing() -> None:
    """These reach a safe outcome by the wrong path. Fixing one should flip its
    routing_pass to True and shrink this list, not be absorbed unnoticed."""
    cases = {case["id"]: case for case in _load_cases()}
    manifest = tomllib.loads((DATASET_DIR / "manifest.toml").read_text(encoding="utf-8"))

    failing = {cid for cid, case in cases.items() if case["review"].get("routing_pass") is False}
    assert failing == set()
    assert manifest["safety"]["reviewed_cases_failing_routing"] == len(failing)


def test_phase_zero_fixture_covers_supported_ambiguous_unsafe_and_data_gap_paths() -> None:
    cases = _load_cases()
    tags = {tag for case in cases for tag in case["tags"]}
    outcomes = {case["expected"]["outcome"] for case in cases}

    assert {"cost", "performance", "risk", "holdings", "objective", "resolution", "stale_evidence", "missing_field", "unsupported", "ambiguous"} <= tags
    assert {"supported_claim", "clarification_required", "unsupported_claim", "entity_resolution_required", "data_unavailable", "data_stale", "data_conflict", "mixed_routing"} <= outcomes
    assert all(
        not case["expected"]["definitive_verdict_permitted"]
        for case in cases
        if case["expected"]["outcome"] in {"clarification_required", "unsupported_claim", "data_unavailable", "data_conflict", "entity_resolution_required"}
    )


def test_data_quality_cases_name_real_schemes_instead_of_describing_the_fixture_state() -> None:
    cases = {case["id"]: case for case in _load_cases()}
    expected_codes = {
        "missing-expense": {"100291"},
        "stale-expense": {"122639"},
        "missing-history": {"152686", "118955"},
        "stale-holdings": {"122639"},
        "missing-riskometer": {"100291"},
        "stale-aum": {"135853"},
        "missing-overlap": {"100291", "122639"},
        "conflicting-manager": {"154262"},
        "conflicting-benchmark": {"118663"},
        "missing-objective": {"122639"},
    }

    for case_id, scheme_codes in expected_codes.items():
        observed_codes = {str(item["scheme_code"]) for item in cases[case_id]["review"]["observed"]["resolved_entities"]}
        assert observed_codes == scheme_codes, case_id
