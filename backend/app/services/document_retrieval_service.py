from __future__ import annotations

import hashlib
import os
import re
from collections import Counter
from typing import Any

import requests
from rapidfuzz import fuzz

BASELINE_RETRIEVAL_VERSION = "amc_hybrid_retrieval_v1"
RETRIEVAL_VERSION = "amc_lexical_rerank_v2"
V3_RETRIEVAL_VERSION = "amc_hybrid_cross_encoder_v3"
EMBEDDING_VERSION = "amc_document_embedding_openai_v2"
EMBEDDING_MODEL = "text-embedding-3-small"
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


def _focused_excerpt(text: str, query_tokens: set[str], *, limit: int = 400) -> str:
    clean = str(text or "").strip()
    if len(clean) <= limit:
        return clean

    lowered = clean.lower()
    starts = {0}
    for token in query_tokens:
        starts.update(max(0, match.start() - 80) for match in re.finditer(rf"\b{re.escape(token)}\b", lowered))

    def window_score(start: int) -> tuple[int, int]:
        window_tokens = _tokens(clean[start : start + limit])
        return len(query_tokens & window_tokens), -start

    start = max(starts, key=window_score)
    if start:
        boundary = clean.rfind(" ", max(0, start - 40), start + 1)
        start = boundary + 1 if boundary >= 0 else start
    excerpt = clean[start : start + limit].strip()
    return f"{'…' if start else ''}{excerpt}{'…' if start + limit < len(clean) else ''}"


def _enabled(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _normalize_filters(filters: dict[str, Any]) -> dict[str, Any]:
    normalized = {key: value for key, value in filters.items() if value not in (None, "")}
    for key in ("amc_code", "document_type"):
        if key in normalized:
            normalized[key] = str(normalized[key]).strip().lower()
    return normalized


class CohereCrossEncoderReranker:
    """Managed cross-encoder adapter; callers must keep a deterministic fallback."""

    def __init__(self, *, http_post=requests.post):
        self.http_post = http_post
        self.model = os.getenv("MF_RESEARCH_CROSS_ENCODER_MODEL", "rerank-v4.0-fast").strip()

    def rerank(self, query: str, documents: list[str]) -> list[float]:
        key = os.getenv("COHERE_API_KEY", "").strip()
        if not key:
            raise RuntimeError("cohere_api_key_missing")
        response = self.http_post(
            os.getenv("COHERE_RERANK_URL", "https://api.cohere.com/v2/rerank"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={"model": self.model, "query": query, "documents": documents, "top_n": len(documents)},
            timeout=30,
        )
        response.raise_for_status()
        scores = [0.0] * len(documents)
        for item in response.json().get("results", []):
            index = int(item.get("index", -1))
            if 0 <= index < len(scores):
                scores[index] = float(item.get("relevance_score") or 0.0)
        return scores


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
        rank_fusion_enabled: bool = False,
        cross_encoder_reranker: Any = None,
    ):
        self.repository = repository
        self.retrieval_version = retrieval_version
        self.reranker_enabled = reranker_enabled
        self.relevance_gate_enabled = relevance_gate_enabled
        self.vector_search_enabled = vector_search_enabled
        self.query_embedder = query_embedder
        self.minimum_query_coverage = minimum_query_coverage
        self.rank_fusion_enabled = rank_fusion_enabled
        self.cross_encoder_reranker = cross_encoder_reranker

    @classmethod
    def configured(cls, repository: Any) -> "DocumentRetrievalService":
        vector_enabled = _enabled("MF_RESEARCH_VECTOR_SEARCH_ENABLED")
        v3_enabled = _enabled("MF_RESEARCH_RETRIEVAL_V3_ENABLED")
        query_embedder = None
        if vector_enabled:
            from app.services.document_indexing_service import DocumentIndexingService

            query_embedder = DocumentIndexingService(repository).embed_query
        cross_encoder = CohereCrossEncoderReranker() if v3_enabled and _enabled("MF_RESEARCH_CROSS_ENCODER_ENABLED") else None
        return cls(
            repository,
            retrieval_version=V3_RETRIEVAL_VERSION if v3_enabled else RETRIEVAL_VERSION,
            vector_search_enabled=vector_enabled,
            query_embedder=query_embedder,
            relevance_gate_enabled=True,
            rank_fusion_enabled=v3_enabled,
            cross_encoder_reranker=cross_encoder,
        )

    @classmethod
    def v3(
        cls,
        repository: Any,
        *,
        vector_search_enabled: bool = False,
        query_embedder: Any = None,
        cross_encoder_reranker: Any = None,
    ) -> "DocumentRetrievalService":
        return cls(
            repository,
            retrieval_version=V3_RETRIEVAL_VERSION,
            relevance_gate_enabled=True,
            vector_search_enabled=vector_search_enabled,
            query_embedder=query_embedder,
            rank_fusion_enabled=True,
            cross_encoder_reranker=cross_encoder_reranker,
        )

    @classmethod
    def lexical_baseline(cls, repository: Any) -> "DocumentRetrievalService":
        return cls(
            repository,
            retrieval_version=BASELINE_RETRIEVAL_VERSION,
            reranker_enabled=False,
            relevance_gate_enabled=False,
        )

    def search(self, query: str, *, filters: dict[str, Any] | None = None, limit: int = 5) -> dict[str, Any]:
        filters = _normalize_filters(filters or {})
        query = str(query or "").strip()
        if not query:
            return self._empty_result(query_coverage=0.0, vector_status="not_requested", corpus_status="not_checked")

        lexical_rows = self.repository.list_document_chunks(filters=filters, limit=max(limit * 40, 200))
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
            return self._empty_result(
                query_coverage=query_coverage,
                vector_status=vector_status,
                corpus_status="available" if lexical_rows else "empty",
            )

        scored, reranker_version, cross_encoder_status = self._score_rows(query, rows, query_tokens)
        scored.sort(key=lambda item: (-item[0], str(item[1].get("id") or "")))
        selected = self._select_diverse_rows(scored, meaningful_tokens, limit=max(1, min(limit, 10)))
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
                "excerpt": _focused_excerpt(str(row.get("chunk_text") or ""), meaningful_tokens),
            }
            for score, row, metadata in selected
        ]
        return {
            "retrieval_version": self.retrieval_version,
            "reranker_version": reranker_version,
            "retrieval_mode": "hybrid" if vector_status == "active" else ("sparse" if self.rank_fusion_enabled else "lexical"),
            "vector_status": vector_status,
            "cross_encoder_status": cross_encoder_status,
            "corpus_status": "available",
            "query_coverage": round(query_coverage, 4),
            "grounded": bool(sources),
            "abstain": not bool(sources),
            "sources": sources,
            "context": "\n\n".join(f"[Source {index + 1}] {item['excerpt']}" for index, item in enumerate(sources)),
        }

    def _empty_result(self, *, query_coverage: float, vector_status: str, corpus_status: str) -> dict[str, Any]:
        return {
            "retrieval_version": self.retrieval_version,
            "reranker_version": "rrf_fusion_v1" if self.rank_fusion_enabled else ("rapidfuzz_token_set_v1" if self.reranker_enabled else None),
            "retrieval_mode": "hybrid" if vector_status == "active" else ("sparse" if self.rank_fusion_enabled else "lexical"),
            "vector_status": vector_status,
            "cross_encoder_status": "not_run" if self.cross_encoder_reranker else "disabled",
            "corpus_status": corpus_status,
            "query_coverage": round(query_coverage, 4),
            "grounded": False,
            "abstain": True,
            "sources": [],
            "context": "",
        }

    def _score_rows(
        self,
        query: str,
        rows: list[dict[str, Any]],
        query_tokens: set[str],
    ) -> tuple[list[tuple[float, dict[str, Any], dict[str, Any]]], str | None, str]:
        if not self.rank_fusion_enabled:
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
                if score <= 0:
                    continue
                metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
                scored.append((round(score, 5), row, metadata))
            return scored, "rapidfuzz_token_set_v1" if self.reranker_enabled else None, "disabled"

        def row_key(row: dict[str, Any]) -> str:
            return str(row.get("id") or row.get("document_id") or chunk_hash(str(row.get("chunk_text") or "")))

        sparse_scores = {
            row_key(row): 0.7 * (len(query_tokens & _tokens(str(row.get("chunk_text") or ""))) / max(1, len(query_tokens)))
            + 0.3 * (fuzz.token_set_ratio(query, str(row.get("chunk_text") or "")) / 100.0)
            for row in rows
        }
        dense_scores = {row_key(row): float(row.get("similarity") or 0.0) for row in rows}
        sparse_rank = {
            key: index for index, (key, score) in enumerate(sorted(sparse_scores.items(), key=lambda item: (-item[1], item[0])), start=1) if score > 0
        }
        dense_rank = {
            key: index for index, (key, score) in enumerate(sorted(dense_scores.items(), key=lambda item: (-item[1], item[0])), start=1) if score > 0
        }
        fusion_scores: dict[str, float] = {}
        for row in rows:
            key = row_key(row)
            fusion_scores[key] = (1 / (60 + sparse_rank[key]) if key in sparse_rank else 0.0) + (
                1 / (60 + dense_rank[key]) if key in dense_rank else 0.0
            )
        maximum = max(fusion_scores.values(), default=0.0)
        if maximum:
            fusion_scores = {key: value / maximum for key, value in fusion_scores.items()}

        ordered = sorted(rows, key=lambda row: (-fusion_scores.get(row_key(row), 0.0), row_key(row)))
        cross_scores: dict[str, float] = {}
        cross_encoder_status = "disabled"
        reranker_version = "rrf_fusion_v1"
        if self.cross_encoder_reranker and ordered:
            candidates = ordered[:20]
            try:
                values = self.cross_encoder_reranker.rerank(query, [str(row.get("chunk_text") or "") for row in candidates])
                if len(values) != len(candidates):
                    raise ValueError("cross_encoder_result_length_mismatch")
                cross_scores = {row_key(row): max(0.0, min(float(score), 1.0)) for row, score in zip(candidates, values)}
                cross_encoder_status = "active"
                model = getattr(self.cross_encoder_reranker, "model", "cross_encoder")
                reranker_version = f"{model}_v1"
            except Exception:
                cross_encoder_status = "fallback_rrf"

        scored = []
        for row in rows:
            key = row_key(row)
            fusion = fusion_scores.get(key, 0.0)
            score = 0.35 * fusion + 0.65 * cross_scores[key] if key in cross_scores else fusion
            if score <= 0:
                continue
            metadata = row.get("metadata") if isinstance(row.get("metadata"), dict) else {}
            scored.append((round(score, 5), row, metadata))
        return scored, reranker_version, cross_encoder_status

    @staticmethod
    def _select_diverse_rows(
        scored: list[tuple[float, dict[str, Any], dict[str, Any]]],
        query_tokens: set[str],
        *,
        limit: int,
    ) -> list[tuple[float, dict[str, Any], dict[str, Any]]]:
        unique: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
        seen_chunks: set[str] = set()
        for item in scored:
            text = str(item[1].get("chunk_text") or "")
            fingerprint = chunk_hash(text)
            if fingerprint in seen_chunks:
                continue
            seen_chunks.add(fingerprint)
            unique.append(item)

        selected: list[tuple[float, dict[str, Any], dict[str, Any]]] = []
        remaining = list(unique)
        uncovered = set(query_tokens)
        while remaining and uncovered and len(selected) < limit:
            best_index = max(
                range(len(remaining)),
                key=lambda index: (
                    len(uncovered & _tokens(str(remaining[index][1].get("chunk_text") or ""))),
                    remaining[index][0],
                    -index,
                ),
            )
            best = remaining[best_index]
            covered = uncovered & _tokens(str(best[1].get("chunk_text") or ""))
            if not covered:
                break
            selected.append(remaining.pop(best_index))
            uncovered -= covered

        selected_fingerprints = {chunk_hash(str(item[1].get("chunk_text") or "")) for item in selected}
        for item in unique:
            fingerprint = chunk_hash(str(item[1].get("chunk_text") or ""))
            if fingerprint in selected_fingerprints:
                continue
            selected.append(item)
            selected_fingerprints.add(fingerprint)
            if len(selected) >= limit:
                break
        return selected[:limit]

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
