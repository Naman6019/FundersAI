from evals.run_retrieval_gate import (
    DEFAULT_BASELINE,
    compare_reports,
    load_baseline,
    run_gate,
)


def _report(**overrides: object) -> dict:
    base = {
        "dataset_version": "fund_research_golden_v1",
        "configuration": {"variant": "lexical_rerank_v2"},
        "recall_at_k": 1.0,
        "hit_rate_at_k": 1.0,
        "all_relevant_rate_at_k": 1.0,
        "mean_reciprocal_rank": 1.0,
        "abstention_accuracy": 1.0,
        "grounded_answer_rate": 0.7857,
        "passed_cases": 14,
    }
    base.update(overrides)
    return base


def test_promoted_baseline_exists_and_matches_current_variant() -> None:
    baseline = load_baseline(DEFAULT_BASELINE)

    assert baseline["dataset_version"] == "fund_research_golden_v1"
    assert baseline["configuration"]["variant"] == "lexical_rerank_v2"
    assert baseline["passed_cases"] == 14


def test_gate_passes_when_current_matches_baseline() -> None:
    report = compare_reports(_report(), _report(), tolerance=0.0, allow_dataset_change=False)

    assert report["passed"] is True
    assert report["regressions"] == []


def test_gate_fails_on_metric_regression() -> None:
    report = compare_reports(
        _report(abstention_accuracy=0.3333, passed_cases=12),
        _report(),
        tolerance=0.0,
        allow_dataset_change=False,
    )

    assert report["passed"] is False
    assert {item["metric"] for item in report["regressions"]} == {"abstention_accuracy", "passed_cases"}


def test_gate_fails_on_dataset_version_change_unless_allowed() -> None:
    changed = _report(dataset_version="fund_research_golden_v2")

    assert compare_reports(changed, _report(), tolerance=0.0, allow_dataset_change=False)["passed"] is False
    assert compare_reports(changed, _report(), tolerance=0.0, allow_dataset_change=True)["passed"] is True


def test_live_gate_against_promoted_baseline_passes() -> None:
    report = run_gate()

    assert report["passed"] is True
    assert report["variant"] == "lexical_rerank_v2"
