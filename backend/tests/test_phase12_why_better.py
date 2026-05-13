import asyncio


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
    from app import main

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
                "scheme_name": "Alpha Fund",
                "nav": 120.5,
                "nav_date": "2026-05-10",
                "category": "Flexi Cap",
                "amc_name": "AMC A",
                "expense_ratio": 1.2,
                "aum": 10000,
                "return_3y": 12.3,
                "volatility_1y": 13.0,
            },
            {
                "scheme_code": "1002",
                "scheme_name": "Beta Fund",
                "nav": 98.7,
                "nav_date": "2026-05-10",
                "category": "Flexi Cap",
                "amc_name": "AMC B",
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
        return {"intent": "compare", "compare_entities": ["Alpha Fund", "Beta Fund"], "ticker": None, "historical_period": "1mo", "sentiment_flag": False}

    async def fake_synthesis_response(*_args, **_kwargs):
        return "ok"

    monkeypatch.setattr(main, "supabase", FakeSupabase(fake_db))
    monkeypatch.setattr(main, "route_query", fake_route_query)
    monkeypatch.setattr(main, "synthesis_response", fake_synthesis_response)
    monkeypatch.setattr(main, "fetch_news", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(main, "analyze_news_sentiment", lambda news: news)
    monkeypatch.setattr(main, "mfapi_get_latest_nav", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("live mfapi called")))
    monkeypatch.setattr(main, "mfapi_get_nav_history", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("live mfapi called")))

    class FailTicker:
        def __init__(self, *_args, **_kwargs):
            raise AssertionError("live yfinance called")

    monkeypatch.setattr(main.yf, "Ticker", FailTicker)

    req = main.ChatRequest(query="Compare Alpha Fund and Beta Fund", asset_type="mutual_fund", research_depth="standard")
    response = asyncio.run(main.chat_endpoint(req))

    assert "quant_data" in response
    assert "comparison" in response["quant_data"]
    assert "why_better" in response["quant_data"]
