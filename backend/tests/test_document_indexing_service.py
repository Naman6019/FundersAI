from pathlib import Path
from types import SimpleNamespace

from app.mf_ingestion.jobs import index_parsed_documents
from app.services import document_indexing_service
from app.services.document_indexing_service import DocumentIndexingService
from app.services.document_retrieval_service import EMBEDDING_DIMENSIONS, EMBEDDING_MODEL, chunk_document_text


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


def test_indexes_official_parsed_document_with_openai(monkeypatch):
    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return _Response(len(kwargs["json"]["input"]))

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    repository = _Repository()
    indexed = DocumentIndexingService(repository, http_post=fake_post, embeddings_enabled=True).index(
        {"id": "document-1", "parse_status": "parsed", "source_url": "https://amc.example/factsheet.pdf", "amc_code": "axis", "document_type": "factsheet"},
        "Official factsheet content.",
    )

    assert indexed == 1
    assert captured["url"] == "https://api.openai.com/v1/embeddings"
    assert captured["headers"]["Authorization"] == "Bearer test-key"
    assert captured["json"] == {
        "model": EMBEDDING_MODEL,
        "input": ["Official factsheet content."],
        "dimensions": EMBEDDING_DIMENSIONS,
        "encoding_format": "float",
    }
    assert repository.rows[0]["embedding_model"] == EMBEDDING_MODEL
    assert repository.rows[0]["metadata"]["amc_code"] == "axis"
    assert repository.rows[0]["metadata"]["index_mode"] == "vector"


def test_indexes_lexical_chunks_when_embeddings_are_unavailable(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_KEY", raising=False)
    repository = _Repository()

    indexed = DocumentIndexingService(repository).index(
        {
            "id": "document-1",
            "parse_status": "parsed",
            "source_url": "https://amc.example/factsheet.pdf",
            "amc_code": "PPFAS",
            "document_type": "FACTSHEET",
        },
        "Investment objective, benchmark and riskometer details.",
    )

    assert indexed == 1
    assert repository.rows[0].get("embedding") is None
    assert repository.rows[0]["metadata"]["amc_code"] == "ppfas"
    assert repository.rows[0]["metadata"]["document_type"] == "factsheet"
    assert repository.rows[0]["metadata"]["index_mode"] == "lexical"


def test_indexes_validated_official_documents_not_reparsed_for_structured_data():
    for status in ("official_source_covered", "skipped_duplicate"):
        repository = _Repository()

        indexed = DocumentIndexingService(repository, embeddings_enabled=False).index(
            {
                "id": f"document-{status}",
                "parse_status": status,
                "source_url": "https://amc.example/factsheet.pdf",
            },
            "Official factsheet content.",
        )

        assert indexed == 1
        assert len(repository.rows) == 1


def test_rejects_documents_without_an_indexable_validation_status():
    repository = _Repository()

    indexed = DocumentIndexingService(repository, embeddings_enabled=False).index(
        {
            "id": "document-review",
            "parse_status": "needs_review",
            "source_url": "https://amc.example/factsheet.pdf",
        },
        "Unvalidated content.",
    )

    assert indexed == 0
    assert repository.rows == []


def test_required_embeddings_keep_provider_failure_strict(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_KEY", raising=False)

    try:
        DocumentIndexingService(_Repository(), require_embeddings=True).index(
            {
                "id": "document-1",
                "parse_status": "parsed",
                "source_url": "https://amc.example/factsheet.pdf",
            },
            "Official factsheet content.",
        )
    except RuntimeError as exc:
        assert str(exc) == "openai_api_key_missing_for_document_embeddings"
    else:
        raise AssertionError("expected strict embedding failure")


def test_requires_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_KEY", raising=False)
    try:
        DocumentIndexingService(_Repository())._embed(["official content"])
    except RuntimeError as exc:
        assert str(exc) == "openai_api_key_missing_for_document_embeddings"
    else:
        raise AssertionError("expected an OpenAI key error")


def test_accepts_existing_openai_key_alias(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("OPENAI_KEY", "legacy-test-key")

    def fake_post(_url, **kwargs):
        assert kwargs["headers"]["Authorization"] == "Bearer legacy-test-key"
        return _Response(len(kwargs["json"]["input"]))

    values = DocumentIndexingService(_Repository(), http_post=fake_post)._embed(["official content"])
    assert len(values[0]) == EMBEDDING_DIMENSIONS


def test_embeddings_are_requested_in_bounded_batches(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_EMBEDDING_BATCH_SIZE", "2")
    batch_sizes = []

    def fake_post(_url, **kwargs):
        batch_sizes.append(len(kwargs["json"]["input"]))
        return _Response(len(kwargs["json"]["input"]))

    values = DocumentIndexingService(_Repository(), http_post=fake_post)._embed(["a", "b", "c", "d", "e"])

    assert batch_sizes == [2, 2, 1]
    assert len(values) == 5


def test_indexing_removes_database_unsafe_controls_and_duplicate_chunks(monkeypatch):
    assert "\x00" not in chunk_document_text("Axis\x00 factsheet")[0]
    monkeypatch.setattr(document_indexing_service, "chunk_document_text", lambda _text: ["same chunk", "same chunk"])
    repository = _Repository()

    indexed = DocumentIndexingService(repository, embeddings_enabled=False).index(
        {"id": "document-1", "parse_status": "parsed", "source_url": "https://amc.example/factsheet.pdf"},
        "ignored",
    )

    assert indexed == 1
    assert len(repository.rows) == 1


def test_existing_document_ids_require_vectors_when_embeddings_are_strict(monkeypatch):
    class _Query:
        def __init__(self):
            self.vector_only = False

        def select(self, *_args):
            return self

        def in_(self, *_args):
            return self

        @property
        def not_(self):
            return self

        def is_(self, column, value):
            assert (column, value) == ("embedding", "null")
            self.vector_only = True
            return self

        def limit(self, _value):
            return self

        def execute(self):
            assert self.vector_only is True
            return SimpleNamespace(data=[{"document_id": "document-vector"}])

    query = _Query()
    monkeypatch.setattr(index_parsed_documents, "supabase", SimpleNamespace(table=lambda _name: query))

    existing = index_parsed_documents._existing_document_ids(
        [{"id": "document-vector"}, {"id": "document-lexical"}],
        require_embeddings=True,
    )

    assert existing == {"document-vector"}


def test_document_chunk_repair_migration_is_service_role_only():
    migration = Path("backend/migrations/20260721_harden_amc_document_chunks.sql").read_text(encoding="utf-8")

    assert "add column if not exists chunk_hash text" in migration
    assert "amc_document_chunks_document_hash_idx" in migration
    assert "revoke all on table public.amc_document_chunks from authenticated" in migration
    assert "grant select, insert, update, delete on table public.amc_document_chunks to service_role" in migration
