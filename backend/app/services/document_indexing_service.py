from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any

import requests

from app.services.document_retrieval_service import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    RETRIEVAL_VERSION,
    chunk_document_text,
    chunk_hash,
)


class DocumentIndexingService:
    """Indexes only parsed official documents from an explicit background job."""

    def __init__(self, repository: Any, *, http_post=requests.post):
        self.repository = repository
        self.http_post = http_post

    def index(self, document: dict[str, Any], text: str) -> int:
        if str(document.get("parse_status") or "").lower() not in {"parsed", "parsed_partial"}:
            return 0
        source_url = str(document.get("source_url") or "")
        if not source_url.startswith("https://"):
            return 0
        chunks = chunk_document_text(text)
        if not chunks:
            return 0
        embeddings = self._embed(chunks)
        rows = [{
            "document_id": document["id"], "chunk_text": chunk, "embedding": embedding,
            "chunk_hash": chunk_hash(chunk), "embedding_model": EMBEDDING_MODEL,
            "embedding_version": RETRIEVAL_VERSION, "parser_version": document.get("parser_version"), "source_url": source_url,
            "metadata": {"amc_code": document.get("amc_code"), "document_type": document.get("document_type") or document.get("source_document_type"), "report_month": document.get("report_month"), "source_url": source_url, "chunk_number": index, "indexed_at": datetime.now(timezone.utc).isoformat()},
        } for index, (chunk, embedding) in enumerate(zip(chunks, embeddings), start=1)]
        self.repository.upsert_document_chunks(rows)
        return len(rows)

    def _embed(self, chunks: list[str]) -> list[list[float]]:
        key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not key:
            raise RuntimeError("openrouter_api_key_missing_for_document_embeddings")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        referer = os.getenv("OPENROUTER_HTTP_REFERER", "").strip()
        title = os.getenv("OPENROUTER_APP_TITLE", "FundersAI").strip()
        if referer:
            headers["HTTP-Referer"] = referer
        if title:
            headers["X-Title"] = title
        response = self.http_post(
            os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/") + "/embeddings",
            headers=headers,
            json={"model": EMBEDDING_MODEL, "input": chunks, "dimensions": EMBEDDING_DIMENSIONS},
            timeout=60,
        )
        response.raise_for_status()
        values = [item["embedding"] for item in response.json().get("data", [])]
        if len(values) != len(chunks) or any(len(value) != EMBEDDING_DIMENSIONS for value in values):
            raise RuntimeError("unexpected_embedding_response")
        return values
