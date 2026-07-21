from __future__ import annotations

import logging
import os
import re
import time
import uuid
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from app.services.document_retrieval_service import EMBEDDING_MODEL
from app.services.research_quality_service import OfficialEvidenceRelevanceGrader, validate_claim_citations

WORKFLOW_VERSION = "fund_research_graph_v3"
ABSTENTION_MESSAGE = "I could not find enough matching official-document evidence to answer this question."
logger = logging.getLogger(__name__)


def _clean_evidence_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip(" …")


def _extract_readable_claims(query: str, sources: list[dict[str, Any]]) -> list[str]:
    requested = query.casefold()
    claims: list[str] = []
    found: set[str] = set()

    asks_for_expense_ratio_location = "expense ratio" in requested and any(
        marker in requested for marker in ("section", "where", "lists", "listed", "location")
    )
    if asks_for_expense_ratio_location:
        heading_pattern = re.compile(
            r"\b(Base\s+Expense\s+Ratio\s*\(As\s+on\s+last\s+business\s+day\s+of\s+the\s+month\s*\))",
            re.IGNORECASE,
        )
        website_note_pattern = re.compile(
            r"\bFor\s+Total\s+Expense\s+Ratio(?:\s+including\s+brokerage,?\s+transaction\s+costs?\s+and\s+statutory\s+levies)?\s+please\s+refer(?:\s+to)?\s+(?:our|the\s+fund)\s+website",
            re.IGNORECASE,
        )
        for source_index, source in enumerate(sources, start=1):
            text = _clean_evidence_text(source.get("excerpt"))
            match = heading_pattern.search(text)
            if not match:
                website_note = website_note_pattern.search(text)
                if not website_note:
                    continue
                claims.append(
                    "- The factsheet directs readers to the fund website for the Total Expense Ratio, "
                    f"including brokerage, transaction cost and statutory levies. [{source_index}]"
                )
                found.add("expense ratio")
                break
            heading = re.sub(r"\s+\)", ")", _clean_evidence_text(match.group(1)))
            claims.append(f'- The total expense ratio is listed under the "{heading}" section. [{source_index}]')
            found.add("expense ratio")
            break

    patterns: list[tuple[str, str, re.Pattern[str]]] = [
        (
            "investment objective",
            "Investment objective",
            re.compile(r"\b(To\s+(?:seek|generate|provide|invest|achieve)[^.]{20,320}\.)", re.IGNORECASE),
        ),
        (
            "benchmark",
            "Benchmark",
            re.compile(
                r"\bAMFI\s+Tier\s+I\s+Benchmark(?:\s+Index)?\s+(.{2,120}?)(?=\s+To\s|\s+Investment\s+Objective|\s+Type\s+of|\s+Date\s+of|[.;]|$)",
                re.IGNORECASE,
            ),
        ),
        (
            "riskometer",
            "Riskometer",
            re.compile(r"\bThe\s+risk\s+of\s+the\s+scheme\s+is\s+(.{3,80}?)(?=\s+RISKOMETER|[.;]|$)", re.IGNORECASE),
        ),
        (
            "expense ratio",
            "Expense ratio",
            re.compile(
                r"\b(?:Total\s+Expense\s+Ratio|Expense\s+Ratio|TER)\s*(?:is|:|-)?\s*([0-9]+(?:\.[0-9]+)?\s*(?:%|percent))",
                re.IGNORECASE,
            ),
        ),
    ]

    for source_index, source in enumerate(sources, start=1):
        text = _clean_evidence_text(source.get("excerpt"))
        for field, label, pattern in patterns:
            if field in found or field not in requested:
                continue
            match = pattern.search(text)
            if not match:
                continue
            value = _clean_evidence_text(match.group(1))
            if field == "riskometer":
                value = f"The risk of the scheme is {value.lower()}"
            claims.append(f"- {label}: {value} [{source_index}]")
            found.add(field)
    return claims


def _model_usage(result: dict[str, Any], retrieval: dict[str, Any]) -> list[dict[str, str]]:
    usage: list[dict[str, str]] = []
    vector_status = str(retrieval.get("vector_status") or "disabled")
    if vector_status == "active":
        usage.append(
            {
                "stage": "Semantic document search",
                "provider": "OpenAI",
                "model": EMBEDDING_MODEL,
                "purpose": "Converts the question into an embedding used to find semantically similar official-document chunks.",
                "status": "active",
            }
        )

    relevance_grade = result.get("relevance_grade") or {}
    grader_status = str(relevance_grade.get("model_status") or "deterministic")
    if grader_status == "active":
        usage.append(
            {
                "stage": "Evidence relevance check",
                "provider": "OpenRouter",
                "model": (os.getenv("MF_RESEARCH_GRADER_MODEL") or os.getenv("OPENROUTER_MODEL") or "configured model").strip(),
                "purpose": "Checks whether the retrieved official excerpts can answer the question.",
                "status": "active",
            }
        )
    else:
        usage.append(
            {
                "stage": "Evidence relevance check",
                "provider": "FundersAI",
                "model": str(relevance_grade.get("grader_version") or "deterministic coverage gate"),
                "purpose": "Checks query-term coverage without a generative model.",
                "status": grader_status,
            }
        )

    cross_encoder_status = str(retrieval.get("cross_encoder_status") or "disabled")
    if cross_encoder_status == "active":
        usage.append(
            {
                "stage": "Result reranking",
                "provider": "Cohere",
                "model": os.getenv("MF_RESEARCH_CROSS_ENCODER_MODEL", "rerank-v4.0-fast").strip(),
                "purpose": "Reranks retrieved official-document chunks by relevance.",
                "status": "active",
            }
        )

    usage.append(
        {
            "stage": "Cited answer construction",
            "provider": "FundersAI",
            "model": WORKFLOW_VERSION,
            "purpose": "Builds readable cited statements with deterministic rules; no generative answer model is used.",
            "status": "active",
        }
    )
    return usage


class FundResearchState(TypedDict, total=False):
    query: str
    original_query: str
    rewrite_count: int
    filters: dict[str, Any]
    limit: int
    retrieval: dict[str, Any]
    answer: str
    answer_format: str
    sources: list[dict[str, Any]]
    grounded: bool
    abstain: bool
    trace: list[str]
    trace_details: list[dict[str, Any]]
    relevance_grade: dict[str, Any]
    claim_validation: dict[str, Any]
    workflow_version: str


def build_fund_research_graph(retrieval_service: Any, relevance_grader: Any | None = None):
    grader = relevance_grader or OfficialEvidenceRelevanceGrader()

    def normalize_request(state: FundResearchState) -> FundResearchState:
        filters = {key: value for key, value in (state.get("filters") or {}).items() if value not in (None, "")}
        query = str(state.get("query") or "").strip()
        return {
            "query": query,
            "original_query": query,
            "rewrite_count": 0,
            "filters": filters,
            "limit": max(1, min(int(state.get("limit") or 5), 10)),
            "trace": ["normalize_request"],
            "trace_details": [{"node": "normalize_request", "status": "ok", "query": query}],
            "workflow_version": WORKFLOW_VERSION,
        }

    def retrieve_evidence(state: FundResearchState) -> FundResearchState:
        retrieval = retrieval_service.search(state["query"], filters=state["filters"], limit=state["limit"])
        return {
            "retrieval": retrieval,
            "trace": [*state["trace"], "retrieve_evidence"],
            "trace_details": [
                *state["trace_details"],
                {
                    "node": "retrieve_evidence",
                    "status": "ok" if retrieval.get("sources") else "limited",
                    "query": state["query"],
                    "source_count": len(retrieval.get("sources") or []),
                    "retrieval_version": retrieval.get("retrieval_version"),
                    "mode": retrieval.get("retrieval_mode"),
                },
            ],
        }

    def grade_retrieval(state: FundResearchState) -> FundResearchState:
        grade = grader.grade(
            state["query"],
            state["retrieval"],
            allow_rewrite=int(state.get("rewrite_count") or 0) < 1,
        )
        return {
            "relevance_grade": grade,
            "trace": [*state["trace"], "grade_retrieval"],
            "trace_details": [
                *state["trace_details"],
                {
                    "node": "grade_retrieval",
                    "status": "ok" if grade.get("relevant") else "limited",
                    "score": grade.get("score"),
                    "grader_version": grade.get("grader_version"),
                    "model_status": grade.get("model_status"),
                },
            ],
        }

    def route_after_grade(state: FundResearchState) -> str:
        grade = state.get("relevance_grade") or {}
        if grade.get("relevant") and state["retrieval"].get("sources"):
            return "synthesize"
        if int(state.get("rewrite_count") or 0) < 1 and str(grade.get("rewritten_query") or "").strip():
            return "rewrite"
        return "abstain"

    def rewrite_query(state: FundResearchState) -> FundResearchState:
        rewritten = str((state.get("relevance_grade") or {}).get("rewritten_query") or "").strip()
        return {
            "query": rewritten,
            "rewrite_count": 1,
            "trace": [*state["trace"], "rewrite_query"],
            "trace_details": [
                *state["trace_details"],
                {
                    "node": "rewrite_query",
                    "status": "ok",
                    "query": rewritten,
                    "scope": "official_document_corpus",
                },
            ],
        }

    def synthesize_from_evidence(state: FundResearchState) -> FundResearchState:
        sources = state["retrieval"].get("sources") or []
        claims = _extract_readable_claims(state["query"], sources)
        lines = ["Answer from official documents:"]
        lines.extend(claims or (f"- [{index}] {_clean_evidence_text(source.get('excerpt'))}" for index, source in enumerate(sources, start=1)))
        return {
            "answer": "\n".join(lines),
            "answer_format": "field_summary" if claims else "source_excerpts",
            "sources": sources,
            "grounded": True,
            "abstain": False,
            "trace": [*state["trace"], "synthesize_from_evidence"],
            "trace_details": [
                *state["trace_details"],
                {"node": "synthesize_from_evidence", "status": "ok", "claim_count": len(sources)},
            ],
        }

    def validate_citations(state: FundResearchState) -> FundResearchState:
        sources = state.get("sources") or []
        answer = state.get("answer") or ""
        cited_indexes = {int(value) for value in re.findall(r"\[(\d+)]", answer)}
        url_valid = bool(cited_indexes) and all(
            1 <= index <= len(sources)
            and str(sources[index - 1].get("source_url") or "").startswith("https://")
            for index in cited_indexes
        )
        validation = validate_claim_citations(answer, sources)
        valid = url_valid and bool(validation.get("valid"))
        if not valid:
            return {
                "answer": ABSTENTION_MESSAGE,
                "answer_format": "abstention",
                "sources": [],
                "grounded": False,
                "abstain": True,
                "claim_validation": validation,
                "trace": [*state["trace"], "validate_citations", "citation_validation_failed"],
                "trace_details": [
                    *state["trace_details"],
                    {
                        "node": "validate_citations",
                        "status": "failed",
                        "url_valid": url_valid,
                        "support_rate": validation.get("support_rate"),
                    },
                ],
            }
        return {
            "claim_validation": validation,
            "trace": [*state["trace"], "validate_citations"],
            "trace_details": [
                *state["trace_details"],
                {
                    "node": "validate_citations",
                    "status": "ok",
                    "support_rate": validation.get("support_rate"),
                    "supported_claims": validation.get("supported_claims"),
                },
            ],
        }

    def abstain(state: FundResearchState) -> FundResearchState:
        return {
            "answer": ABSTENTION_MESSAGE,
            "answer_format": "abstention",
            "sources": [],
            "grounded": False,
            "abstain": True,
            "trace": [*state["trace"], "abstain"],
            "trace_details": [
                *state["trace_details"],
                {"node": "abstain", "status": "safe", "reason": (state.get("relevance_grade") or {}).get("reason")},
            ],
        }

    graph = StateGraph(FundResearchState)
    graph.add_node("normalize_request", normalize_request)
    graph.add_node("retrieve_evidence", retrieve_evidence)
    graph.add_node("grade_retrieval", grade_retrieval)
    graph.add_node("rewrite_query", rewrite_query)
    graph.add_node("synthesize_from_evidence", synthesize_from_evidence)
    graph.add_node("validate_citations", validate_citations)
    graph.add_node("abstain", abstain)
    graph.add_edge(START, "normalize_request")
    graph.add_edge("normalize_request", "retrieve_evidence")
    graph.add_edge("retrieve_evidence", "grade_retrieval")
    graph.add_conditional_edges(
        "grade_retrieval",
        route_after_grade,
        {"synthesize": "synthesize_from_evidence", "rewrite": "rewrite_query", "abstain": "abstain"},
    )
    graph.add_edge("rewrite_query", "retrieve_evidence")
    graph.add_edge("synthesize_from_evidence", "validate_citations")
    graph.add_edge("validate_citations", END)
    graph.add_edge("abstain", END)
    return graph.compile()


def run_fund_research_workflow(
    retrieval_service: Any,
    *,
    query: str,
    filters: dict[str, Any] | None = None,
    limit: int = 5,
    relevance_grader: Any | None = None,
) -> dict[str, Any]:
    started_at = time.perf_counter()
    run_id = uuid.uuid4().hex
    try:
        graph = build_fund_research_graph(retrieval_service, relevance_grader=relevance_grader)
        payload = {"query": query, "filters": filters or {}, "limit": limit}
        tracing_enabled = os.getenv("MF_RESEARCH_LANGFUSE_TRACING_ENABLED", "false").strip().lower() in {"1", "true", "yes", "on"}
        if tracing_enabled and os.getenv("LANGFUSE_PUBLIC_KEY", "").strip() and os.getenv("LANGFUSE_SECRET_KEY", "").strip():
            from langfuse import get_client

            langfuse = get_client()
            with langfuse.start_as_current_observation(
                name="fund_research_workflow",
                as_type="chain",
                input=payload,
                version=WORKFLOW_VERSION,
            ) as span:
                result = graph.invoke(payload)
                langfuse.update_current_span(
                    output={"grounded": result.get("grounded"), "abstain": result.get("abstain"), "trace": result.get("trace")},
                    metadata={"retrieval_version": (result.get("retrieval") or {}).get("retrieval_version")},
                )
                langfuse.score_current_span(name="grounded", value=bool(result.get("grounded")), data_type="BOOLEAN")
                run_id = langfuse.get_current_trace_id() or run_id
                span.update()
        else:
            result = graph.invoke(payload)
    except Exception:
        logger.exception("event=fund_research_failed workflow_version=%s", WORKFLOW_VERSION)
        raise
    retrieval = result.get("retrieval") or {}
    response = {
        "workflow_version": result.get("workflow_version", WORKFLOW_VERSION),
        "trace_id": run_id,
        "retrieval_version": retrieval.get("retrieval_version"),
        "answer": result.get("answer", ABSTENTION_MESSAGE),
        "answer_format": result.get("answer_format", "abstention"),
        "grounded": bool(result.get("grounded")),
        "abstain": bool(result.get("abstain", True)),
        "sources": result.get("sources") or [],
        "trace": result.get("trace") or [],
        "trace_details": result.get("trace_details") or [],
        "original_query": result.get("original_query", query),
        "resolved_query": result.get("query", query),
        "rewrite_count": int(result.get("rewrite_count") or 0),
        "relevance_grade": result.get("relevance_grade") or {},
        "claim_validation": result.get("claim_validation") or {},
        "model_usage": _model_usage(result, retrieval),
        "retrieval": {
            "mode": retrieval.get("retrieval_mode"),
            "vector_status": retrieval.get("vector_status"),
            "cross_encoder_status": retrieval.get("cross_encoder_status"),
            "corpus_status": retrieval.get("corpus_status"),
            "reranker_version": retrieval.get("reranker_version"),
            "query_coverage": retrieval.get("query_coverage"),
        },
    }
    logger.info(
        "event=fund_research_completed workflow_version=%s retrieval_version=%s grounded=%s abstain=%s "
        "vector_status=%s source_count=%s rewrite_count=%s latency_ms=%s",
        WORKFLOW_VERSION,
        retrieval.get("retrieval_version"),
        str(response["grounded"]).lower(),
        str(response["abstain"]).lower(),
        retrieval.get("vector_status"),
        len(response["sources"]),
        response["rewrite_count"],
        round((time.perf_counter() - started_at) * 1000, 2),
    )
    return response
