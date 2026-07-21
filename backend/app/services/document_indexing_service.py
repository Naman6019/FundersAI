from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import requests

from app.services.document_retrieval_service import (
    EMBEDDING_DIMENSIONS,
    EMBEDDING_MODEL,
    EMBEDDING_VERSION,
    chunk_document_text,
    chunk_hash,
)

logger = logging.getLogger(__name__)


class DocumentIndexingService:
    """Indexes only parsed official documents from an explicit background job."""

    def __init__(
        self,
        repository: Any,
        *,
        http_post=requests.post,
        require_embeddings: bool = False,
        embeddings_enabled: bool | None = None,
    ):
        self.repository = repository
        self.http_post = http_post
        self.require_embeddings = require_embeddings
        configured_embeddings = (
            os.getenv("MF_RESEARCH_INDEX_EMBEDDINGS_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
            if embeddings_enabled is None
            else embeddings_enabled
        )
        self.embeddings_enabled = require_embeddings or configured_embeddings
        self.last_index_mode = "not_run"

    def index(self, document: dict[str, Any], text: str) -> int:
        if str(document.get("parse_status") or "").lower() not in {"parsed", "parsed_partial"}:
            return 0
        source_url = str(document.get("source_url") or "")
        if not source_url.startswith("https://"):
            return 0
        chunks = list(dict.fromkeys(chunk_document_text(text)))
        if not chunks:
            return 0
        embeddings = self._embed_with_lexical_fallback(chunks)
        rows = []
        for index, (chunk, embedding) in enumerate(zip(chunks, embeddings), start=1):
            row = {
                "document_id": document["id"],
                "chunk_text": chunk,
                "chunk_hash": chunk_hash(chunk),
                "parser_version": document.get("parser_version"),
                "source_url": source_url,
                "metadata": {
                    "amc_code": str(document.get("amc_code") or "").strip().lower(),
                    "document_type": str(document.get("document_type") or document.get("source_document_type") or "").strip().lower(),
                    "report_month": document.get("report_month"),
                    "source_url": source_url,
                    "chunk_number": index,
                    "index_mode": self.last_index_mode,
                    "indexed_at": datetime.now(timezone.utc).isoformat(),
                },
            }
            if embedding is not None:
                row.update(
                    {
                        "embedding": embedding,
                        "embedding_model": EMBEDDING_MODEL,
                        "embedding_version": EMBEDDING_VERSION,
                    }
                )
            rows.append(row)
        self.repository.upsert_document_chunks(rows)
        return len(rows)

    def embed_query(self, query: str) -> list[float]:
        values = self._embed([query])
        return values[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Explicit evaluation hook; production indexing should continue to call index()."""
        return self._embed(texts)

    def _embed_with_lexical_fallback(self, chunks: list[str]) -> list[list[float] | None]:
        if not self.embeddings_enabled:
            self.last_index_mode = "lexical"
            return [None] * len(chunks)
        try:
            embeddings = self._embed(chunks)
            self.last_index_mode = "vector"
            return embeddings
        except Exception as exc:
            if self.require_embeddings:
                raise
            response = getattr(exc, "response", None)
            logger.warning(
                "event=document_embedding_fallback mode=lexical exception_type=%s provider_status=%s exception=%r",
                type(exc).__name__,
                getattr(response, "status_code", None),
                exc,
            )
            self.last_index_mode = "lexical"
            return [None] * len(chunks)

    def _embed(self, chunks: list[str]) -> list[list[float]]:
        key = (os.getenv("OPENAI_API_KEY") or os.getenv("OPENAI_KEY") or "").strip()
        if not key:
            raise RuntimeError("openai_api_key_missing_for_document_embeddings")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        batch_size = max(1, min(int(os.getenv("OPENAI_EMBEDDING_BATCH_SIZE", "64")), 256))
        values: list[list[float]] = []
        for start in range(0, len(chunks), batch_size):
            batch = chunks[start : start + batch_size]
            response = self.http_post(
                os.getenv("OPENAI_EMBEDDINGS_URL", "https://api.openai.com/v1/embeddings"),
                headers=headers,
                json={
                    "model": EMBEDDING_MODEL,
                    "input": batch,
                    "dimensions": EMBEDDING_DIMENSIONS,
                    "encoding_format": "float",
                },
                timeout=60,
            )
            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                detail = str(getattr(response, "text", "") or "")[:500]
                raise RuntimeError(
                    f"openai_embedding_request_failed status={getattr(response, 'status_code', None)} detail={detail}"
                ) from exc
            batch_values = [item["embedding"] for item in response.json().get("data", [])]
            if len(batch_values) != len(batch):
                raise RuntimeError("unexpected_embedding_response")
            values.extend(batch_values)
        if len(values) != len(chunks) or any(len(value) != EMBEDDING_DIMENSIONS for value in values):
            raise RuntimeError("unexpected_embedding_response")
        return values
