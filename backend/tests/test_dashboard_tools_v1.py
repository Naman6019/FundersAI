from __future__ import annotations

from types import SimpleNamespace


class _FakeQuery:
    def __init__(self, root, table_name: str):
        self.root = root
        self.table_name = table_name
        self.ilike_filters: list[tuple[str, str]] = []
        self.limit_value = None

    def select(self, fields: str, count=None):
        self.root.selected_tables.append((self.table_name, fields))
        self.count_requested = count == "exact"
        return self

    def ilike(self, key: str, pattern: str):
        self.ilike_filters.append((key, pattern))
        return self

    def limit(self, value: int):
        self.limit_value = value
        return self

    def execute(self):
        rows = list(self.root.tables.get(self.table_name, []))
        for key, pattern in self.ilike_filters:
            needles = [part.lower() for part in pattern.split("%") if part]
            rows = [
                row
                for row in rows
                if all(needle in str(row.get(key) or "").lower() for needle in needles)
            ]
        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        return SimpleNamespace(data=rows)


class _FakeSupabase:
    def __init__(self, tables: dict[str, list[dict]]):
        self.tables = tables
        self.selected_tables: list[tuple[str, str]] = []

    def table(self, name: str):
        return _FakeQuery(self, name)


def test_sip_projection_uses_standard_monthly_formula():
    from app import main as app_main

    projection = app_main._calculate_sip_projection(10_000, 10, 12)

    assert projection["total_invested"] == 1_200_000
    assert round(projection["estimated_value"], 2) == 2_323_390.76
    assert round(projection["estimated_gain"], 2) == 1_123_390.76


def test_sip_response_defaults_rate_when_missing():
    from app import main as app_main

    response = app_main._build_sip_calculator_response(
        "Calculate SIP returns for 10000 per month for 10 years"
    )

    assert response is not None
    assert response["debug_intent"]["intent"] == "sip_calculator"
    assert response["debug_intent"]["annual_rate"] == 12.0
    assert response["debug_intent"]["rate_defaulted"] is True
    assert "Assumption: expected annual return defaults to 12.00%" in response["answer"]
    assert "INR 2,323,391" in response["answer"]


def test_category_search_reads_core_snapshot_and_ranks_by_3y_return(monkeypatch):
    from app import main as app_main

    fake = _FakeSupabase(
        {
            "mutual_fund_core_snapshot": [
                {
                    "scheme_name": "HDFC Large Cap Fund",
                    "amc_name": "HDFC Mutual Fund",
                    "category": "Large Cap",
                    "return_3y": 12.0,
                    "aum": 1000,
                    "expense_ratio": 0.6,
                    "nav_date": "2026-06-01",
                },
                {
                    "scheme_name": "SBI Large Cap Fund",
                    "amc_name": "SBI Mutual Fund",
                    "category": "Large Cap",
                    "return_3y": 15.0,
                    "aum": 900,
                    "expense_ratio": 0.7,
                    "nav_date": "2026-06-01",
                },
                {
                    "scheme_name": "Other Large Cap Fund",
                    "amc_name": "Other AMC",
                    "category": "Large Cap",
                    "return_3y": 40.0,
                    "aum": 5000,
                    "expense_ratio": 1.0,
                    "nav_date": "2026-06-01",
                },
            ]
        }
    )
    monkeypatch.setattr(app_main, "supabase", fake)

    intent = app_main._dashboard_tool_intent("Show me top large cap funds", "mutual_fund")
    response = app_main._build_category_search_response(intent)

    assert intent["intent"] == "category_search"
    assert fake.selected_tables[0][0] == "mutual_fund_core_snapshot"
    assert response["quant_data"]["category_search"]["ranking"] == "Top by 3Y return"
    assert response["quant_data"]["category_search"]["rows"][0]["scheme_name"] == "SBI Large Cap Fund"
    assert "Other Large Cap Fund" not in response["answer"]


def test_empty_category_search_returns_clear_message(monkeypatch):
    from app import main as app_main

    monkeypatch.setattr(app_main, "supabase", _FakeSupabase({"mutual_fund_core_snapshot": []}))

    intent = {
        "intent": "category_search",
        "category_key": "large_cap",
        "category_label": "Large Cap",
    }
    response = app_main._build_category_search_response(intent)

    assert "No matching Large Cap fund data is available" in response["answer"]
    assert response["quant_data"]["category_search"]["rows"] == []


def test_risk_quiz_starts_with_first_question():
    from app import main as app_main

    response = app_main._build_risk_quiz_response("Help me find my risk profile", [])

    assert response is not None
    assert response["debug_intent"]["intent"] == "risk_quiz"
    assert response["debug_intent"]["step"] == 1
    assert "If your portfolio fell 15%" in response["answer"]


def test_risk_quiz_completes_from_history():
    from app import main as app_main

    history = [
        {"role": "user", "content": "Help me find my risk profile"},
        {"role": "system", "content": "### Risk Quiz\n1. If your portfolio fell 15%"},
        {"role": "user", "content": "B"},
        {"role": "system", "content": "### Risk Quiz\n2. When do you expect"},
        {"role": "user", "content": "C"},
        {"role": "system", "content": "### Risk Quiz\n3. What matters"},
    ]

    response = app_main._build_risk_quiz_response("B", history)

    assert response is not None
    assert response["debug_intent"]["step"] == "complete"
    assert response["debug_intent"]["score"] == 4
    assert response["debug_intent"]["profile"] == "Moderate"
    assert "Risk Profile Result" in response["answer"]


def test_portfolio_review_prompts_for_holdings():
    from app import main as app_main

    response = app_main._build_portfolio_review_response("Review my portfolio health", [])

    assert response is not None
    assert response["debug_intent"]["step"] == "awaiting_holdings"
    assert "Paste your mutual fund holdings" in response["answer"]


def test_portfolio_review_parses_matches_and_scores(monkeypatch):
    from app import main as app_main

    fake = _FakeSupabase(
        {
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "122639",
                    "scheme_name": "Parag Parikh Flexi Cap Fund Direct Growth",
                    "amc_name": "PPFAS Mutual Fund",
                    "category": "Flexi Cap",
                    "return_3y": 18.0,
                    "aum": 1000,
                    "expense_ratio": 0.6,
                    "nav_date": "2026-06-01",
                },
                {
                    "scheme_code": "118955",
                    "scheme_name": "HDFC Mid Cap Opportunities Fund Direct Growth",
                    "amc_name": "HDFC Mutual Fund",
                    "category": "Mid Cap",
                    "return_3y": 16.0,
                    "aum": 900,
                    "expense_ratio": 0.7,
                    "nav_date": "2026-06-01",
                },
            ],
            "mutual_fund_nav_history": [],
        }
    )
    monkeypatch.setattr(app_main, "supabase", fake)
    history = [
        {"role": "user", "content": "Review my portfolio health"},
        {"role": "system", "content": "Paste your mutual fund holdings"},
    ]

    response = app_main._build_portfolio_review_response(
        "50k in Parag Parikh Flexi Cap, 20k in HDFC Mid Cap Opportunities",
        history,
    )

    assert response is not None
    assert response["debug_intent"]["intent"] == "portfolio_review"
    assert response["debug_intent"]["step"] == "complete"
    assert response["quant_data"]["portfolio_review"]["score"] > 0
    assert "Parag Parikh Flexi Cap Fund Direct Growth" in response["answer"]
    assert "Flexi/Multi Cap" in response["answer"]
