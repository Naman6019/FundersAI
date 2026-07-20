from evals.run_retrieval_evaluation import DEFAULT_DATASET_DIR, load_dataset, run_evaluation


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
