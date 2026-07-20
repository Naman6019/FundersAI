from evals.run_retrieval_evaluation import DEFAULT_DATASET_DIR, load_dataset, run_evaluation, run_v2_v3_comparison
from evals.run_langfuse_retrieval_experiment import _retrieval_evaluator


def test_seed_dataset_is_versioned_and_covers_retrieval_and_abstention() -> None:
    manifest, cases, corpus = load_dataset(DEFAULT_DATASET_DIR)

    assert manifest["dataset_version"] == "fund_research_golden_v1"
    assert manifest["status"] == "development_seed"
    assert len(cases) >= 12
    assert len(corpus) >= 8
    tags = {tag for case in cases for tag in case.get("tags", [])}
    assert {"direct", "cross_document", "abstention"} <= tags


def test_lexical_seed_baseline_is_reproducible() -> None:
    report = run_evaluation(variant="lexical_v1")

    assert report["retrieval_version"] == "amc_hybrid_retrieval_v1"
    assert report["retrieval_cases"] == 11
    assert report["abstention_cases"] == 3
    assert report["recall_at_k"] == 1.0
    assert report["all_relevant_rate_at_k"] == 1.0
    assert report["abstention_accuracy"] == 0.3333
    assert report["passed_cases"] == 12


def test_relevance_gate_fixes_seed_abstention_failures_without_losing_recall() -> None:
    report = run_evaluation(variant="lexical_rerank_v2")

    assert report["retrieval_version"] == "amc_lexical_rerank_v2"
    assert report["recall_at_k"] == 1.0
    assert report["all_relevant_rate_at_k"] == 1.0
    assert report["abstention_accuracy"] == 1.0
    assert report["passed_cases"] == report["cases"]


def test_v2_v3_comparison_is_reproducible_and_truthful_about_provider_status() -> None:
    report = run_v2_v3_comparison()

    assert report["experiment"] == "fund_research_v2_vs_v3"
    assert report["production_claim"] is False
    assert [variant["configuration"]["variant"] for variant in report["variants"]] == [
        "lexical_rerank_v2",
        "hybrid_cross_encoder_v3",
    ]
    assert report["variants"][1]["configuration"]["live_embeddings"] is False
    assert report["variants"][1]["configuration"]["live_cross_encoder"] is False


def test_langfuse_experiment_evaluator_returns_typed_boolean_scores() -> None:
    scores = _retrieval_evaluator(
        output={"sources": [{"document_id": "doc-1"}], "abstain": False},
        expected_output={"document_ids": ["doc-1"], "abstain": False},
    )

    assert [score.name for score in scores] == ["retrieval_pass", "abstention_correct"]
    assert all(score.value is True for score in scores)
