import asyncio
from datetime import datetime, timezone


def _headline(title: str, published: str, source: str = "Reuters", url: str = "https://www.reuters.com/example") -> dict:
    return {
        "title": title,
        "published": published,
        "source": source,
        "url": url,
    }


def test_market_evidence_marks_old_headlines_stale():
    from app.services.market_current_events_service import normalize_market_evidence

    evidence = normalize_market_evidence(
        [
            _headline("Fresh market update", "Wed, 15 Jul 2026 07:00:00 GMT"),
            _headline("Old market update", "Mon, 15 Jun 2026 07:00:00 GMT", url="https://www.reuters.com/old"),
        ],
        now=datetime(2026, 7, 15, 12, tzinfo=timezone.utc),
    )

    assert evidence[0]["freshness"] == "fresh"
    assert evidence[1]["freshness"] == "stale"
    assert evidence[1]["age_hours"] == 725.0


def test_market_context_status_depends_on_dates_not_headline_count():
    from app.services.market_current_events_service import market_context_status, normalize_market_evidence

    evidence = normalize_market_evidence(
        [
            _headline("Old update one", "Mon, 15 Jun 2026 07:00:00 GMT"),
            _headline("Old update two", "Wed, 29 Apr 2026 07:00:00 GMT", url="https://www.reuters.com/older"),
        ],
        now=datetime(2026, 7, 15, 12, tzinfo=timezone.utc),
    )

    assert market_context_status(evidence) == "stale"


def test_approved_market_sources_do_not_use_short_url_substrings():
    from app.services import chat_service as main

    assert main._is_approved_web_source("NSE", "https://news.google.com/rss/articles/example") is True
    assert main._is_approved_web_source("Unknown Blog", "https://example.com/sensex-rally") is False


def test_market_fallback_is_readable_and_does_not_expose_model_failure():
    from app.services.market_current_events_service import build_market_fallback, normalize_market_evidence

    evidence = normalize_market_evidence(
        [
            _headline("Ceasefire breached as fresh strikes raise tensions", "Wed, 15 Jul 2026 07:00:00 GMT"),
            _headline(
                "Indian shares edge higher as oil and foreign flows limit gains",
                "Wed, 15 Jul 2026 06:00:00 GMT",
                source="NSE",
                url="https://www.nseindia.com/market-data/example",
            ),
        ],
        now=datetime(2026, 7, 15, 12, tzinfo=timezone.utc),
    )

    answer = build_market_fallback(
        "Will the Indian market have a strong rally now as the war has ended?",
        evidence,
    )

    assert answer.startswith("### Probably not a strong, sustained rally yet")
    assert "durable end is not confirmed" in answer
    assert "what would strengthen the rally case" in answer.lower()
    assert "[Reuters](https://www.reuters.com/example)" in answer
    assert "synthesis step" not in answer
    assert "timeout" not in answer


def test_current_events_synthesis_enables_web_search_and_merges_citations(monkeypatch):
    from app.services import chat_service as main

    captured = {}

    async def fake_function_ollama_chat(*_args, **kwargs):
        captured.update(kwargs)
        kwargs["citation_collector"].append(
            {
                "title": "Indian shares edge higher",
                "source": "Reuters",
                "url": "https://www.reuters.com/markets/india/example",
                "published": None,
                "context_type": "openrouter_web_search",
            }
        )
        return "### Probably not a strong, sustained rally yet\n\nThe premise needs confirmation."

    monkeypatch.setattr(main, "function_ollama_chat", fake_function_ollama_chat)

    meta = {}
    answer = asyncio.run(
        main.synthesis_response(
            query="Will the Indian market have a strong rally now as the war has ended?",
            intent_info={"intent": "news", "ticker": None, "answer_mode": "market_current_events"},
            quant_data={},
            news_data=[_headline("Oil rises as ceasefire comes under pressure", "Wed, 15 Jul 2026 07:00:00 GMT")],
            response_meta=meta,
        )
    )

    assert answer.startswith("### Probably not")
    assert captured["enable_web_search"] is True
    assert meta["news_context_status"] == "current_web_search"
    assert any(source["url"].startswith("https://www.reuters.com/markets") for source in meta["sources"])


def test_openrouter_web_search_tool_and_citations_are_added(monkeypatch):
    from app.services import chat_service as main

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "model": "test-model",
                "choices": [
                    {
                        "message": {
                            "content": "Grounded answer",
                            "annotations": [
                                {
                                    "type": "url_citation",
                                    "url_citation": {
                                        "title": "Official FPI data",
                                        "url": "https://www.nsdl.co.in/fpi-data",
                                        "content": "Latest daily FPI data",
                                    },
                                }
                            ],
                        }
                    }
                ],
                "usage": {},
            }

    class FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            captured["timeout"] = kwargs.get("timeout")

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, _url, *, headers, json):
            captured["headers"] = headers
            captured["payload"] = json
            return FakeResponse()

    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setattr(main.httpx, "AsyncClient", FakeAsyncClient)
    citations = []

    answer = asyncio.run(
        main.function_ollama_chat(
            [{"role": "user", "content": "What is happening now?"}],
            format="text",
            enable_web_search=True,
            citation_collector=citations,
        )
    )

    assert answer == "Grounded answer"
    assert captured["payload"]["tools"][0]["type"] == "openrouter:web_search"
    assert captured["payload"]["tools"][0]["parameters"]["max_total_results"] == 12
    assert citations[0]["url"] == "https://www.nsdl.co.in/fpi-data"
