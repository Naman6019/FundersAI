import asyncio

from app.services import chat_service
from app.services.chat_service import (
    ChatRequest,
    _build_nav_lag_details,
    _build_official_research_chat_response,
    _build_response_as_of,
    _is_official_fund_research_query,
    _official_research_query,
)


def test_visible_official_evidence_action_maps_to_bounded_research_path():
    prompt = "Find official-document evidence for: What benchmark does HDFC Flexi Cap use?"

    assert _is_official_fund_research_query(prompt, "auto") is True
    assert _official_research_query(prompt) == "What benchmark does HDFC Flexi Cap use?"
    assert _is_official_fund_research_query("Explain diversification", "mutual_fund") is False


def test_official_research_response_carries_claim_sources_and_as_of_metadata():
    result = {
        "answer": "Answer from official documents:\n- The benchmark is NIFTY 500 TRI. [1]",
        "grounded": True,
        "abstain": False,
        "trace_id": "retrieval-trace",
        "sources": [
            {
                "source_url": "https://official.example/factsheet.pdf",
                "amc_code": "hdfc",
                "document_type": "factsheet",
                "report_month": "2026-07-01",
            }
        ],
        "claim_validation": {"valid": True, "claim_count": 1, "supported_claims": 1},
    }

    response = _build_official_research_chat_response("What is the benchmark?", result)

    assert response["answer_mode"] == "official_fund_research"
    assert response["sources"] == result["sources"]
    assert response["claim_validation"]["valid"] is True
    assert response["as_of"] == {
        "label": "Official AMC documents",
        "date": "2026-07-01",
        "source": "hdfc",
        "entity_dates": {},
        "source_count": 1,
    }


def test_nav_lag_details_and_as_of_are_derived_from_answer_metadata():
    freshness = {
        "Fund A": {
            "source": "FundersAI DB",
            "status": "lagging",
            "nav_date": "2026-07-24",
            "expected_nav_date": "2026-07-27",
            "missed_business_days": 1,
        }
    }
    quality = {"Fund A": {"missing_fields": ["expense_ratio"]}}

    lag = _build_nav_lag_details(freshness, quality)
    as_of = _build_response_as_of(freshness)

    assert lag["has_lag"] is True
    assert lag["refresh_scope"] == "read_only_data_health"
    assert lag["items"][0]["missing_fields"] == ["expense_ratio"]
    assert as_of["date"] == "2026-07-24"
    assert as_of["source"] == "FundersAI DB"


def test_chat_official_evidence_request_uses_grounded_citation_workflow(monkeypatch):
    source = {
        "source_url": "https://official.example/factsheet.pdf",
        "amc_code": "hdfc",
        "report_month": "2026-07-01",
    }
    monkeypatch.setattr(
        chat_service,
        "run_fund_research_workflow",
        lambda *_args, **_kwargs: {
            "answer": "Answer from official documents:\n- The benchmark is NIFTY 500 TRI. [1]",
            "grounded": True,
            "abstain": False,
            "sources": [source],
            "claim_validation": {"valid": True, "claim_count": 1, "supported_claims": 1},
        },
    )

    response = asyncio.run(chat_service.chat_endpoint(ChatRequest(
        query="Find official-document evidence for: What is the HDFC Flexi Cap benchmark?",
        asset_type="mutual_fund",
    )))

    assert response["answer_mode"] == "official_fund_research"
    assert response["sources"] == [source]
    assert response["claim_validation"]["valid"] is True
