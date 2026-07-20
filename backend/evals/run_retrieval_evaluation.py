from __future__ import annotations

import argparse
import json
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from app.services.document_indexing_service import DocumentIndexingService
    from app.services.document_retrieval_service import CohereCrossEncoderReranker, DocumentRetrievalService, evaluate_retrieval
except ModuleNotFoundError:  # Supports `python -m backend.evals...` from the repository root.
    from backend.app.services.document_indexing_service import DocumentIndexingService
    from backend.app.services.document_retrieval_service import CohereCrossEncoderReranker, DocumentRetrievalService, evaluate_retrieval


DEFAULT_DATASET_DIR = Path(__file__).resolve().parent / "fund_research_v1"


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: expected a JSON object")
        rows.append(value)
    return rows


def load_dataset(dataset_dir: Path = DEFAULT_DATASET_DIR) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]]]:
    manifest = tomllib.loads((dataset_dir / "manifest.toml").read_text(encoding="utf-8"))
    cases = load_jsonl(dataset_dir / "cases.jsonl")
    corpus = load_jsonl(dataset_dir / "corpus.jsonl")
    _validate_dataset(manifest, cases, corpus)
    return manifest, cases, corpus


def _validate_dataset(manifest: dict[str, Any], cases: list[dict[str, Any]], corpus: list[dict[str, Any]]) -> None:
    if not str(manifest.get("dataset_version") or "").strip():
        raise ValueError("dataset_version is required")
    document_ids = {str(row.get("document_id") or "") for row in corpus}
    if "" in document_ids:
        raise ValueError("every corpus row requires document_id")
    case_ids: set[str] = set()
    for case in cases:
        case_id = str(case.get("id") or "")
        if not case_id or case_id in case_ids:
            raise ValueError("case ids must be present and unique")
        case_ids.add(case_id)
        if not str(case.get("query") or "").strip():
            raise ValueError(f"{case_id}: query is required")
        expected = {str(value) for value in case.get("expected_document_ids") or []}
        unknown = expected - document_ids
        if unknown:
            raise ValueError(f"{case_id}: unknown expected documents: {sorted(unknown)}")


class FixtureCorpusRepository:
    def __init__(self, rows: list[dict[str, Any]]):
        self.rows = rows
        self.embeddings: dict[str, list[float]] = {}

    def list_document_chunks(self, *, filters: dict[str, Any], limit: int) -> list[dict[str, Any]]:
        matched = []
        for row in self.rows:
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            if all(metadata.get(key) == value for key, value in filters.items()):
                matched.append(row)
        return matched[:limit]

    def set_embeddings(self, values: list[list[float]]) -> None:
        self.embeddings = {str(row.get("id") or ""): value for row, value in zip(self.rows, values)}

    def match_document_chunks(
        self,
        *,
        query_embedding: list[float],
        filters: dict[str, Any],
        threshold: float,
        limit: int,
    ) -> list[dict[str, Any]]:
        query_norm = sum(value * value for value in query_embedding) ** 0.5
        matches = []
        for row in self.list_document_chunks(filters=filters, limit=len(self.rows)):
            embedding = self.embeddings.get(str(row.get("id") or ""))
            if not embedding or not query_norm:
                continue
            row_norm = sum(value * value for value in embedding) ** 0.5
            similarity = sum(left * right for left, right in zip(query_embedding, embedding)) / max(query_norm * row_norm, 1e-12)
            if similarity >= threshold:
                matches.append({**row, "similarity": similarity})
        return sorted(matches, key=lambda row: float(row.get("similarity") or 0.0), reverse=True)[:limit]


def run_evaluation(
    *,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    limit: int = 5,
    variant: str = "lexical_rerank_v2",
    live_embeddings: bool = False,
    live_cross_encoder: bool = False,
) -> dict[str, Any]:
    manifest, cases, corpus = load_dataset(dataset_dir)
    repository = FixtureCorpusRepository(corpus)
    indexer = DocumentIndexingService(repository)
    if live_embeddings:
        repository.set_embeddings(indexer.embed_texts([str(row.get("chunk_text") or "") for row in corpus]))
    if variant == "lexical_v1":
        service = DocumentRetrievalService.lexical_baseline(repository)
    elif variant == "lexical_rerank_v2":
        service = DocumentRetrievalService(repository)
    elif variant == "hybrid_cross_encoder_v3":
        service = DocumentRetrievalService.v3(
            repository,
            vector_search_enabled=live_embeddings,
            query_embedder=indexer.embed_query if live_embeddings else None,
            cross_encoder_reranker=CohereCrossEncoderReranker() if live_cross_encoder else None,
        )
    else:
        raise ValueError(f"unsupported evaluation variant: {variant}")
    report = evaluate_retrieval(cases, service.search, limit=limit)
    return {
        "dataset_version": manifest["dataset_version"],
        "dataset_status": manifest.get("status"),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "configuration": {
            "limit": limit,
            "corpus_chunks": len(corpus),
            "variant": variant,
            "live_embeddings": live_embeddings,
            "live_cross_encoder": live_cross_encoder,
        },
        **report,
    }


def run_v2_v3_comparison(
    *,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    limit: int = 5,
    live_embeddings: bool = False,
    live_cross_encoder: bool = False,
) -> dict[str, Any]:
    v2 = run_evaluation(dataset_dir=dataset_dir, limit=limit, variant="lexical_rerank_v2")
    v3 = run_evaluation(
        dataset_dir=dataset_dir,
        limit=limit,
        variant="hybrid_cross_encoder_v3",
        live_embeddings=live_embeddings,
        live_cross_encoder=live_cross_encoder,
    )
    metrics = ("recall_at_k", "hit_rate_at_k", "all_relevant_rate_at_k", "mean_reciprocal_rank", "abstention_accuracy")
    return {
        "experiment": "fund_research_v2_vs_v3",
        "dataset_version": v2["dataset_version"],
        "dataset_status": v2.get("dataset_status"),
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
        "production_claim": False,
        "variants": [v2, v3],
        "delta_v3_minus_v2": {
            metric: round(float(v3.get(metric) or 0.0) - float(v2.get(metric) or 0.0), 4)
            for metric in metrics
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate official-document retrieval on a fixed, provider-free dataset")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--variant", choices=("lexical_v1", "lexical_rerank_v2", "hybrid_cross_encoder_v3", "compare"), default="lexical_rerank_v2")
    parser.add_argument("--live-embeddings", action="store_true")
    parser.add_argument("--live-cross-encoder", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.variant == "compare":
        report = run_v2_v3_comparison(
            dataset_dir=args.dataset_dir,
            limit=max(1, min(args.limit, 10)),
            live_embeddings=args.live_embeddings,
            live_cross_encoder=args.live_cross_encoder,
        )
    else:
        report = run_evaluation(
            dataset_dir=args.dataset_dir,
            limit=max(1, min(args.limit, 10)),
            variant=args.variant,
            live_embeddings=args.live_embeddings,
            live_cross_encoder=args.live_cross_encoder,
        )
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
