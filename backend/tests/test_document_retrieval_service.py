from app.services.document_retrieval_service import DocumentRetrievalService, chunk_document_text, evaluate_retrieval
from app.services.research_quality_service import validate_claim_citations


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


class _FilterRepository(_Repository):
    def __init__(self):
        self.filters = None
        self.limit = None

    def list_document_chunks(self, *, filters, limit):
        self.filters = filters
        self.limit = limit
        return super().list_document_chunks(filters=filters, limit=limit)


def test_retrieval_returns_citable_official_sources_and_abstains_without_matches():
    service = DocumentRetrievalService(_Repository())
    result = service.search("official factsheet expense ratio", filters={"document_type": "factsheet"})
    assert result["grounded"] is True
    assert result["sources"][0]["source_url"].startswith("https://official.example")
    assert DocumentRetrievalService(_Repository()).search("", filters={})["abstain"] is True


def test_retrieval_normalizes_amc_and_document_type_filters():
    repository = _FilterRepository()

    result = DocumentRetrievalService(repository).search(
        "official factsheet expense ratio",
        filters={"amc_code": "PPFAS", "document_type": "FACTSHEET"},
    )

    assert result["grounded"] is True
    assert repository.filters == {"amc_code": "ppfas", "document_type": "factsheet"}
    assert repository.limit == 200


def test_retrieval_covers_distinct_query_fields_and_focuses_excerpts():
    duplicate = {
        "id": "cover-duplicate",
        "document_id": "doc-duplicate",
        "chunk_text": "PPFAS index " + ("filler " * 80) + "Investment Objective and Benchmark details.",
        "metadata": {"source_url": "https://official.example/factsheet.pdf"},
    }

    class _CoverageRepository:
        def list_document_chunks(self, *, filters, limit):
            assert limit == 200
            return [
                {**duplicate, "id": "cover-1", "document_id": "doc-1"},
                duplicate,
                {
                    "id": "risk-1",
                    "document_id": "doc-1",
                    "chunk_text": "The scheme riskometer is very high risk and the benchmark riskometer is very high risk.",
                    "metadata": {"source_url": "https://official.example/factsheet.pdf"},
                },
            ]

    result = DocumentRetrievalService(_CoverageRepository()).search(
        "Find the investment objective, benchmark, and riskometer in the PPFAS factsheet.",
        filters={"amc_code": "ppfas"},
        limit=3,
    )

    assert len(result["sources"]) == 2
    assert any("riskometer" in source["excerpt"].lower() for source in result["sources"])
    assert any("investment objective" in source["excerpt"].lower() for source in result["sources"])


def test_empty_corpus_is_distinguished_from_irrelevant_evidence():
    class _EmptyRepository:
        def list_document_chunks(self, *, filters, limit):
            return []

    result = DocumentRetrievalService(_EmptyRepository()).search("official factsheet expense ratio", filters={})

    assert result["abstain"] is True
    assert result["corpus_status"] == "empty"


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


class _FakeCrossEncoder:
    model = "test-cross-encoder"

    def rerank(self, query, documents):
        assert query == "official factsheet expense ratio"
        return [0.95 if "0.45" in document else 0.1 for document in documents]


def test_v3_cross_encoder_is_feature_isolated_and_reported():
    service = DocumentRetrievalService.v3(_Repository(), cross_encoder_reranker=_FakeCrossEncoder())

    result = service.search("official factsheet expense ratio", filters={})

    assert result["retrieval_version"] == "amc_hybrid_cross_encoder_v3"
    assert result["cross_encoder_status"] == "active"
    assert result["reranker_version"] == "test-cross-encoder_v1"
    assert result["sources"][0]["document_id"] == "doc-1"


def test_v3_cross_encoder_failure_falls_back_to_rank_fusion():
    class _FailingCrossEncoder:
        model = "unavailable-cross-encoder"

        def rerank(self, query, documents):
            raise RuntimeError("provider unavailable")

    result = DocumentRetrievalService.v3(
        _Repository(),
        cross_encoder_reranker=_FailingCrossEncoder(),
    ).search("official factsheet expense ratio", filters={})

    assert result["grounded"] is True
    assert result["cross_encoder_status"] == "fallback_rrf"
    assert result["reranker_version"] == "rrf_fusion_v1"


def test_claim_validation_rejects_uncited_or_unsupported_claims():
    sources = [{"excerpt": "The official factsheet states expense ratio is 0.45 percent."}]

    valid = validate_claim_citations("- [1] The official factsheet states expense ratio is 0.45 percent.", sources)
    invalid = validate_claim_citations("- The expense ratio is guaranteed to remain low.", sources)

    assert valid["valid"] is True
    assert valid["support_rate"] == 1.0
    assert invalid["valid"] is False
    assert invalid["support_rate"] == 0.0
