from __future__ import annotations

import asyncio
from types import SimpleNamespace

from app.services.asset_resolver import AssetResolution
from app.services.compare_data_service import CompareDataService


class _FakeQuery:
    def __init__(self, root, table_name: str):
        self.root = root
        self.table_name = table_name
        self.eq_filters: list[tuple[str, object]] = []
        self.order_by: list[tuple[str, bool]] = []
        self.limit_value = None

    def select(self, _fields: str, count=None):
        self.root.calls.append((self.table_name, "select"))
        return self

    def eq(self, key: str, value):
        self.eq_filters.append((key, value))
        return self

    def ilike(self, key: str, value):
        return self

    def order(self, key: str, desc=False):
        self.order_by.append((key, bool(desc)))
        return self

    def limit(self, value: int):
        self.limit_value = value
        return self

    def execute(self):
        rows = list(self.root.tables.get(self.table_name, []))
        for key, value in self.eq_filters:
            rows = [row for row in rows if str(row.get(key)) == str(value)]
        for key, desc in reversed(self.order_by):
            rows.sort(key=lambda row: row.get(key) or "", reverse=desc)
        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        return SimpleNamespace(data=rows)


class _FakeSupabase:
    def __init__(self, tables: dict[str, list[dict]]):
        self.tables = tables
        self.calls: list[tuple[str, str]] = []

    def table(self, name: str):
        return _FakeQuery(self, name)


def _resolution(name: str, code: str, amc: str = "HDFC") -> AssetResolution:
    return AssetResolution(
        input=name,
        resolved_name=name,
        asset_type="mutual_fund",
        id=code,
        confidence=0.96,
        coverage_status="supported",
        amc=amc,
        match_reason="test",
    )


def test_compare_service_returns_partial_data_and_benchmark_fallback():
    fake = _FakeSupabase({
        "mutual_fund_core_snapshot": [
            {
                "scheme_code": "101",
                "scheme_name": "HDFC Flexi Cap Fund Direct Growth",
                "amc_name": "HDFC Mutual Fund",
                "category": "Flexi Cap",
                "nav": 100.0,
                "nav_date": "2026-05-31",
                "expense_ratio": 0.75,
                "aum": None,
            }
        ],
        "mutual_fund_nav_history": [
            {"scheme_code": "101", "nav_date": "2026-05-30", "nav": 99.0},
            {"scheme_code": "101", "nav_date": "2026-05-31", "nav": 100.0},
        ],
        "stock_prices_daily": [
            {"symbol": "NIFTY", "date": "2026-05-30", "close": 22000.0},
            {"symbol": "NIFTY", "date": "2026-05-31", "close": 22100.0},
        ],
        "mutual_fund_holdings": [],
        "mutual_fund_sectors": [],
    })
    service = CompareDataService(fake)

    result = asyncio.run(service.build_mutual_fund_compare(
        ["HDFC Flexi Cap"],
        pre_resolutions=[_resolution("HDFC Flexi Cap Fund Direct Growth", "101")],
    ))

    item = result["quant_data"]["comparison"]["HDFC Flexi Cap Fund Direct Growth"]
    assert result["coverage_status"] == "partial"
    assert item["benchmark"] == "NIFTY"
    assert item["benchmark_source"] == "nifty_fallback"
    assert "fund_benchmark" in item["data_quality"]["missing_fields"]
    assert "aum" in item["data_quality"]["missing_fields"]
    assert not any(call[0] == "mfapi" for call in fake.calls)


def test_compare_service_builds_holdings_overlap_from_local_rows():
    fake = _FakeSupabase({
        "mutual_fund_core_snapshot": [
            {
                "scheme_code": "101",
                "scheme_name": "HDFC Flexi Cap Fund Direct Growth",
                "amc_name": "HDFC Mutual Fund",
                "category": "Flexi Cap",
                "benchmark": "NIFTY 500 TRI",
                "nav": 100.0,
                "nav_date": "2026-05-31",
                "expense_ratio": 0.75,
                "aum": 1000,
            },
            {
                "scheme_code": "102",
                "scheme_name": "Parag Parikh Flexi Cap Fund Direct Growth",
                "amc_name": "PPFAS Mutual Fund",
                "category": "Flexi Cap",
                "benchmark": "NIFTY 500 TRI",
                "nav": 200.0,
                "nav_date": "2026-05-31",
                "expense_ratio": 0.65,
                "aum": 2000,
            },
        ],
        "mutual_fund_nav_history": [],
        "stock_prices_daily": [],
        "mutual_fund_holdings": [
            {"scheme_code": "101", "as_of_date": "2026-05-31", "security_name": "HDFC Bank", "isin": "INE040A01034", "sector": "Financials", "weight_pct": 7.0},
            {"scheme_code": "102", "as_of_date": "2026-05-31", "security_name": "HDFC Bank", "isin": "INE040A01034", "sector": "Financials", "weight_pct": 6.0},
        ],
        "mutual_fund_sectors": [],
    })
    service = CompareDataService(fake)

    result = asyncio.run(service.build_mutual_fund_compare(
        ["HDFC Flexi Cap", "Parag Parikh Flexi Cap"],
        pre_resolutions=[
            _resolution("HDFC Flexi Cap Fund Direct Growth", "101", "HDFC"),
            _resolution("Parag Parikh Flexi Cap Fund Direct Growth", "102", "PPFAS"),
        ],
    ))

    overlap = result["quant_data"]["holdings_overlap"]
    assert overlap["coverage_status"] == "available"
    assert overlap["common_holding_count"] == 1
    assert overlap["top_common_holdings"][0]["name"] == "HDFC Bank"


def test_compare_service_loads_family_id_holdings_and_sectors():
    fake = _FakeSupabase({
        "mutual_fund_core_snapshot": [
            {
                "scheme_code": "301",
                "scheme_name": "Nippon India Small Cap Fund - Direct Plan - Growth",
                "amc_name": "Nippon India Mutual Fund",
                "category": "Small Cap",
                "benchmark": "Nifty Smallcap 250 TRI",
                "nav": 180.0,
                "nav_date": "2026-05-31",
                "expense_ratio": 0.67,
                "aum": 59456.65,
            },
        ],
        "mutual_fund_nav_history": [],
        "stock_prices_daily": [],
        "mutual_fund_family_mapping": [{"scheme_code": "301", "family_id": "nippon-small"}],
        "mutual_fund_holdings": [
            {
                "family_id": "nippon-small",
                "as_of_date": "2026-05-31",
                "security_name": "BSE Limited",
                "isin": "INE118H01025",
                "sector": "Capital Markets",
                "weight_pct": 3.32,
                "source": "amc_disclosure",
            }
        ],
        "mutual_fund_sectors": [
            {
                "family_id": "nippon-small",
                "sector": "Capital Markets",
                "weight_pct": 12.5,
                "stock_count": 8,
                "source": "amc_disclosure",
            }
        ],
    })
    service = CompareDataService(fake)

    result = asyncio.run(service.build_mutual_fund_compare(
        ["Nippon India Small Cap"],
        pre_resolutions=[_resolution("Nippon India Small Cap Fund - Direct Plan - Growth", "301", "NIPPON")],
    ))

    item = result["quant_data"]["comparison"]["Nippon India Small Cap Fund - Direct Plan - Growth"]
    assert item["source_summary"]["holdings_as_of_date"] == "2026-05-31"
    assert item["holdings"][0]["security_name"] == "BSE Limited"
    assert item["sector_allocation"][0]["sector"] == "Capital Markets"


def test_compare_service_accepts_axis_percent_nav_holdings_without_isin():
    fake = _FakeSupabase({
        "mutual_fund_core_snapshot": [
            {
                "scheme_code": "201",
                "scheme_name": "Axis Flexi Cap Fund Direct Growth",
                "amc_name": "Axis Mutual Fund",
                "category": "Flexi Cap",
                "benchmark": "Nifty 500 TRI",
                "nav": 75.0,
                "nav_date": "2026-05-31",
                "expense_ratio": 0.70,
                "aum": 12047.3,
                "max_drawdown_1y": -9.1,
            },
            {
                "scheme_code": "101",
                "scheme_name": "HDFC Flexi Cap Fund Direct Growth",
                "amc_name": "HDFC Mutual Fund",
                "category": "Flexi Cap",
                "benchmark": "Nifty 500 TRI",
                "nav": 100.0,
                "nav_date": "2026-05-31",
                "expense_ratio": 0.75,
                "aum": 1000,
                "max_drawdown_1y": -10.5,
            },
        ],
        "mutual_fund_nav_history": [],
        "stock_prices_daily": [],
        "mutual_fund_holdings": [
            {"scheme_code": "201", "as_of_date": "2026-03-01", "security_name": "ICICI Bank", "isin": None, "sector": "Banks", "weight_pct": 8.0, "source": "amc_disclosure"},
            {"scheme_code": "101", "as_of_date": "2026-05-31", "security_name": "ICICI Bank", "isin": "INE090A01021", "sector": "Banks", "weight_pct": 7.0, "source": "amc_disclosure"},
        ],
        "mutual_fund_sectors": [],
    })
    service = CompareDataService(fake)

    result = asyncio.run(service.build_mutual_fund_compare(
        ["Axis Flexi Cap", "HDFC Flexi Cap"],
        downside_focus=True,
        pre_resolutions=[
            _resolution("Axis Flexi Cap Fund Direct Growth", "201", "AXIS"),
            _resolution("HDFC Flexi Cap Fund Direct Growth", "101", "HDFC"),
        ],
    ))

    comparison = result["quant_data"]["comparison"]
    axis_item = comparison["Axis Flexi Cap Fund Direct Growth"]
    assert result["coverage_status"] == "complete"
    assert axis_item["source_summary"]["holdings_as_of_date"] == "2026-03-01"
    assert axis_item["holdings"][0]["isin"] is None
    assert result["quant_data"]["asset_type"] == "mutual_fund"
    assert result["quant_data"]["why_better"]["winner"]


def test_compare_service_builds_fund_items_concurrently():
    import pandas as pd

    class ConcurrentService(CompareDataService):
        def __init__(self):
            super().__init__(_FakeSupabase({}))
            self.active = 0
            self.max_active = 0

        async def _nifty_history_df(self, days: int = 1100):
            return pd.DataFrame()

        def _core_snapshot_row(self, scheme_code):
            return {"scheme_code": scheme_code, "scheme_name": f"Fund {scheme_code}"}

        async def _comparison_item(self, row, resolution, benchmark_hist):
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            await asyncio.sleep(0.01)
            self.active -= 1
            return {
                "scheme_code": str(row["scheme_code"]),
                "name": resolution.resolved_name,
                "return_3y": 10.0,
                "volatility_1y": 12.0,
                "expense_ratio": 0.8,
                "source_summary": {"stale": False, "metadata": "test"},
                "data_quality": {"coverage_status": "complete", "missing_fields": []},
                "holdings": [],
            }

    service = ConcurrentService()
    result = asyncio.run(service.build_mutual_fund_compare(
        ["Fund A", "Fund B"],
        pre_resolutions=[
            _resolution("Fund A", "101", "HDFC"),
            _resolution("Fund B", "102", "PPFAS"),
        ],
    ))

    assert service.max_active == 2
    assert list(result["quant_data"]["comparison"]) == ["Fund A", "Fund B"]


def test_compare_history_uses_stored_cache_without_provider_refresh(monkeypatch):
    from app.services import compare_data_service as module

    calls: list[str] = []

    def stored_history(scheme_code: str):
        calls.append(scheme_code)
        return {
            "ok": True,
            "data": [
                {"scheme_code": scheme_code, "nav_date": "2026-05-30", "nav": 99.0},
                {"scheme_code": scheme_code, "nav_date": "2026-05-31", "nav": 100.0},
            ],
            "cache_status": "stale_cache",
            "stale": True,
        }

    monkeypatch.setattr(module, "get_stored_nav_history", stored_history)
    service = CompareDataService(_FakeSupabase({}))

    frame = asyncio.run(service._mf_history_df("101"))

    assert calls == ["101"]
    assert list(frame["Close"]) == [99.0, 100.0]
