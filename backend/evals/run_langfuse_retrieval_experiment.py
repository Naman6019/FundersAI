from __future__ import annotations

import argparse
import os
from typing import Any

from langfuse import get_client
from langfuse.experiment import Evaluation

try:
    from evals.run_retrieval_evaluation import DEFAULT_DATASET_DIR, FixtureCorpusRepository, load_dataset
    from app.services.document_indexing_service import DocumentIndexingService
    from app.services.document_retrieval_service import CohereCrossEncoderReranker, DocumentRetrievalService
except ModuleNotFoundError:
    from backend.evals.run_retrieval_evaluation import DEFAULT_DATASET_DIR, FixtureCorpusRepository, load_dataset
    from backend.app.services.document_indexing_service import DocumentIndexingService
    from backend.app.services.document_retrieval_service import CohereCrossEncoderReranker, DocumentRetrievalService


def _experiment_items(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "input": {"query": case["query"], "filters": case.get("filters") or {}, "limit": 5},
            "expected_output": {
                "document_ids": case.get("expected_document_ids") or [],
                "abstain": bool(case.get("expected_abstain")),
            },
            "metadata": {"case_id": case["id"], "tags": case.get("tags") or []},
        }
        for case in cases
    ]


def _retrieval_evaluator(*, output: Any, expected_output: Any, **_: Any) -> list[Evaluation]:
    expected_ids = {str(value) for value in (expected_output or {}).get("document_ids") or []}
    actual_ids = {str(source.get("document_id") or "") for source in (output or {}).get("sources") or []}
    expects_abstain = bool((expected_output or {}).get("abstain"))
    retrieval_pass = bool((output or {}).get("abstain")) if expects_abstain else expected_ids <= actual_ids
    return [
        Evaluation(name="retrieval_pass", value=retrieval_pass, data_type="BOOLEAN"),
        Evaluation(name="abstention_correct", value=bool((output or {}).get("abstain")) == expects_abstain, data_type="BOOLEAN"),
    ]


def run_langfuse_experiment(*, live_embeddings: bool = False, live_cross_encoder: bool = False) -> list[Any]:
    if not os.getenv("LANGFUSE_PUBLIC_KEY", "").strip() or not os.getenv("LANGFUSE_SECRET_KEY", "").strip():
        raise RuntimeError("langfuse_credentials_missing")

    manifest, cases, corpus = load_dataset(DEFAULT_DATASET_DIR)
    repository = FixtureCorpusRepository(corpus)
    indexer = DocumentIndexingService(repository)
    if live_embeddings:
        repository.set_embeddings(indexer.embed_texts([str(row.get("chunk_text") or "") for row in corpus]))

    services = {
        "v2": DocumentRetrievalService(repository),
        "v3": DocumentRetrievalService.v3(
            repository,
            vector_search_enabled=live_embeddings,
            query_embedder=indexer.embed_query if live_embeddings else None,
            cross_encoder_reranker=CohereCrossEncoderReranker() if live_cross_encoder else None,
        ),
    }
    client = get_client()
    results = []
    for variant, service in services.items():
        def task(*, item: Any, _service=service, **__: Any) -> dict[str, Any]:
            value = item["input"] if isinstance(item, dict) else item.input
            return _service.search(value["query"], filters=value.get("filters") or {}, limit=int(value.get("limit") or 5))

        results.append(
            client.run_experiment(
                name="fund_research_v2_vs_v3",
                run_name=f"{variant}-{manifest['dataset_version']}",
                description="Official-document retrieval comparison; development seed, not a production claim.",
                data=_experiment_items(cases),
                task=task,
                evaluators=[_retrieval_evaluator],
                max_concurrency=1,
                metadata={
                    "variant": variant,
                    "dataset_status": str(manifest.get("status") or "unknown"),
                    "live_embeddings": str(live_embeddings).lower(),
                    "live_cross_encoder": str(live_cross_encoder).lower(),
                },
            )
        )
    client.flush()
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the FundersAI v2-v3 retrieval experiment in Langfuse")
    parser.add_argument("--live-embeddings", action="store_true")
    parser.add_argument("--live-cross-encoder", action="store_true")
    args = parser.parse_args()
    run_langfuse_experiment(live_embeddings=args.live_embeddings, live_cross_encoder=args.live_cross_encoder)


if __name__ == "__main__":
    main()
