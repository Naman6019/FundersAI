from app.services.document_indexing_service import DocumentIndexingService
from app.services.document_retrieval_service import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL


class _Response:
    def __init__(self, count):
        self.count = count

    def raise_for_status(self):
        return None

    def json(self):
        return {"data": [{"embedding": [0.0] * EMBEDDING_DIMENSIONS} for _ in range(self.count)]}


class _Repository:
    def __init__(self):
        self.rows = []

    def upsert_document_chunks(self, rows):
        self.rows.extend(rows)


def test_indexes_official_parsed_document_with_openrouter(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return _Response(len(kwargs["json"]["input"]))

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("OPENROUTER_HTTP_REFERER", "https://funders.ai")
    repository = _Repository()
    indexed = DocumentIndexingService(repository, http_post=fake_post).index(
        {"id": "document-1", "parse_status": "parsed", "source_url": "https://amc.example/factsheet.pdf", "amc_code": "axis", "document_type": "factsheet"},
        "Official factsheet content.",
    )

    assert indexed == 1
    assert captured["url"] == "https://openrouter.ai/api/v1/embeddings"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["headers"]["HTTP-Referer"] == "https://funders.ai"
    assert captured["json"] == {"model": EMBEDDING_MODEL, "input": ["Official factsheet content."], "dimensions": EMBEDDING_DIMENSIONS}
    assert repository.rows[0]["embedding_model"] == EMBEDDING_MODEL


def test_requires_openrouter_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    try:
        DocumentIndexingService(_Repository())._embed(["official content"])
    except RuntimeError as exc:
        assert str(exc) == "openrouter_api_key_missing_for_document_embeddings"
    else:
        raise AssertionError("expected an OpenRouter key error")
