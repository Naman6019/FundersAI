from app.services.document_retrieval_service import DocumentRetrievalService, chunk_document_text, evaluate_retrieval


class _Repository:
    def list_document_chunks(self, *, filters, limit):
        return [
            {"id": "chunk-1", "document_id": "doc-1", "chunk_text": "The official factsheet states expense ratio is 0.45 percent.", "metadata": {"source_url": "https://official.example/factsheet.pdf", **filters}},
            {"id": "chunk-2", "document_id": "doc-2", "chunk_text": "Monthly portfolio disclosure lists holdings.", "metadata": {"source_url": "https://official.example/portfolio.pdf", **filters}},
        ]


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
