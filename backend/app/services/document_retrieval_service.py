from __future__ import annotations

import hashlib
import re
from collections import Counter
from typing import Any

RETRIEVAL_VERSION = "amc_hybrid_retrieval_v1"
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


class DocumentRetrievalService:
    """Hybrid ranking over already embedded, official AMC document chunks."""

    def __init__(self, repository: Any):
        self.repository = repository

    def search(self, query: str, *, filters: dict[str, Any] | None = None, limit: int = 5) -> dict[str, Any]:
        filters = {key: value for key, value in (filters or {}).items() if value not in (None, "")}
        rows = self.repository.list_document_chunks(filters=filters, limit=max(limit * 6, 30))
        query_tokens = _tokens(query)
        scored = []
        for row in rows:
            lexical = len(query_tokens & _tokens(str(row.get("chunk_text") or ""))) / max(1, len(query_tokens))
            vector = float(row.get("similarity") or 0.0)
            score = round(0.65 * vector + 0.35 * lexical, 5)
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
            "retrieval_version": RETRIEVAL_VERSION,
            "grounded": bool(sources),
            "abstain": not bool(sources),
            "sources": sources,
            "context": "\n\n".join(f"[Source {index + 1}] {item['excerpt']}" for index, item in enumerate(sources)),
        }


def evaluate_retrieval(cases: list[dict[str, Any]], search: Any, *, limit: int = 5) -> dict[str, Any]:
    """Offline, provider-free retrieval metrics for a versioned golden set."""
    totals = Counter()
    for case in cases:
        result = search(str(case.get("query") or ""), filters=case.get("filters") or {}, limit=limit)
        ids = {item.get("document_id") for item in result.get("sources", [])}
        expected = set(case.get("expected_document_ids") or [])
        totals["cases"] += 1
        totals["grounded"] += int(bool(result.get("grounded")))
        totals["hits"] += int(bool(ids & expected))
        totals["abstention_correct"] += int(not expected and bool(result.get("abstain")))
    count = max(1, totals["cases"])
    return {
        "retrieval_version": RETRIEVAL_VERSION,
        "cases": totals["cases"],
        "recall_at_k": round(totals["hits"] / count, 4),
        "grounded_answer_rate": round(totals["grounded"] / count, 4),
        "abstention_accuracy": round(totals["abstention_correct"] / count, 4),
    }
