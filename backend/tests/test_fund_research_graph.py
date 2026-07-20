from app.workflows.fund_research_graph import ABSTENTION_MESSAGE, run_fund_research_workflow


class _RetrievalService:
    def __init__(self, *, grounded: bool):
        self.grounded = grounded

    def search(self, query, *, filters, limit):
        sources = [{
            "document_id": "doc-1",
            "source_url": "https://official.example/factsheet.pdf",
            "excerpt": "The factsheet states the total expense ratio is 0.45 percent.",
        }] if self.grounded else []
        return {
            "retrieval_version": "test_retrieval_v1",
            "retrieval_mode": "lexical",
            "vector_status": "disabled",
            "query_coverage": 1.0 if sources else 0.0,
            "grounded": bool(sources),
            "abstain": not bool(sources),
            "sources": sources,
        }


def test_workflow_returns_only_cited_evidence() -> None:
    result = run_fund_research_workflow(_RetrievalService(grounded=True), query="expense ratio")

    assert result["grounded"] is True
    assert result["abstain"] is False
    assert "[1]" in result["answer"]
    assert result["sources"][0]["source_url"].startswith("https://")
    assert result["trace"] == [
        "normalize_request",
        "retrieve_evidence",
        "synthesize_from_evidence",
        "validate_citations",
    ]


def test_workflow_abstains_when_retrieval_has_no_evidence() -> None:
    result = run_fund_research_workflow(_RetrievalService(grounded=False), query="unanswerable")

    assert result["grounded"] is False
    assert result["abstain"] is True
    assert result["answer"] == ABSTENTION_MESSAGE
    assert result["sources"] == []
    assert result["trace"][-1] == "abstain"
