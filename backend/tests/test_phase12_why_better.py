import asyncio


def test_sanitize_research_text_removes_provider_reasoning():
    from app.services.chat_service import _sanitize_research_text

    answer = _sanitize_research_text("<think>private model trace</think>\n### Answer\nVerified summary")
    incomplete = _sanitize_research_text("<think>unfinished private model trace")

    assert answer == "### Answer\nVerified summary"
    assert incomplete == ""


def test_stock_why_better_shape():
    from app.services.comparison_reasoning import build_stock_why_better

    payload = {
        "TCS": {
            "fundamentals": {
                "pe": 22.0,
                "roe": 0.25,
                "profit_growth_3y": 15.0,
                "debt_to_equity": 0.1,
            },
            "source_summary": {"stale": False, "metadata": "stocks"},
            "data_quality": {"missing_fields": []},
        },
        "RELIANCE": {
            "fundamentals": {
                "pe": 28.0,
                "roe": 0.18,
                "profit_growth_3y": 10.0,
                "debt_to_equity": 0.3,
            },
            "source_summary": {"stale": False, "metadata": "stocks"},
            "data_quality": {"missing_fields": []},
        },
    }

    result = build_stock_why_better(payload)

    assert isinstance(result.get("winner"), dict)
    assert result["winner"]["status"] in {"winner", "tie", "insufficient_data"}
    assert "verdict_context" in result
    assert "factor_results" in result
    assert isinstance(result.get("confidence"), dict)
    assert "score" in result["confidence"]
    assert "label" in result["confidence"]


def test_mf_why_better_missing_holdings_blocked():
    from app.services.comparison_reasoning import build_mf_why_better

    payload = {
        "Fund A": {
            "return_3y": 12.0,
            "volatility_1y": 14.0,
            "expense_ratio": 1.1,
            "source_summary": {"stale": False, "metadata": "mutual_fund_core_snapshot"},
            "data_quality": {"missing_fields": []},
            "holdings": [],
        },
        "Fund B": {
            "return_3y": 10.0,
            "volatility_1y": 13.5,
            "expense_ratio": 0.9,
            "source_summary": {"stale": False, "metadata": "mutual_fund_core_snapshot"},
            "data_quality": {"missing_fields": []},
            "holdings": [],
        },
    }

    result = build_mf_why_better(payload)
    assert result["holdings_based_reasoning"]["status"] == "blocked"
    assert any("holdings" in msg.lower() for msg in result.get("data_limitations", []))
    assert isinstance(result.get("winner"), dict)


def test_stock_compare_response_additive_metadata(monkeypatch):
    from app.services import quant_service

    monkeypatch.setattr(quant_service, "resolve_stock_request", lambda symbol: symbol)
    monkeypatch.setattr(
        quant_service,
        "_comparison_item",
        lambda symbol: {
            "symbol": symbol,
            "name": symbol,
            "price": 100,
            "change_pct": 1.2,
            "pe_ratio": 20,
            "market_cap": 1000,
            "fundamentals": {
                "pe": 20,
                "roe": 0.2,
                "profit_growth_3y": 10,
                "debt_to_equity": 0.2,
            },
            "ratios": {},
            "financials": {"quarterly": [], "annual": []},
            "shareholding": {},
            "price_history": [],
            "data_quality": {"missing_fields": [], "message": "Complete"},
            "source_summary": {"stale": False, "metadata": "stocks"},
        },
    )

    response = quant_service.build_stock_compare("TCS,INFY")

    assert "comparison" in response
    assert "why_better" in response
    assert "source_freshness" in response
    assert "data_quality" in response
    assert "verdict_context" in response


def test_stock_compare_does_not_call_live_clients(monkeypatch):
    from app.services import quant_service

    # Fail hard if old live paths are called.
    monkeypatch.setattr(quant_service, "_resolve_indianapi_stock_symbol", lambda _entity: (_ for _ in ()).throw(AssertionError("live indianapi called")))
    monkeypatch.setattr(quant_service.YFinanceProvider, "get_price_history", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("live yfinance called")))

    monkeypatch.setattr(quant_service, "resolve_stock_request", lambda symbol: symbol)
    monkeypatch.setattr(
        quant_service,
        "_comparison_item",
        lambda symbol: {
            "symbol": symbol,
            "name": symbol,
            "price": 100,
            "change_pct": 1.0,
            "pe_ratio": 15,
            "market_cap": 1000,
            "fundamentals": {
                "pe": 15,
                "roe": 0.2,
                "profit_growth_3y": 8,
                "debt_to_equity": 0.3,
            },
            "ratios": {},
            "financials": {"quarterly": [], "annual": []},
            "shareholding": {},
            "price_history": [],
            "data_quality": {"missing_fields": [], "message": "Complete"},
            "source_summary": {"stale": False, "metadata": "stocks"},
        },
    )

    response = quant_service.build_stock_compare("TCS,INFY")
    assert response["available"] == ["TCS", "INFY"]


def test_chat_mf_compare_does_not_call_live_clients(monkeypatch):
    from app.services import chat_service as main

    class FakeResult:
        def __init__(self, data):
            self.data = data

    class FakeQuery:
        def __init__(self, table, db):
            self.table = table
            self.db = db
            self.filters = {}
            self._limit = None
            self._order = None

        def select(self, _fields):
            return self

        def eq(self, key, value):
            self.filters[key] = value
            return self

        def ilike(self, key, value):
            self.filters[key] = value.replace("%", "").lower()
            return self

        def order(self, key, desc=False):
            self._order = (key, desc)
            return self

        def limit(self, value):
            self._limit = value
            return self

        def execute(self):
            rows = list(self.db.get(self.table, []))
            if self.table in {"mutual_fund_core_snapshot", "mutual_funds"} and "scheme_name" in self.filters:
                needle = self.filters["scheme_name"]
                rows = [r for r in rows if needle in str(r.get("scheme_name", "")).lower()]
            if self.table == "mutual_fund_nav_history" and "scheme_code" in self.filters:
                code = str(self.filters["scheme_code"])
                rows = [r for r in rows if str(r.get("scheme_code")) == code]
            if self.table == "stock_prices_daily" and "symbol" in self.filters:
                rows = [r for r in rows if r.get("symbol") == self.filters["symbol"]]
            if self._order:
                key, desc = self._order
                rows = sorted(rows, key=lambda row: row.get(key), reverse=desc)
            if self._limit is not None:
                rows = rows[: self._limit]
            return FakeResult(rows)

    class FakeSupabase:
        def __init__(self, db):
            self.db = db

        def table(self, name):
            return FakeQuery(name, self.db)

    fake_db = {
        "mutual_fund_core_snapshot": [
            {
                "scheme_code": "1001",
                "scheme_name": "ICICI Alpha Fund",
                "nav": 120.5,
                "nav_date": "2026-05-10",
                "category": "Flexi Cap",
                "amc_name": "ICICI Prudential Mutual Fund",
                "expense_ratio": 1.2,
                "aum": 10000,
                "return_3y": 12.3,
                "volatility_1y": 13.0,
            },
            {
                "scheme_code": "1002",
                "scheme_name": "PPFAS Beta Fund",
                "nav": 98.7,
                "nav_date": "2026-05-10",
                "category": "Flexi Cap",
                "amc_name": "PPFAS Mutual Fund",
                "expense_ratio": 1.0,
                "aum": 8000,
                "return_3y": 10.4,
                "volatility_1y": 12.8,
            },
        ],
        "mutual_fund_nav_history": [
            {"scheme_code": "1001", "nav_date": "2026-05-10", "nav": 120.5},
            {"scheme_code": "1001", "nav_date": "2026-05-09", "nav": 120.0},
            {"scheme_code": "1002", "nav_date": "2026-05-10", "nav": 98.7},
            {"scheme_code": "1002", "nav_date": "2026-05-09", "nav": 98.2},
        ],
        "stock_prices_daily": [
            {"symbol": "NIFTY", "date": "2026-05-10", "close": 22000.0},
            {"symbol": "NIFTY", "date": "2026-05-09", "close": 21980.0},
        ],
    }

    async def fake_route_query(_query, _asset_type="auto"):
        return {"intent": "compare", "compare_entities": ["ICICI Alpha Fund", "PPFAS Beta Fund"], "ticker": None, "historical_period": "1mo", "sentiment_flag": False}

    async def fake_synthesis_response(*_args, **_kwargs):
        return "ok"

    main._current_mf_repository.set(FakeSupabase(fake_db))
    monkeypatch.setattr(main, "route_query", fake_route_query)
    monkeypatch.setattr(main, "synthesis_response", fake_synthesis_response)
    monkeypatch.setattr(main, "fetch_news", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("news fetch called")))
    monkeypatch.setattr(main, "analyze_news_sentiment", lambda news: news)
    monkeypatch.setattr(main, "mfapi_get_latest_nav", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("live mfapi called")))
    monkeypatch.setattr(main, "mfapi_get_nav_history", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("live mfapi called")))

    class FailTicker:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("live yfinance called")

    monkeypatch.setattr(main.yf, "Ticker", FailTicker)

    req = main.ChatRequest(query="Compare ICICI Alpha Fund and PPFAS Beta Fund", asset_type="mutual_fund", research_depth="standard", comparison_view_mode="canvas")
    response = asyncio.run(main.chat_endpoint(req))

    assert "quant_data" in response
    assert "comparison" in response["quant_data"]
    assert "why_better" in response["quant_data"]


def test_compare_synthesis_includes_direct_difference_section(monkeypatch):
    from app.services import chat_service as main

    async def fake_function_ollama_chat(*_args, **_kwargs):
        return "Trend text."

    monkeypatch.setattr(main, "function_ollama_chat", fake_function_ollama_chat)

    quant_data = {
        "comparison": {
            "ICICI Multi asset fund": {
                "name": "ICICI Multi asset fund",
                "nav": 100.5,
                "nav_date": "2026-05-14",
                "expense_ratio": 1.2,
                "source": "MarketMind DB",
                "data_quality": {"missing_fields": []},
                "source_summary": {"stale": False, "metadata": "MarketMind DB"},
            },
            "Parag Flexi Cap": {
                "name": "Parag Flexi Cap",
                "nav": 98.2,
                "nav_date": "2026-05-14",
                "expense_ratio": 1.6,
                "source": "MarketMind DB",
                "data_quality": {"missing_fields": []},
                "source_summary": {"stale": False, "metadata": "MarketMind DB"},
            },
        },
        "why_better": {
            "winner": {
                "entity_name": "ICICI Multi asset fund",
                "status": "winner",
            },
            "confidence": {"label": "Low", "score": 0.2},
            "factor_results": [
                {"factor": "Returns (3Y)", "winner": None, "coverage": 0.5},
                {"factor": "Risk (Volatility 1Y)", "winner": None, "coverage": 0.5},
                {"factor": "Cost (Expense Ratio)", "winner": "ICICI Multi asset fund", "coverage": 1.0},
            ],
            "data_limitations": ["holdings data missing"],
        },
    }

    response = asyncio.run(
        main.synthesis_response(
            query="Compare ICICI Multi asset fund and Parag Flexi Cap. How are they different?",
            intent_info={"intent": "compare", "ticker": None},
            quant_data=quant_data,
            news_data=[],
            comparison_view_mode="chat",
        )
    )

    assert "### How They Differ" in response
    assert "- Overall: ICICI Multi asset fund ranks higher on the selected deterministic factors." in response
    assert "- Returns (3Y): No clear edge (coverage: 50%)" in response


def test_compare_synthesis_canvas_mode_hides_data_table(monkeypatch):
    from app.services import chat_service as main

    async def fake_function_ollama_chat(*_args, **_kwargs):
        raise AssertionError("OpenRouter synthesis called")

    monkeypatch.setattr(main, "function_ollama_chat", fake_function_ollama_chat)

    response = asyncio.run(
        main.synthesis_response(
            query="Compare A and B",
            intent_info={"intent": "compare", "ticker": None},
            quant_data={
                "comparison": {
                    "A": {"name": "A", "nav": 100, "source_summary": {"stale": False}},
                    "B": {"name": "B", "nav": 110, "source_summary": {"stale": False}},
                },
                "why_better": {
                    "winner": {"entity_name": "B", "status": "winner"},
                    "confidence": {"label": "Medium", "score": 0.6},
                    "factor_results": [{"factor": "Returns (3Y)", "winner": "B", "coverage": 1.0}],
                },
            },
            news_data=[],
            comparison_view_mode="canvas",
        )
    )

    assert "Canvas is open with the full metric view" in response
    assert "### What the Data Says" in response
    assert "### Data Table" not in response
    assert "### How They Differ" not in response


def test_compare_synthesis_canvas_followup_calls_model(monkeypatch):
    from app.services import chat_service as main

    seen = {}

    async def fake_function_ollama_chat(*_args, **kwargs):
        seen["timeout_seconds"] = kwargs.get("timeout_seconds")
        return "Model follow-up explanation."

    monkeypatch.setattr(main, "function_ollama_chat", fake_function_ollama_chat)

    response = asyncio.run(
        main.synthesis_response(
            query="Why is B riskier?",
            intent_info={"intent": "compare", "ticker": None, "followup_question": "Why is B riskier?"},
            quant_data={
                "comparison": {
                    "A": {"name": "A", "nav": 100, "source_summary": {"stale": False}},
                    "B": {"name": "B", "nav": 110, "source_summary": {"stale": False}},
                },
                "why_better": {
                    "winner": {"entity_name": "B", "status": "winner"},
                    "confidence": {"label": "Medium", "score": 0.6},
                    "factor_results": [{"factor": "Risk (Volatility 1Y)", "winner": "A", "coverage": 1.0}],
                },
            },
            news_data=[],
            comparison_view_mode="canvas",
        )
    )

    assert seen["timeout_seconds"] == 20.0
    assert "Model follow-up explanation." in response
    assert "### Follow-up Answer" in response
    assert "### Data Table" not in response


def test_compare_intent_preserves_same_message_followup_question():
    from app.services import chat_service as main

    intent = main._deterministic_compare_intent(
        "Compare HDFC Flexi and ICICI Large cap. What fund is better for long term investment and which fund has higher downside protection?",
        asset_type="mutual_fund",
    )

    assert intent is not None
    assert intent["intent"] == "compare"
    assert intent["compare_entities"] == ["HDFC Flexi Cap", "ICICI Prudential Large Cap"]
    assert intent["historical_period"] == "5y"
    assert intent["downside_focus"] is True
    assert "higher downside protection" in intent["followup_question"].lower()


def test_compare_synthesis_canvas_advanced_calls_model(monkeypatch):
    from app.services import chat_service as main

    seen = {}

    async def fake_function_ollama_chat(*_args, **kwargs):
        seen["timeout_seconds"] = kwargs.get("timeout_seconds")
        return "Advanced model synthesis."

    monkeypatch.setattr(main, "function_ollama_chat", fake_function_ollama_chat)

    response = asyncio.run(
        main.synthesis_response(
            query="Compare A and B",
            intent_info={"intent": "compare", "ticker": None},
            quant_data={
                "comparison": {
                    "A": {"name": "A", "nav": 100, "source_summary": {"stale": False}},
                    "B": {"name": "B", "nav": 110, "source_summary": {"stale": False}},
                },
                "why_better": {
                    "winner": {"entity_name": "B", "status": "winner"},
                    "confidence": {"label": "Medium", "score": 0.6},
                    "factor_results": [{"factor": "Returns (3Y)", "winner": "B", "coverage": 1.0}],
                },
            },
            news_data=[],
            research_depth="deep",
            explanation_mode="advanced",
            comparison_view_mode="canvas",
        )
    )

    assert seen["timeout_seconds"] == 20.0
    assert "Advanced model synthesis." in response
    assert "### Data Table" not in response


def test_news_markdown_has_takeaway_quote_and_source_link():
    from app.services import chat_service as main

    news = [
        {
            "title": "Two funds receive over Rs 1,000 crore inflow in November",
            "source": "The Economic Times",
            "published": "Sat, 13 Dec 2025 08:00:00 GMT",
            "url": "https://example.com/news-1",
            "sentiment": "NEUTRAL",
        }
    ]

    formatted = main._news_markdown(news)

    assert "Takeaway:" in formatted
    assert "Quoted headline:" in formatted
    assert "([The Economic Times](https://example.com/news-1))" in formatted


def test_current_events_query_routes_to_news_without_llm():
    from app.services import chat_service as main

    intent = asyncio.run(
        main.route_query(
            "What is the status of the Iran US peace deal and how does it affect the Indian market?",
            "auto",
        )
    )

    assert intent["intent"] == "news"
    assert intent["answer_mode"] == "market_current_events"
    assert intent["ticker"] is None


def test_current_events_chat_fetches_news_and_returns_metadata(monkeypatch):
    from app.services import chat_service as main

    calls = []

    def fake_fetch_news(query, ticker, *_args, **_kwargs):
        calls.append((query, ticker))
        return [
            {
                "title": "Oil eases as Iran US talks resume",
                "source": "The Economic Times",
                "published": "Fri, 19 Jun 2026 08:00:00 GMT",
                "url": "https://example.com/oil",
            }
        ]

    async def fake_function_ollama_chat(*_args, **_kwargs):
        return "### Current Status\nTalks are being tracked through approved headlines.\n\n### Indian Market Impact\nOil and INR are the first channels to watch."

    monkeypatch.setattr(main, "fetch_news", fake_fetch_news)
    monkeypatch.setattr(main, "function_ollama_chat", fake_function_ollama_chat)

    req = main.ChatRequest(
        query="What is the status of the Iran US peace deal and how does it affect the Indian market?",
        asset_type="auto",
    )
    response = asyncio.run(main.ChatService(None).handle_chat(req))

    assert calls
    assert response["answer_mode"] == "market_current_events"
    assert response["news_context_status"] == "stale"
    assert response["sources"][0]["source"] == "The Economic Times"
    assert response["reasoning_summary"]["title"] == "Reasoning summary"
    assert response["reasoning_summary"]["steps"][0]["label"] == "Routed"
    assert "Indian Market Impact" in response["answer"]


def test_current_events_no_prefetched_source_uses_web_search(monkeypatch):
    from app.services import chat_service as main

    captured = {}

    async def fake_function_ollama_chat(*_args, **kwargs):
        captured.update(kwargs)
        kwargs["citation_collector"].append(
            {
                "title": "Current Reuters report",
                "source": "Reuters",
                "url": "https://www.reuters.com/current-report",
                "published": None,
                "context_type": "openrouter_web_search",
            }
        )
        return "### Current View\nThe latest verified evidence remains mixed."

    monkeypatch.setattr(main, "function_ollama_chat", fake_function_ollama_chat)

    meta = {}
    response = asyncio.run(
        main.synthesis_response(
            query="What is the status of the Iran US peace deal and how does it affect the Indian market?",
            intent_info={"intent": "news", "ticker": None, "answer_mode": "market_current_events"},
            quant_data={},
            news_data=[],
            response_meta=meta,
        )
    )

    assert "latest verified evidence" in response
    assert captured["enable_web_search"] is True
    assert meta["answer_mode"] == "market_current_events"
    assert meta["news_context_status"] == "current_web_search"
    assert meta["model_status"] == "completed"
    assert meta["sources"][0]["source"] == "Reuters"


def test_current_events_no_source_response_has_limited_thinking(monkeypatch):
    from app.services import chat_service as main

    async def fake_function_ollama_chat(*_args, **_kwargs):
        return None

    monkeypatch.setattr(main, "fetch_news", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(main, "function_ollama_chat", fake_function_ollama_chat)

    req = main.ChatRequest(
        query="What is the status of the Iran US peace deal and how does it affect the Indian market?",
        asset_type="auto",
    )
    response = asyncio.run(main.ChatService(None).handle_chat(req))

    assert response["reasoning_summary"]["title"] == "Reasoning summary"
    assert response["reasoning_summary"]["steps"][1]["status"] == "limited"
    assert "News source coverage was unavailable." in response["reasoning_summary"]["limits"]
    assert response["status_flag"] == "deterministic_fallback"
    assert "synthesis step" not in response["answer"]
