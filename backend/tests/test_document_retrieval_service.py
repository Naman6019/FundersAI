from app.services.document_retrieval_service import DocumentRetrievalService, chunk_document_text, evaluate_retrieval


class _Repository:
    def list_document_chunks(self, *, filters, limit):
        return [
            {"id": "chunk-1", "document_id": "doc-1", "chunk_text": "The official factsheet states expense ratio is 0.45 percent.", "metadata": {"source_url": "https://official.example/factsheet.pdf", **filters}},
            {"id": "chunk-2", "document_id": "doc-2", "chunk_text": "Monthly portfolio disclosure lists holdings.", "metadata": {"source_url": "https://official.example/portfolio.pdf", **filters}},
        ]


class _VectorRepository(_Repository):
    def match_document_chunks(self, *, query_embedding, filters, threshold, limit):
        assert query_embedding == [0.1, 0.2]
        assert threshold == 0.2
        return [{
            "id": "chunk-vector",
            "document_id": "doc-vector",
            "chunk_text": "The official factsheet states expense ratio is 0.40 percent.",
            "similarity": 0.91,
            "metadata": {"source_url": "https://official.example/vector.pdf", **filters},
        }]


def test_retrieval_returns_citable_official_sources_and_abstains_without_matches():
    service = DocumentRetrievalService(_Repository())
    result = service.search("official factsheet expense ratio", filters={"document_type": "factsheet"})
    assert result["grounded"] is True
    assert result["sources"][0]["source_url"].startswith("https://official.example")
    assert DocumentRetrievalService(_Repository()).search("", filters={})["abstain"] is True


def test_chunking_and_evaluation_are_deterministic():
    assert len(chunk_document_text("x" * 1600)) >= 2
    service = DocumentRetrievalService(_Repository())
    report = evaluate_retrieval([{"query": "factsheet expense ratio", "expected_document_ids": ["doc-1"]}], service.search)
    assert report["recall_at_k"] == 1.0


def test_opt_in_vector_search_reports_hybrid_mode():
    service = DocumentRetrievalService(
        _VectorRepository(),
        vector_search_enabled=True,
        query_embedder=lambda _query: [0.1, 0.2],
    )

    result = service.search("official factsheet expense ratio", filters={"document_type": "factsheet"})

    assert result["retrieval_mode"] == "hybrid"
    assert result["vector_status"] == "active"
    assert "doc-vector" in {source["document_id"] for source in result["sources"]}


def test_vector_failure_falls_back_to_lexical_search():
    def fail_embedding(_query):
        raise RuntimeError("provider unavailable")

    service = DocumentRetrievalService(
        _VectorRepository(),
        vector_search_enabled=True,
        query_embedder=fail_embedding,
    )
    result = service.search("official factsheet expense ratio", filters={"document_type": "factsheet"})

    assert result["grounded"] is True
    assert result["retrieval_mode"] == "lexical"
    assert result["vector_status"] == "fallback_lexical"
