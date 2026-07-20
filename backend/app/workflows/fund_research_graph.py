from __future__ import annotations

import logging
import time
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

WORKFLOW_VERSION = "fund_research_graph_v1"
ABSTENTION_MESSAGE = "I could not find enough matching official-document evidence to answer this question."
logger = logging.getLogger(__name__)


class FundResearchState(TypedDict, total=False):
    query: str
    filters: dict[str, Any]
    limit: int
    retrieval: dict[str, Any]
    answer: str
    sources: list[dict[str, Any]]
    grounded: bool
    abstain: bool
    trace: list[str]
    workflow_version: str


def build_fund_research_graph(retrieval_service: Any):
    def normalize_request(state: FundResearchState) -> FundResearchState:
        filters = {key: value for key, value in (state.get("filters") or {}).items() if value not in (None, "")}
        return {
            "query": str(state.get("query") or "").strip(),
            "filters": filters,
            "limit": max(1, min(int(state.get("limit") or 5), 10)),
            "trace": ["normalize_request"],
            "workflow_version": WORKFLOW_VERSION,
        }

    def retrieve_evidence(state: FundResearchState) -> FundResearchState:
        retrieval = retrieval_service.search(state["query"], filters=state["filters"], limit=state["limit"])
        return {"retrieval": retrieval, "trace": [*state["trace"], "retrieve_evidence"]}

    def route_after_retrieval(state: FundResearchState) -> str:
        return "abstain" if state["retrieval"].get("abstain") else "synthesize"

    def synthesize_from_evidence(state: FundResearchState) -> FundResearchState:
        sources = state["retrieval"].get("sources") or []
        lines = ["Official-document evidence:"]
        lines.extend(f"- [{index}] {source.get('excerpt', '')}" for index, source in enumerate(sources, start=1))
        return {
            "answer": "\n".join(lines),
            "sources": sources,
            "grounded": True,
            "abstain": False,
            "trace": [*state["trace"], "synthesize_from_evidence"],
        }

    def validate_citations(state: FundResearchState) -> FundResearchState:
        sources = state.get("sources") or []
        answer = state.get("answer") or ""
        valid = bool(sources) and all(
            str(source.get("source_url") or "").startswith("https://") and f"[{index}]" in answer
            for index, source in enumerate(sources, start=1)
        )
        if not valid:
            return {
                "answer": ABSTENTION_MESSAGE,
                "sources": [],
                "grounded": False,
                "abstain": True,
                "trace": [*state["trace"], "validate_citations", "citation_validation_failed"],
            }
        return {"trace": [*state["trace"], "validate_citations"]}

    def abstain(state: FundResearchState) -> FundResearchState:
        return {
            "answer": ABSTENTION_MESSAGE,
            "sources": [],
            "grounded": False,
            "abstain": True,
            "trace": [*state["trace"], "abstain"],
        }

    graph = StateGraph(FundResearchState)
    graph.add_node("normalize_request", normalize_request)
    graph.add_node("retrieve_evidence", retrieve_evidence)
    graph.add_node("synthesize_from_evidence", synthesize_from_evidence)
    graph.add_node("validate_citations", validate_citations)
    graph.add_node("abstain", abstain)
    graph.add_edge(START, "normalize_request")
    graph.add_edge("normalize_request", "retrieve_evidence")
    graph.add_conditional_edges(
        "retrieve_evidence",
        route_after_retrieval,
        {"synthesize": "synthesize_from_evidence", "abstain": "abstain"},
    )
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
) -> dict[str, Any]:
    started_at = time.perf_counter()
    try:
        result = build_fund_research_graph(retrieval_service).invoke(
            {"query": query, "filters": filters or {}, "limit": limit}
        )
    except Exception:
        logger.exception("event=fund_research_failed workflow_version=%s", WORKFLOW_VERSION)
        raise
    retrieval = result.get("retrieval") or {}
    response = {
        "workflow_version": result.get("workflow_version", WORKFLOW_VERSION),
        "retrieval_version": retrieval.get("retrieval_version"),
        "answer": result.get("answer", ABSTENTION_MESSAGE),
        "grounded": bool(result.get("grounded")),
        "abstain": bool(result.get("abstain", True)),
        "sources": result.get("sources") or [],
        "trace": result.get("trace") or [],
        "retrieval": {
            "mode": retrieval.get("retrieval_mode"),
            "vector_status": retrieval.get("vector_status"),
            "query_coverage": retrieval.get("query_coverage"),
        },
    }
    logger.info(
        "event=fund_research_completed workflow_version=%s retrieval_version=%s grounded=%s abstain=%s "
        "vector_status=%s source_count=%s latency_ms=%s",
        WORKFLOW_VERSION,
        retrieval.get("retrieval_version"),
        str(response["grounded"]).lower(),
        str(response["abstain"]).lower(),
        retrieval.get("vector_status"),
        len(response["sources"]),
        round((time.perf_counter() - started_at) * 1000, 2),
    )
    return response
