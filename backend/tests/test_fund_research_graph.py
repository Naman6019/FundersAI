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
        "grade_retrieval",
        "synthesize_from_evidence",
        "validate_citations",
    ]
    assert result["claim_validation"]["support_rate"] == 1.0
    assert result["trace_id"]
    assert result["model_usage"][-1]["stage"] == "Cited answer construction"
    assert "no generative answer model" in result["model_usage"][-1]["purpose"]


def test_workflow_turns_common_factsheet_fields_into_readable_cited_claims() -> None:
    class _FactsheetRetrievalService:
        def search(self, query, *, filters, limit):
            return {
                "retrieval_version": "test_retrieval_v1",
                "retrieval_mode": "hybrid",
                "vector_status": "active",
                "query_coverage": 1.0,
                "grounded": True,
                "abstain": False,
                "sources": [
                    {
                        "document_id": "doc-1",
                        "source_url": "https://official.example/factsheet.pdf",
                        "excerpt": (
                            "Investment Objective AMFI Tier I Benchmark Index NIFTY 500 (TRI) "
                            "To seek to generate long-term capital growth from an actively managed equity portfolio."
                        ),
                    },
                    {
                        "document_id": "doc-1",
                        "source_url": "https://official.example/factsheet.pdf",
                        "excerpt": "The risk of the scheme is very high risk RISKOMETER.",
                    },
                    {
                        "document_id": "doc-2",
                        "source_url": "https://official.example/unused.pdf",
                        "excerpt": "An unrelated but retrieved official excerpt.",
                    },
                ],
            }

    result = run_fund_research_workflow(
        _FactsheetRetrievalService(),
        query="Find the investment objective, benchmark, and riskometer in the factsheet.",
    )

    assert "Investment objective: To seek to generate long-term capital growth" in result["answer"]
    assert "Benchmark: NIFTY 500 (TRI)" in result["answer"]
    assert "Riskometer: The risk of the scheme is very high risk" in result["answer"]
    assert result["claim_validation"]["support_rate"] == 1.0
    assert result["grounded"] is True


def test_workflow_answers_expense_ratio_section_question_without_raw_excerpt_dump() -> None:
    class _ExpenseRatioRetrievalService:
        def search(self, query, *, filters, limit):
            return {
                "retrieval_version": "test_retrieval_v1",
                "retrieval_mode": "hybrid",
                "vector_status": "active",
                "cross_encoder_status": "disabled",
                "query_coverage": 1.0,
                "grounded": True,
                "abstain": False,
                "sources": [
                    {
                        "document_id": "doc-1",
                        "source_url": "https://official.example/factsheet.pdf",
                        "excerpt": (
                            "FACT SHEET - APRIL 2026 Base Expense Ratio "
                            "(As on last business day of the month) For TER, investors may refer to our website."
                        ),
                    }
                ],
            }

    result = run_fund_research_workflow(
        _ExpenseRatioRetrievalService(),
        query="Which official factsheet section lists the total expense ratio?",
    )

    assert result["answer"] == (
        'Answer from official documents:\n- The total expense ratio is listed under the '
        '"Base Expense Ratio (As on last business day of the month)" section. [1]'
    )
    assert result["answer_format"] == "field_summary"
    assert result["claim_validation"]["support_rate"] == 1.0
    assert "FACT SHEET - APRIL" not in result["answer"]
    assert result["model_usage"][0] == {
        "stage": "Semantic document search",
        "provider": "OpenAI",
        "model": "text-embedding-3-small",
        "purpose": "Converts the question into an embedding used to find semantically similar official-document chunks.",
        "status": "active",
    }


def test_workflow_answers_live_hdfc_expense_ratio_wording_without_ocr_dump() -> None:
    class _HdfcRetrievalService:
        def search(self, query, *, filters, limit):
            return {
                "retrieval_version": "amc_lexical_rerank_v2",
                "retrieval_mode": "hybrid",
                "vector_status": "active",
                "cross_encoder_status": "disabled",
                "query_coverage": 1.0,
                "grounded": True,
                "abstain": False,
                "sources": [
                    {
                        "document_id": "doc-1",
                        "source_url": "https://official.example/hdfc-factsheet.pdf",
                        "excerpt": "Total expense ratio (TER) means the ratio of total expenses charged to investors.",
                    },
                    {
                        "document_id": "doc-1",
                        "source_url": "https://official.example/hdfc-factsheet.pdf",
                        "excerpt": (
                            "For Total Expense Ratio including brokerage, transaction cost and statutory levies "
                            "please refer our website. Industry Allocation of Equity Holding of Net Assets."
                        ),
                    },
                ],
            }

    result = run_fund_research_workflow(
        _HdfcRetrievalService(),
        query="Which official factsheet section lists the total expense ratio?",
    )

    assert result["answer"] == (
        "Answer from official documents:\n- The factsheet directs readers to the fund website for the "
        "Total Expense Ratio, including brokerage, transaction cost and statutory levies. [2]"
    )
    assert result["answer_format"] == "field_summary"
    assert result["claim_validation"]["support_rate"] == 1.0
    assert "Industry Allocation" not in result["answer"]


def test_workflow_marks_unstructured_fallback_as_source_excerpts() -> None:
    class _UnstructuredRetrievalService:
        def search(self, query, *, filters, limit):
            return {
                "retrieval_version": "test_retrieval_v1",
                "retrieval_mode": "lexical",
                "vector_status": "disabled",
                "query_coverage": 1.0,
                "grounded": True,
                "abstain": False,
                "sources": [{
                    "document_id": "doc-1",
                    "source_url": "https://official.example/factsheet.pdf",
                    "excerpt": "A matching official passage that has no supported field extractor.",
                }],
            }

    result = run_fund_research_workflow(_UnstructuredRetrievalService(), query="Explain this passage")

    assert result["answer_format"] == "source_excerpts"
    assert result["grounded"] is True


def test_workflow_abstains_when_retrieval_has_no_evidence() -> None:
    result = run_fund_research_workflow(_RetrievalService(grounded=False), query="unanswerable")

    assert result["grounded"] is False
    assert result["abstain"] is True
    assert result["answer"] == ABSTENTION_MESSAGE
    assert result["sources"] == []
    assert result["trace"][-1] == "abstain"


class _RewriteRetrievalService:
    def __init__(self):
        self.queries = []

    def search(self, query, *, filters, limit):
        self.queries.append(query)
        sources = [{
            "document_id": "doc-1",
            "source_url": "https://official.example/factsheet.pdf",
            "excerpt": "The total expense ratio is listed in the official factsheet.",
        }] if query == "total expense ratio" else []
        return {
            "retrieval_version": "test_retrieval_v3",
            "retrieval_mode": "sparse",
            "vector_status": "disabled",
            "query_coverage": 1.0 if sources else 0.0,
            "grounded": bool(sources),
            "abstain": not bool(sources),
            "sources": sources,
        }


def test_workflow_rewrites_once_inside_official_corpus() -> None:
    service = _RewriteRetrievalService()
    result = run_fund_research_workflow(service, query="What is TER?")

    assert service.queries == ["What is TER?", "total expense ratio"]
    assert result["rewrite_count"] == 1
    assert result["resolved_query"] == "total expense ratio"
    assert result["grounded"] is True
    assert result["trace"].count("rewrite_query") == 1
