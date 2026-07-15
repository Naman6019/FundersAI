from __future__ import annotations

from app.services.fund_similarity_service import FEATURE_VERSION, FundSimilarityService


def _fund(code: str, name: str, *, return_3y: float, volatility: float, drawdown: float, expense: float, aum: float) -> dict:
    return {
        "scheme_code": code,
        "scheme_name": name,
        "amc_name": "Test AMC",
        "category": "Flexi Cap",
        "risk_level": "Very High",
        "return_1m": 1.2,
        "return_3m": 3.4,
        "return_6m": 7.1,
        "return_1y": 12.0,
        "return_3y": return_3y,
        "return_5y": 14.0,
        "volatility_1y": volatility,
        "max_drawdown_1y": drawdown,
        "expense_ratio": expense,
        "aum": aum,
        "alpha": 1.2,
        "beta": 0.95,
        "sharpe_ratio": 1.1,
    }


class _Repository:
    def __init__(self, rows: list[dict]):
        self.rows = rows

    def get_fund_by_scheme_code(self, scheme_code):
        return next((row for row in self.rows if str(row["scheme_code"]) == str(scheme_code)), None)

    def list_core_snapshot_rows(self, *, category=None, limit=5000):
        return [row for row in self.rows if not category or row.get("category") == category][:limit]


def test_similarity_returns_explainable_category_peers():
    target = _fund("101", "Target Flexi Cap", return_3y=15.0, volatility=12.0, drawdown=-10.0, expense=0.60, aum=1000)
    near = _fund("102", "Near Flexi Cap", return_3y=15.2, volatility=12.1, drawdown=-10.2, expense=0.61, aum=1050)
    middle = _fund("103", "Middle Flexi Cap", return_3y=13.0, volatility=14.0, drawdown=-14.0, expense=0.72, aum=3000)
    far = _fund("104", "Far Flexi Cap", return_3y=8.0, volatility=22.0, drawdown=-25.0, expense=1.20, aum=50000)

    result = FundSimilarityService(_Repository([target, near, middle, far])).find_similar("101", limit=3)

    assert result["status"] == "available"
    assert result["feature_version"] == FEATURE_VERSION
    assert result["target"]["cluster"]["member_count"] >= 1
    assert result["peers"][0]["scheme_code"] == "102"
    assert result["peers"][0]["matching_factors"]
    assert all("standardized_distance" in factor for factor in result["peers"][0]["matching_factors"])


def test_similarity_requires_enough_numeric_coverage_and_peers():
    sparse = {"scheme_code": "101", "scheme_name": "Sparse Fund", "category": "Flexi Cap", "return_1y": 10.0}
    result = FundSimilarityService(_Repository([sparse])).find_similar("101")

    assert result["status"] == "insufficient_data"
    assert result["peers"] == []
