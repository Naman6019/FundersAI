from __future__ import annotations

from types import SimpleNamespace


class _FakeQuery:
    def __init__(self, root, table_name: str):
        self.root = root
        self.table_name = table_name
        self.ilike_filters: list[tuple[str, str]] = []
        self.eq_filters: list[tuple[str, object]] = []
        self.order_by: list[tuple[str, bool]] = []
        self.limit_value = None

    def select(self, fields: str, count=None):
        self.root.selected_tables.append((self.table_name, fields))
        self.count_requested = count == "exact"
        return self

    def ilike(self, key: str, pattern: str):
        self.ilike_filters.append((key, pattern))
        return self

    def eq(self, key: str, value):
        self.eq_filters.append((key, value))
        return self

    def order(self, key: str, desc=False):
        self.order_by.append((key, bool(desc)))
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
        for key, value in self.eq_filters:
            rows = [row for row in rows if str(row.get(key)) == str(value)]
        for key, desc in reversed(self.order_by):
            rows.sort(key=lambda row: row.get(key) or 0, reverse=desc)
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
                    "risk_level": "Very High",
                    "nav_date": "2026-06-01",
                },
                {
                    "scheme_name": "SBI Large Cap Fund",
                    "amc_name": "SBI Mutual Fund",
                    "category": "Large Cap",
                    "return_3y": 15.0,
                    "aum": 900,
                    "expense_ratio": 0.7,
                    "risk_level": "High",
                    "nav_date": "2026-06-01",
                },
                {
                    "scheme_name": "Other Large Cap Fund",
                    "amc_name": "Other AMC",
                    "category": "Large Cap",
                    "return_3y": 40.0,
                    "aum": 5000,
                    "expense_ratio": 1.0,
                    "risk_level": "Moderate",
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
    assert "risk_level" in fake.selected_tables[0][1]
    assert response["quant_data"]["category_search"]["ranking"] == "Top by 3Y return"
    assert response["quant_data"]["category_search"]["rows"][0]["scheme_name"] == "SBI Large Cap Fund"
    assert response["quant_data"]["category_search"]["rows"][0]["risk_level"] == "High"
    assert "Risk Label" in response["answer"]
    assert "Other Large Cap Fund" not in response["answer"]


def test_category_list_includes_unsupported_as_coming_soon(monkeypatch):
    from app import main as app_main

    fake = _FakeSupabase(
        {
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "1",
                    "scheme_name": "HDFC Large Cap Fund",
                    "amc_name": "HDFC Mutual Fund",
                    "category": "Large Cap",
                    "return_3y": 12.0,
                    "aum": 1000,
                    "risk_level": "High",
                },
                {
                    "scheme_code": "2",
                    "scheme_name": "Axis Large Cap Fund",
                    "amc_name": "Axis Mutual Fund",
                    "category": "Large Cap",
                    "return_3y": 16.0,
                    "aum": 2000,
                    "risk_level": None,
                },
            ]
        }
    )
    monkeypatch.setattr(app_main, "supabase", fake)

    payload = app_main._category_list_payload("large_cap")

    assert len(payload["rows"]) == 2
    unsupported = [row for row in payload["rows"] if row["scheme_name"] == "Axis Large Cap Fund"][0]
    assert unsupported["is_supported"] is False
    assert unsupported["disabled_reason"] == "Coming Soon"
    supported = [row for row in payload["rows"] if row["scheme_name"] == "HDFC Large Cap Fund"][0]
    assert supported["is_supported"] is True
    assert supported["risk_level"] == "High"


def test_category_compare_rejects_unsupported_fund(monkeypatch):
    from app import main as app_main
    from fastapi import HTTPException

    fake = _FakeSupabase(
        {
            "mutual_fund_core_snapshot": [
                {"scheme_code": "1", "scheme_name": "HDFC Large Cap Fund", "amc_name": "HDFC Mutual Fund", "category": "Large Cap"},
                {"scheme_code": "2", "scheme_name": "Axis Large Cap Fund", "amc_name": "Axis Mutual Fund", "category": "Large Cap"},
            ]
        }
    )
    monkeypatch.setattr(app_main, "supabase", fake)

    try:
        app_main._build_category_compare_payload("large_cap", ["1", "2"])
    except HTTPException as exc:
        assert exc.status_code == 400
        assert "Coming Soon" in str(exc.detail)
    else:
        raise AssertionError("Unsupported fund should be rejected")


def test_category_compare_returns_metrics_and_overlap_for_three_funds(monkeypatch):
    from app import main as app_main

    fake = _FakeSupabase(
        {
            "mutual_fund_core_snapshot": [
                {"scheme_code": "1", "scheme_name": "HDFC Large Cap Fund", "amc_name": "HDFC Mutual Fund", "category": "Large Cap", "return_3y": 12.0, "expense_ratio": 0.5, "risk_level": "High"},
                {"scheme_code": "2", "scheme_name": "SBI Large Cap Fund", "amc_name": "SBI Mutual Fund", "category": "Large Cap", "return_3y": 11.0, "expense_ratio": 0.6, "risk_level": "Very High"},
                {"scheme_code": "3", "scheme_name": "ICICI Prudential Large Cap Fund", "amc_name": "ICICI Prudential Mutual Fund", "category": "Large Cap", "return_3y": 10.0, "expense_ratio": 0.7, "risk_level": None},
            ],
            "mutual_fund_holdings": [
                {"scheme_code": "1", "as_of_date": "2026-05-31", "security_name": "HDFC Bank", "isin": "INE040A01034", "sector": "Banks", "weight_pct": 7.0},
                {"scheme_code": "2", "as_of_date": "2026-05-31", "security_name": "HDFC Bank", "isin": "INE040A01034", "sector": "Banks", "weight_pct": 6.0},
                {"scheme_code": "3", "as_of_date": "2026-05-31", "security_name": "HDFC Bank", "isin": "INE040A01034", "sector": "Banks", "weight_pct": 5.0},
            ],
        }
    )
    monkeypatch.setattr(app_main, "supabase", fake)

    payload = app_main._build_category_compare_payload("large_cap", ["1", "2", "3"])

    assert payload["category"] == "Large Cap"
    assert len(payload["selected_funds"]) == 3
    assert payload["selected_funds"][0]["return_3y"] == 12.0
    assert payload["selected_funds"][0]["risk_level"] == "High"
    assert "risk_level" in payload["metric_groups"]["risk"]
    assert payload["overlap"]["coverage_status"] == "available"
    assert payload["overlap"]["common_holding_count"] == 1
    assert payload["insights"]["headline"]


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


def test_compare_shorthand_maps_to_mutual_fund_canvas_intent():
    from app import main as app_main

    intent = app_main._deterministic_compare_intent(
        "Compare HDFC Flexi and Parag Flexi for long term",
        "mutual_fund",
    )

    assert intent is not None
    assert intent["intent"] == "compare"
    assert intent["asset_type"] == "mutual_fund"
    assert intent["historical_period"] == "5y"
    assert intent["compare_entities"] == ["HDFC Flexi Cap", "Parag Parikh Flexi Cap"]


def test_compare_query_can_include_same_message_followup():
    from app import main as app_main

    intent = app_main._deterministic_compare_intent(
        "Compare HDFC Flexi and Parag Flexi and why do returns differ?",
        "mutual_fund",
    )

    assert intent is not None
    assert intent["compare_entities"] == ["HDFC Flexi Cap", "Parag Parikh Flexi Cap"]
    assert intent["followup_question"] == "why do returns differ?"


def test_compare_followup_reuses_previous_compare_from_history():
    from app import main as app_main

    history = [
        {"role": "user", "content": "Compare HDFC Flexi and Parag Flexi"},
        {"role": "system", "content": "### HDFC Flexi Cap vs Parag Parikh Flexi Cap"},
    ]

    intent = app_main._followup_compare_intent(
        "Why do the returns differ in both?",
        history,
        "mutual_fund",
    )

    assert intent is not None
    assert intent["intent"] == "compare"
    assert intent["followup_from_history"] is True
    assert intent["followup_question"] == "Why do the returns differ in both?"
    assert intent["compare_entities"] == ["HDFC Flexi Cap", "Parag Parikh Flexi Cap"]


def test_compare_followup_with_category_words_still_reuses_history():
    from app import main as app_main

    history = [
        {"role": "user", "content": "Compare HDFC Flexi and Parag Flexi"},
        {"role": "system", "content": "### HDFC Flexi Cap vs Parag Parikh Flexi Cap"},
    ]

    intent = app_main._followup_compare_intent(
        "Why does the return differ for both even if the funds are flexi cap?",
        history,
        "mutual_fund",
    )
    dashboard_intent = app_main._dashboard_tool_intent(
        "Why does the return differ for both even if the funds are flexi cap?",
        "mutual_fund",
    )

    assert dashboard_intent["intent"] == "category_search"
    assert intent is not None
    assert intent["intent"] == "compare"
    assert intent["followup_from_history"] is True
    assert intent["compare_entities"] == ["HDFC Flexi Cap", "Parag Parikh Flexi Cap"]


def test_compare_followup_prefers_structured_context_over_history():
    from app import main as app_main

    context = {
        "last_compare": {
            "asset_type": "mutual_fund",
            "entities": ["ICICI Multi Asset", "Parag Parikh Flexi Cap"],
            "ids": ["120546", "122639"],
            "query": "Compare ICICI Multi Asset and Parag Flexi",
        }
    }
    history = [
        {"role": "user", "content": "Compare HDFC Flexi and Parag Flexi"},
    ]

    intent = app_main._followup_compare_intent(
        "Which one has lower risk?",
        history,
        "mutual_fund",
        context,
    )

    assert intent is not None
    assert intent["followup_from_context"] is True
    assert intent["followup_from_history"] is False
    assert intent["compare_entities"] == ["ICICI Multi Asset", "Parag Parikh Flexi Cap"]
    assert intent["compare_ids"] == ["120546", "122639"]
    assert intent["followup_topic"] == "risk"


def test_comparison_summary_builds_verdict_cards():
    from app import main as app_main

    summary = app_main._build_comparison_summary(
        {
            "comparison": {
                "HDFC Flexi Cap": {"return_3y": 14.2, "volatility_1y": 11.1, "expense_ratio": 0.74},
                "Parag Parikh Flexi Cap": {"return_3y": 18.4, "volatility_1y": 9.8, "expense_ratio": 0.63},
            }
        }
    )

    assert "Parag Parikh Flexi Cap" in summary["headline"]
    assert len(summary["verdict_cards"]) == 4
    assert summary["verdict_cards"][0]["label"] == "Return profile"


def test_holdings_overlap_matches_common_isins_and_sectors():
    from app import main as app_main

    overlap = app_main._build_holdings_overlap(
        {
            "Fund A": {
                "holdings": [
                    {"security_name": "ABC Ltd", "isin": "INE001", "sector": "Financials", "weight_pct": 5.0, "as_of_date": "2026-05-31"},
                    {"security_name": "XYZ Ltd", "isin": "INE002", "sector": "Technology", "weight_pct": 3.0, "as_of_date": "2026-05-31"},
                ]
            },
            "Fund B": {
                "holdings": [
                    {"security_name": "ABC Ltd", "isin": "INE001", "sector": "Financials", "weight_pct": 4.0, "as_of_date": "2026-05-31"},
                    {"security_name": "Other Ltd", "isin": "INE003", "sector": "Energy", "weight_pct": 6.0, "as_of_date": "2026-05-31"},
                ]
            },
        }
    )

    assert overlap["coverage_status"] == "available"
    assert overlap["common_holding_count"] == 1
    assert overlap["total_overlap_weight"] == 4.0
    assert overlap["top_common_holdings"][0]["isin"] == "INE001"
    assert overlap["sector_overlap"][0]["sector"] == "Financials"


def test_holdings_overlap_reports_unavailable_when_missing():
    from app import main as app_main

    overlap = app_main._build_holdings_overlap(
        {
            "Fund A": {"holdings": []},
            "Fund B": {"holdings": [{"security_name": "ABC Ltd", "isin": "INE001", "weight_pct": 4.0}]},
        }
    )

    assert overlap["coverage_status"] == "unavailable"


def test_comparison_followup_answer_explains_return_gap():
    from app import main as app_main

    answer = app_main._comparison_followup_answer_markdown(
        {
            "comparison": {
                "HDFC Flexi Cap": {"return_3y": 14.2, "volatility_1y": 11.1, "expense_ratio": 0.74},
                "Parag Parikh Flexi Cap": {"return_3y": 18.4, "volatility_1y": 9.8, "expense_ratio": 0.63},
            }
        },
        "Why do the returns differ in both?",
    )

    assert "3Y return" in answer
    assert "portfolio composition" in answer


def test_comparison_followup_answer_uses_holdings_overlap():
    from app import main as app_main

    answer = app_main._comparison_followup_answer_markdown(
        {
            "comparison": {
                "Fund A": {"return_3y": 12.0},
                "Fund B": {"return_3y": 13.0},
            },
            "holdings_overlap": {
                "coverage_status": "available",
                "total_overlap_weight": 4.0,
                "common_holding_count": 1,
                "top_common_holdings": [{"name": "ABC Ltd", "overlap_weight": 4.0}],
            },
        },
        "Do they hold the same stocks?",
    )

    assert "Holdings overlap weight is 4.00%" in answer
    assert "ABC Ltd" in answer


def test_controlled_web_context_filters_to_approved_sources():
    from app import main as app_main

    assert app_main._is_approved_web_source("Mint")
    assert app_main._is_approved_web_source("Value Research")
    assert not app_main._is_approved_web_source("Random Blog")


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


def test_portfolio_parser_accepts_fund_name_then_amount():
    from app import main as app_main

    holdings = app_main._parse_portfolio_holdings(
        "Parag Flexi Cap 10K, HDFC Flexi Cap 12K and ICICI Large Cap 10K"
    )

    assert holdings == [
        {"input_name": "Parag Flexi Cap", "amount": 10000.0},
        {"input_name": "HDFC Flexi Cap", "amount": 12000.0},
        {"input_name": "ICICI Large Cap", "amount": 10000.0},
    ]


def test_portfolio_parser_accepts_amount_first_and_colon_formats():
    from app import main as app_main

    amount_first = app_main._parse_portfolio_holdings(
        "50k in Parag Parikh Flexi Cap, 20k in HDFC Mid-Cap"
    )
    colon = app_main._parse_portfolio_holdings(
        "Parag Parikh Flexi Cap: 50k, HDFC Mid-Cap = 20k"
    )

    assert amount_first[0]["input_name"] == "Parag Parikh Flexi Cap"
    assert amount_first[0]["amount"] == 50000.0
    assert colon[1]["input_name"] == "HDFC Mid-Cap"
    assert colon[1]["amount"] == 20000.0


def test_portfolio_fund_name_normalization_supports_active_amcs():
    from app import main as app_main

    assert app_main._normalize_portfolio_fund_name("Parag Flexi Cap") == "Parag Parikh Flexi Cap"
    assert app_main._normalize_portfolio_fund_name("HDFC Mid-Cap") == "HDFC Mid Cap Opportunities"
    assert app_main._normalize_portfolio_fund_name("SBI Bluechip") == "SBI Blue Chip"
    assert app_main._normalize_portfolio_fund_name("ICICI Large Cap") == "ICICI Prudential Large Cap"
    assert app_main._normalize_portfolio_fund_name("ICICI Multi Asset") == "ICICI Prudential Multi Asset"


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


def test_portfolio_review_matches_supported_amc_shorthand(monkeypatch):
    from app import main as app_main

    fake = _FakeSupabase(
        {
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "122639",
                    "scheme_name": "Parag Parikh Flexi Cap Fund - Direct Plan - Growth",
                    "amc_name": "PPFAS Mutual Fund",
                    "category": "Flexi Cap",
                    "return_3y": 18.0,
                    "aum": 1000,
                    "expense_ratio": 0.6,
                    "nav_date": "2026-06-01",
                },
                {
                    "scheme_code": "118955",
                    "scheme_name": "HDFC Growth Fund - Direct Plan - Growth",
                    "amc_name": "HDFC Mutual Fund",
                    "category": "Equity Scheme - Mid Cap Fund",
                    "return_3y": 16.0,
                    "aum": 900,
                    "expense_ratio": 0.7,
                    "nav_date": "2026-06-01",
                },
                {
                    "scheme_code": "102000",
                    "scheme_name": "SBI Large Cap Fund - Direct Plan - Growth",
                    "amc_name": "SBI Mutual Fund",
                    "category": "Unclassified",
                    "return_3y": 14.0,
                    "aum": 800,
                    "expense_ratio": 0.5,
                    "nav_date": "2026-06-01",
                },
                {
                    "scheme_code": "103000",
                    "scheme_name": "ICICI Prudential Large Cap Fund - Direct Plan - Growth",
                    "amc_name": "ICICI Prudential Mutual Fund",
                    "category": "Large Cap",
                    "return_3y": 13.0,
                    "aum": 700,
                    "expense_ratio": 0.4,
                    "nav_date": "2026-06-01",
                },
            ],
            "mutual_fund_nav_history": [],
        }
    )
    monkeypatch.setattr(app_main, "supabase", fake)

    response = app_main._build_portfolio_review_response(
        "Parag Flexi Cap 10K, HDFC Mid-Cap 20K, SBI Bluechip 30K and ICICI Large Cap 10K",
        [{"role": "user", "content": "Review my portfolio health"}],
    )
    review = response["quant_data"]["portfolio_review"]

    assert response["debug_intent"]["step"] == "complete"
    assert all(item["matched"] for item in review["holdings"])
    assert "Unmatched entries" not in response["answer"]
    matched_names = [item["matched"]["scheme_name"] for item in review["holdings"]]
    assert "HDFC Growth Fund - Direct Plan - Growth" in matched_names
    assert "SBI Large Cap Fund - Direct Plan - Growth" in matched_names
    buckets_by_input = {item["input_name"]: item["bucket"] for item in review["holdings"]}
    assert buckets_by_input["HDFC Mid-Cap"] == "Mid Cap"
    assert buckets_by_input["SBI Bluechip"] == "Large Cap"


def test_portfolio_review_reports_portfolio_overlap(monkeypatch):
    from app import main as app_main

    fake = _FakeSupabase(
        {
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "101",
                    "scheme_name": "SBI Large Cap Fund - Direct Plan - Growth",
                    "amc_name": "SBI Mutual Fund",
                    "category": "Large Cap",
                },
                {
                    "scheme_code": "102",
                    "scheme_name": "Parag Parikh Flexi Cap Fund - Direct Plan - Growth",
                    "amc_name": "PPFAS Mutual Fund",
                    "category": "Flexi Cap",
                },
                {
                    "scheme_code": "103",
                    "scheme_name": "HDFC Mid-Cap Opportunities Fund - Direct Plan - Growth",
                    "amc_name": "HDFC Mutual Fund",
                    "category": "Mid Cap",
                },
                {
                    "scheme_code": "104",
                    "scheme_name": "ICICI Prudential Smallcap Fund - Direct Plan - Growth",
                    "amc_name": "ICICI Prudential Mutual Fund",
                    "category": "Small Cap",
                },
            ],
            "mutual_fund_holdings": [
                {"scheme_code": "101", "as_of_date": "2026-05-31", "security_name": "Reliance Industries", "isin": "INE002A01018", "sector": "Energy", "weight_pct": 5.0},
                {"scheme_code": "101", "as_of_date": "2026-05-31", "security_name": "HDFC Bank", "isin": "INE040A01034", "sector": "Financials", "weight_pct": 7.0},
                {"scheme_code": "102", "as_of_date": "2026-05-31", "security_name": "HDFC Bank", "isin": "INE040A01034", "sector": "Financials", "weight_pct": 6.0},
                {"scheme_code": "102", "as_of_date": "2026-05-31", "security_name": "Bajaj Holdings", "isin": "INE118A01012", "sector": "Financials", "weight_pct": 4.0},
                {"scheme_code": "103", "as_of_date": "2026-05-31", "security_name": "HDFC Bank", "isin": "INE040A01034", "sector": "Financials", "weight_pct": 3.0},
                {"scheme_code": "104", "as_of_date": "2026-05-31", "security_name": "Smallcap Co", "isin": "INE999A01010", "sector": "Industrials", "weight_pct": 6.0},
            ],
        }
    )
    monkeypatch.setattr(app_main, "supabase", fake)

    response = app_main._build_portfolio_review_response(
        "SBI Large Cap 12K, PARAG Flexi 18K, HDFC Mid Cap 10K and ICICI Small Cap 10K",
        [{"role": "user", "content": "Review my portfolio health"}],
    )
    overlap = response["quant_data"]["portfolio_review"]["overlap"]

    assert overlap["coverage_status"] == "available"
    assert overlap["funds_with_holdings"] == 4
    assert overlap["common_holding_count"] == 1
    assert overlap["top_common_holdings"][0]["name"] == "HDFC Bank"
    assert round(overlap["top_common_holdings"][0]["portfolio_exposure"], 2) == 4.44
    assert round(overlap["top_common_holdings"][0]["overlap_exposure"], 2) == 2.28
    assert "Portfolio Overlap" in response["answer"]
    assert "Review Interpretation" in response["answer"]
    assert "HDFC Bank" in response["answer"]
    assert response["system_action"]["type"] == "PORTFOLIO_REVIEW"
    assert response["conversation_context"]["last_portfolio"]["overlap"]["common_holding_count"] == 1
    insights = response["quant_data"]["portfolio_review"]["insights"]
    assert insights["overlap_level"] == "Low"
    assert any("Duplicated stock exposure" in item for item in insights["review_points"])


def test_portfolio_followup_uses_last_portfolio_context():
    from app import main as app_main

    context = {
        "last_portfolio": {
            "query": "SBI Large Cap 12K, PARAG Flexi 18K",
            "score": 82,
            "label": "Good",
            "holdings": [
                {"input_name": "SBI Large Cap", "weight": 0.24, "bucket": "Large Cap"},
                {"input_name": "PARAG Flexi", "weight": 0.36, "bucket": "Flexi/Multi Cap"},
            ],
            "buckets": {"Large Cap": 12000.0, "Flexi/Multi Cap": 18000.0},
            "overlap": {
                "coverage_status": "available",
                "common_holding_count": 1,
                "total_overlap_exposure": 2.28,
                "top_common_holdings": [
                    {
                        "name": "HDFC Bank",
                        "portfolio_exposure": 4.44,
                        "overlap_exposure": 2.28,
                        "fund_count": 2,
                    }
                ],
                "sector_overlap": [{"sector": "Financials", "overlap_exposure": 2.28}],
            },
            "insights": {
                "headline": "The portfolio has some shared holdings, but duplicated stock exposure is not dominant.",
                "review_points": ["Overall label is Good with a score of 82/100."],
                "watchpoints": ["No single deterministic red flag appears."],
            },
        }
    }

    response = app_main._build_portfolio_followup_response("What is the actual overlap?", context)

    assert response is not None
    assert response["debug_intent"]["intent"] == "portfolio_followup"
    assert "Duplicated stock exposure is 2.28%" in response["answer"]
    assert "HDFC Bank" in response["answer"]
    assert response["system_action"]["type"] == "PORTFOLIO_REVIEW"

    review_response = app_main._build_portfolio_followup_response("Can you review this portfolio?", context)
    assert review_response is not None
    assert "Overall label is Good" in review_response["answer"]

    risk_response = app_main._build_portfolio_followup_response("Which fund has the most risk associated with it here?", context)
    assert risk_response is not None
    assert "Main fund-level risk driver" in risk_response["answer"]
    assert "PARAG Flexi" in risk_response["answer"]

    balance_response = app_main._build_portfolio_followup_response("What changes can be made to balance it better?", context)
    assert balance_response is not None
    assert "Balance levers to test" in balance_response["answer"]
    assert "not a new suitability recommendation" in balance_response["answer"]
