from __future__ import annotations

import hashlib
import os
import re
from collections import Counter
from typing import Any

from rapidfuzz import fuzz

BASELINE_RETRIEVAL_VERSION = "amc_hybrid_retrieval_v1"
RETRIEVAL_VERSION = "amc_lexical_rerank_v2"
EMBEDDING_VERSION = "amc_document_embedding_v1"
EMBEDDING_MODEL = "openai/text-embedding-3-small"
EMBEDDING_DIMENSIONS = 1_536
CHUNK_SIZE = 1_200
CHUNK_OVERLAP = 160


def chunk_document_text(text: str) -> list[str]:
    """Deterministic, paragraph-aware chunks; only callers with parsed official docs may use it."""
    clean = re.sub(r"\s+", " ", str(text or "")).strip()
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + CHUNK_SIZE)
        if end < len(clean):
            boundary = clean.rfind(". ", start, end)
            if boundary > start + CHUNK_SIZE // 2:
                end = boundary + 1
        chunks.append(clean[start:end].strip())
        if end == len(clean):
            break
        start = max(end - CHUNK_OVERLAP, start + 1)
    return chunks


def chunk_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _tokens(value: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9]{3,}", value.lower())}


_QUERY_STOPWORDS = {
    "across", "contains", "document", "evidence", "factsheet", "find", "from", "into", "lists",
    "locate", "official", "report", "requested", "section", "source", "that", "their", "this", "which",
    "where", "with",
}


def _meaningful_query_tokens(query: str) -> set[str]:
    return _tokens(query) - _QUERY_STOPWORDS


class DocumentRetrievalService:
    """Hybrid ranking over already embedded, official AMC document chunks."""

    def __init__(
        self,
        repository: Any,
        *,
        retrieval_version: str = RETRIEVAL_VERSION,
        reranker_enabled: bool = True,
        relevance_gate_enabled: bool = True,
        vector_search_enabled: bool = False,
        query_embedder: Any = None,
        minimum_query_coverage: float = 0.5,
    ):
        self.repository = repository
        self.retrieval_version = retrieval_version
        self.reranker_enabled = reranker_enabled
        self.relevance_gate_enabled = relevance_gate_enabled
        self.vector_search_enabled = vector_search_enabled
        self.query_embedder = query_embedder
        self.minimum_query_coverage = minimum_query_coverage

    @classmethod
    def configured(cls, repository: Any) -> "DocumentRetrievalService":
        vector_enabled = os.getenv("MF_RESEARCH_VECTOR_SEARCH_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        query_embedder = None
        if vector_enabled:
            from app.services.document_indexing_service import DocumentIndexingService

            query_embedder = DocumentIndexingService(repository).embed_query
        return cls(repository, vector_search_enabled=vector_enabled, query_embedder=query_embedder)

    @classmethod
    def lexical_baseline(cls, repository: Any) -> "DocumentRetrievalService":
        return cls(
            repository,
            retrieval_version=BASELINE_RETRIEVAL_VERSION,
            reranker_enabled=False,
            relevance_gate_enabled=False,
        )

    def search(self, query: str, *, filters: dict[str, Any] | None = None, limit: int = 5) -> dict[str, Any]:
        filters = {key: value for key, value in (filters or {}).items() if value not in (None, "")}
        query = str(query or "").strip()
        if not query:
            return self._empty_result(query_coverage=0.0, vector_status="not_requested")

        lexical_rows = self.repository.list_document_chunks(filters=filters, limit=max(limit * 6, 30))
        rows = lexical_rows
        vector_status = "disabled"
        if self.vector_search_enabled and self.query_embedder:
            try:
                embedding = self.query_embedder(query)
                vector_rows = self.repository.match_document_chunks(
                    query_embedding=embedding,
                    filters=filters,
                    threshold=float(os.getenv("MF_RESEARCH_VECTOR_MATCH_THRESHOLD", "0.2")),
                    limit=max(limit * 6, 30),
                )
                rows = self._merge_rows(vector_rows, lexical_rows)
                vector_status = "active"
            except Exception:
                rows = lexical_rows
                vector_status = "fallback_lexical"

        query_tokens = _tokens(query)
        meaningful_tokens = _meaningful_query_tokens(query)
        corpus_tokens = set().union(*(_tokens(str(row.get("chunk_text") or "")) for row in lexical_rows)) if lexical_rows else set()
        query_coverage = len(meaningful_tokens & corpus_tokens) / max(1, len(meaningful_tokens))
        if self.relevance_gate_enabled and meaningful_tokens and query_coverage < self.minimum_query_coverage:
            return self._empty_result(query_coverage=query_coverage, vector_status=vector_status)

        scored = []
        for row in rows:
            chunk_text = str(row.get("chunk_text") or "")
            lexical = len(query_tokens & _tokens(chunk_text)) / max(1, len(query_tokens))
            vector = float(row.get("similarity") or 0.0)
            if self.reranker_enabled:
                fuzzy = fuzz.token_set_ratio(query, chunk_text) / 100.0
                score = 0.55 * vector + 0.3 * lexical + 0.15 * fuzzy if vector else 0.7 * lexical + 0.3 * fuzzy
            else:
                score = 0.65 * vector + 0.35 * lexical
            score = round(score, 5)
            if score <= 0:
                continue
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            scored.append((score, row, metadata))
        scored.sort(key=lambda item: (-item[0], str(item[1].get("id") or "")))
        sources = [
            {
                "document_id": str(row.get("document_id") or ""),
                "chunk_id": str(row.get("id") or ""),
                "source_url": metadata.get("source_url"),
                "amc_code": metadata.get("amc_code"),
                "document_type": metadata.get("document_type"),
                "report_month": metadata.get("report_month"),
                "page": metadata.get("page"),
                "score": score,
                "excerpt": str(row.get("chunk_text") or "")[:400],
            }
            for score, row, metadata in scored[: max(1, min(limit, 10))]
        ]
        return {
            "retrieval_version": self.retrieval_version,
            "reranker_version": "rapidfuzz_token_set_v1" if self.reranker_enabled else None,
            "retrieval_mode": "hybrid" if vector_status == "active" else "lexical",
            "vector_status": vector_status,
            "query_coverage": round(query_coverage, 4),
            "grounded": bool(sources),
            "abstain": not bool(sources),
            "sources": sources,
            "context": "\n\n".join(f"[Source {index + 1}] {item['excerpt']}" for index, item in enumerate(sources)),
        }

    def _empty_result(self, *, query_coverage: float, vector_status: str) -> dict[str, Any]:
        return {
            "retrieval_version": self.retrieval_version,
            "reranker_version": "rapidfuzz_token_set_v1" if self.reranker_enabled else None,
            "retrieval_mode": "hybrid" if vector_status == "active" else "lexical",
            "vector_status": vector_status,
            "query_coverage": round(query_coverage, 4),
            "grounded": False,
            "abstain": True,
            "sources": [],
            "context": "",
        }

    @staticmethod
    def _merge_rows(primary: list[dict[str, Any]], secondary: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[str, dict[str, Any]] = {}
        for row in [*primary, *secondary]:
            key = str(row.get("id") or row.get("document_id") or chunk_hash(str(row.get("chunk_text") or "")))
            if key in merged and merged[key].get("similarity") is not None:
                continue
            merged[key] = row
        return list(merged.values())


def evaluate_retrieval(cases: list[dict[str, Any]], search: Any, *, limit: int = 5) -> dict[str, Any]:
    """Offline, provider-free retrieval metrics for a versioned golden set."""
    totals = Counter()
    case_results: list[dict[str, Any]] = []
    retrieval_versions: set[str] = set()
    recall_sum = 0.0
    reciprocal_rank_sum = 0.0
    for case in cases:
        result = search(str(case.get("query") or ""), filters=case.get("filters") or {}, limit=limit)
        retrieval_versions.add(str(result.get("retrieval_version") or RETRIEVAL_VERSION))
        ranked_ids = [str(item.get("document_id") or "") for item in result.get("sources", [])]
        expected = {str(value) for value in case.get("expected_document_ids") or [] if value not in (None, "")}
        retrieved = set(ranked_ids)
        matched = expected & retrieved
        expects_abstention = bool(case.get("expected_abstain", not expected))
        totals["cases"] += 1
        totals["grounded"] += int(bool(result.get("grounded")))
        if expected:
            totals["retrieval_cases"] += 1
            case_recall = len(matched) / len(expected)
            recall_sum += case_recall
            totals["hits"] += int(bool(matched))
            totals["all_relevant"] += int(matched == expected)
            first_rank = next((index for index, document_id in enumerate(ranked_ids, start=1) if document_id in expected), None)
            reciprocal_rank = 1.0 / first_rank if first_rank else 0.0
            reciprocal_rank_sum += reciprocal_rank
        else:
            case_recall = None
            reciprocal_rank = None
        if expects_abstention:
            totals["abstention_cases"] += 1
            totals["abstention_correct"] += int(bool(result.get("abstain")))
        case_results.append(
            {
                "case_id": str(case.get("id") or ""),
                "expected_document_ids": sorted(expected),
                "retrieved_document_ids": ranked_ids,
                "matched_document_ids": sorted(matched),
                "expected_abstain": expects_abstention,
                "actual_abstain": bool(result.get("abstain")),
                "recall_at_k": round(case_recall, 4) if case_recall is not None else None,
                "reciprocal_rank": round(reciprocal_rank, 4) if reciprocal_rank is not None else None,
                "passed": bool(result.get("abstain")) if expects_abstention else matched == expected,
            }
        )
    case_count = max(1, totals["cases"])
    retrieval_count = totals["retrieval_cases"]
    abstention_count = totals["abstention_cases"]
    return {
        "retrieval_version": sorted(retrieval_versions)[0] if len(retrieval_versions) == 1 else "mixed",
        "cases": totals["cases"],
        "retrieval_cases": retrieval_count,
        "abstention_cases": abstention_count,
        "recall_at_k": round(recall_sum / retrieval_count, 4) if retrieval_count else None,
        "hit_rate_at_k": round(totals["hits"] / retrieval_count, 4) if retrieval_count else None,
        "all_relevant_rate_at_k": round(totals["all_relevant"] / retrieval_count, 4) if retrieval_count else None,
        "mean_reciprocal_rank": round(reciprocal_rank_sum / retrieval_count, 4) if retrieval_count else None,
        "grounded_answer_rate": round(totals["grounded"] / case_count, 4),
        "abstention_accuracy": round(totals["abstention_correct"] / abstention_count, 4) if abstention_count else None,
        "passed_cases": sum(bool(item["passed"]) for item in case_results),
        "case_results": case_results,
    }
