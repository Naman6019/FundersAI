from app.services.comparison_reasoning import build_mf_why_better, build_stock_why_better


def test_stock_risk_analysis_flags_debt_stale_and_missing_data():
    payload = build_stock_why_better(
        {
            "ABC": {
                "fundamentals": {"debt_to_equity": 2.4, "pe": 70, "profit_growth_3y": -4},
                "data_quality": {"missing_fields": ["roe", "roce"]},
                "source_summary": {"stale": True, "stale_warning": "Price data is stale."},
            },
            "XYZ": {
                "fundamentals": {"debt_to_equity": 0.2, "pe": 18, "profit_growth_3y": 12},
                "data_quality": {"missing_fields": []},
                "source_summary": {"stale": False},
            },
        }
    )

    items = payload["risk_analysis"]["items"]
    labels = {(item["entity"], item["label"], item["level"]) for item in items}
    assert ("ABC", "Debt risk", "High") in labels
    assert ("ABC", "Valuation risk", "High") in labels
    assert ("ABC", "Earnings trend", "High") in labels
    assert ("ABC", "Freshness risk", "Medium") in labels
    assert any(item["label"] == "Data availability" and item["kind"] == "data_gap" for item in items)
    assert all(item["kind"] == "risk" for item in items if item["level"] in {"High", "Medium"} and item["label"] != "Data availability")


def test_mf_risk_analysis_flags_expense_volatility_stale_and_holdings_gap():
    payload = build_mf_why_better(
        {
            "Fund A": {
                "risk_level": "Very High",
                "volatility_1y": 22,
                "max_drawdown_1y": -21,
                "expense_ratio": 1.7,
                "return_3y": -1,
                "holdings": [],
                "data_quality": {"missing_fields": ["aum"]},
                "source_summary": {"stale": True},
            },
            "Fund B": {
                "risk_level": "Moderate",
                "volatility_1y": 8,
                "max_drawdown_1y": -4,
                "expense_ratio": 0.4,
                "return_3y": 10,
                "holdings": [{"security_name": "Example", "weight_pct": 1}],
                "data_quality": {"missing_fields": []},
                "source_summary": {"stale": False},
            },
        }
    )

    items = payload["risk_analysis"]["items"]
    labels = {(item["entity"], item["label"], item["level"]) for item in items}
    assert ("Fund A", "Official risk label", "High") in labels
    assert ("Fund A", "Volatility", "High") in labels
    assert ("Fund A", "Drawdown", "High") in labels
    assert ("Fund A", "Cost risk", "High") in labels
    assert ("Fund A", "Freshness risk", "Medium") in labels
    assert ("Fund A", "Concentration risk", "Not available") in labels
    assert next(item for item in items if item["label"] == "Concentration risk")["kind"] == "data_gap"
    assert next(item for item in items if item["label"] == "Freshness risk")["kind"] == "risk"


def test_mf_risk_analysis_accepts_positive_drawdown_magnitude():
    payload = build_mf_why_better(
        {
            "Fund A": {
                "max_drawdown_1y": 21,
                "holdings": [{"security_name": "Example", "weight_pct": 1}],
                "data_quality": {"missing_fields": []},
                "source_summary": {"stale": False},
            }
        }
    )

    drawdown = next(item for item in payload["risk_analysis"]["items"] if item["label"] == "Drawdown")
    assert drawdown["level"] == "High"
    assert "21.00%" in drawdown["evidence"]
