from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import patch

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


def test_compare_service_keeps_benchmark_fallback_as_limitation_not_missing_field():
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
    assert "fund_benchmark" not in item["data_quality"]["missing_fields"]
    assert item["data_quality"]["limitations"]
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


def test_compare_service_filters_fragmented_summary_rows_from_holdings():
    fake = _FakeSupabase({
        "mutual_fund_core_snapshot": [
            {
                "scheme_code": "101",
                "scheme_name": "HDFC Flexi Cap Fund Direct Growth",
                "category": "Flexi Cap",
                "benchmark": "NIFTY 500 TRI",
                "nav": 100.0,
                "nav_date": "2026-05-31",
                "expense_ratio": 0.75,
                "aum": 1000,
            }
        ],
        "mutual_fund_nav_history": [],
        "stock_prices_daily": [],
        "mutual_fund_holdings": [
            {"scheme_code": "101", "as_of_date": "2026-05-31", "security_name": "HDFC Bank", "weight_pct": 7.0},
            {"scheme_code": "101", "as_of_date": "2026-05-31", "security_name": "Sub T otal", "weight_pct": 99.0},
            {"scheme_code": "101", "as_of_date": "2026-05-31", "security_name": "Ramco Systems Ltd. Sub Total Nexus Select Trust REIT", "weight_pct": 5.0},
        ],
        "mutual_fund_sectors": [],
    })
    service = CompareDataService(fake)

    result = asyncio.run(service.build_mutual_fund_compare(
        ["HDFC Flexi Cap"],
        pre_resolutions=[_resolution("HDFC Flexi Cap Fund Direct Growth", "101")],
    ))

    holdings = result["quant_data"]["comparison"]["HDFC Flexi Cap Fund Direct Growth"]["holdings"]
    assert [row["security_name"] for row in holdings] == ["HDFC Bank"]


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


def test_compare_summary_carries_business_day_nav_freshness():
    service = CompareDataService(_FakeSupabase({}))
    row = {
        "scheme_code": "301",
        "scheme_name": "Nippon India Small Cap Fund - Direct Plan - Growth",
        "nav": 180.0,
        "nav_date": "2026-07-24",
    }

    with patch(
        "app.services.compare_data_service.assess_nav_freshness",
        return_value={"status": "lagging", "expected_nav_date": "2026-07-27", "missed_business_days": 1},
    ):
        item = service._summary_item(row, _resolution(row["scheme_name"], "301", "NIPPON"))

    assert item["source_summary"] == {
        "metadata": "FundersAI DB",
        "stale": False,
        "status": "lagging",
        "expected_nav_date": "2026-07-27",
        "missed_business_days": 1,
        "nav_date": "2026-07-24",
    }


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
    assert result["coverage_status"] == "partial"
    assert "risk_level" in axis_item["data_quality"]["missing_fields"]
    assert "sectors" in axis_item["data_quality"]["missing_fields"]
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


def test_compare_service_summary_skips_history_holdings_and_sector_reads():
    fake = _FakeSupabase({
        "mutual_fund_core_snapshot": [
            {
                "scheme_code": "101",
                "scheme_name": "HDFC Flexi Cap Fund Direct Growth",
                "category": "Flexi Cap",
                "nav": 100.0,
                "nav_date": "2026-05-31",
                "return_3y": 12.0,
                "volatility_1y": 10.0,
                "max_drawdown_1y": -8.0,
                "expense_ratio": 0.75,
                "aum": 1000,
            },
            {
                "scheme_code": "102",
                "scheme_name": "Parag Parikh Flexi Cap Fund Direct Growth",
                "category": "Flexi Cap",
                "nav": 200.0,
                "nav_date": "2026-05-31",
                "return_3y": 11.0,
                "volatility_1y": 11.0,
                "max_drawdown_1y": -9.0,
                "expense_ratio": 0.65,
                "aum": 2000,
            },
        ],
        "mutual_fund_nav_history": [],
        "stock_prices_daily": [],
        "mutual_fund_holdings": [],
        "mutual_fund_sectors": [],
    })

    result = asyncio.run(CompareDataService(fake).build_mutual_fund_compare_summary(
        ["HDFC Flexi Cap", "Parag Parikh Flexi Cap"],
        pre_resolutions=[
            _resolution("HDFC Flexi Cap Fund Direct Growth", "101", "HDFC"),
            _resolution("Parag Parikh Flexi Cap Fund Direct Growth", "102", "PPFAS"),
        ],
    ))

    assert result["quant_data"]["comparison_data_level"] == "summary"
    assert result["quant_data"]["why_better"]["winner"]["entity_name"] == "HDFC Flexi Cap Fund Direct Growth"
    assert {table for table, _action in fake.calls} == {"mutual_fund_core_snapshot"}


def test_hdfc_118989_vs_nippon_118668_production_acceptance_contract():
    rows = [
        {
            "scheme_code": "118989",
            "scheme_name": "HDFC Mid-Cap Opportunities Fund - Direct Plan - Growth",
            "amc_name": "HDFC Mutual Fund",
            "category": "Mid Cap",
            "nav": 210.0,
            "nav_date": "2026-07-24",
            "return_3y": 19.42,
            "volatility_1y": 16.45,
            "max_drawdown_1y": -39.51,
            "expense_ratio": 0.72,
            "aum": 79474.72,
            "benchmark": "NIFTY Midcap 150 TRI",
            "risk_level": "Very High",
            "fund_manager": "Official AMC manager",
        },
        {
            "scheme_code": "118668",
            "scheme_name": "Nippon India Growth Mid Cap Fund - Direct Plan - Growth Option",
            "amc_name": "Nippon India Mutual Fund",
            "category": "Mid Cap",
            "nav": 330.0,
            "nav_date": "2026-07-24",
            "return_3y": 21.54,
            "volatility_1y": 17.15,
            "max_drawdown_1y": -35.32,
            "expense_ratio": 0.81,
            "aum": 65994.88,
            "benchmark": "NIFTY Midcap 150 TRI",
            "risk_level": "Very High",
            "fund_manager": "Official AMC manager",
        },
    ]
    fake = _FakeSupabase({"mutual_fund_core_snapshot": rows})
    result = asyncio.run(
        CompareDataService(fake).build_mutual_fund_compare_summary(
            [rows[0]["scheme_name"], rows[1]["scheme_name"]],
            pre_resolutions=[
                _resolution(rows[0]["scheme_name"], "118989", "HDFC"),
                _resolution(rows[1]["scheme_name"], "118668", "NIPPON"),
            ],
        )
    )

    comparison = result["quant_data"]["comparison"]
    assert set(comparison) == {rows[0]["scheme_name"], rows[1]["scheme_name"]}
    assert comparison[rows[0]["scheme_name"]]["data_quality"]["missing_fields"] == []
    assert comparison[rows[1]["scheme_name"]]["data_quality"]["missing_fields"] == []
    assert result["coverage_status"] == "complete"


def test_compare_service_uses_precomputed_metrics_without_history_or_benchmark(monkeypatch):
    from app.services import compare_data_service as module
    from app.services.mf_metrics_service import NAV_METRIC_SNAPSHOT_VERSION

    class SnapshotService(CompareDataService):
        async def _nifty_history_df(self, days: int = 1100):
            raise AssertionError("benchmark history loaded")

        async def _mf_history_df(self, scheme_code, days: int = 2200):
            raise AssertionError("fund history loaded")

        async def _load_holdings_and_sectors(self, scheme_code):
            return [], [], None

        def _nav_history_summary(self, scheme_code):
            return {
                "count": 2200,
                "first_nav_date": "2020-01-01",
                "last_nav_date": "2026-07-24",
                "cache_status": "hit",
                "stale": False,
                "supports": {"1Y": True, "3Y": True, "5Y": True},
            }

    fake = _FakeSupabase({
        "mutual_fund_core_snapshot": [
            {
                "scheme_code": "101",
                "scheme_name": "HDFC Flexi Cap Fund Direct Growth",
                "category": "Flexi Cap",
                "nav": 100.0,
                "nav_date": "2026-07-24",
                "return_1y": 14.0,
                "return_3y": 13.0,
                "return_5y": 12.0,
                "volatility_1y": 10.0,
                "max_drawdown_1y": 8.0,
                "sharpe_ratio": 1.1,
                "alpha": 2.4,
                "beta": 0.9,
                "expense_ratio": 0.75,
                "aum": 1000,
                "provider_payload": {
                    "metric_snapshot": {
                        "version": NAV_METRIC_SNAPSHOT_VERSION,
                        "as_of_date": "2026-07-24",
                        "computed_at": "2026-07-25T00:00:00+00:00",
                    }
                },
            }
        ],
    })
    monkeypatch.setattr(
        module,
        "compute_nav_metrics",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("request metrics computed")),
    )

    result = asyncio.run(SnapshotService(fake).build_mutual_fund_compare(
        ["HDFC Flexi Cap"],
        pre_resolutions=[_resolution("HDFC Flexi Cap Fund Direct Growth", "101")],
    ))

    item = result["quant_data"]["comparison"]["HDFC Flexi Cap Fund Direct Growth"]
    assert item["metrics_source"] == "precomputed_snapshot"
    assert item["metrics_as_of_date"] == "2026-07-24"
    assert item["return_3y"] == 13.0
    assert item["sharpe_ratio"] == 1.1
    assert item["beta"] == 0.9


def test_holdings_and_sectors_load_in_parallel_after_one_family_lookup():
    import time

    from app.repositories.mutual_fund_repository import MutualFundRepository

    class ParallelRepository(MutualFundRepository):
        def __init__(self):
            super().__init__(object())
            self.active = 0
            self.max_active = 0
            self.family_calls = 0

        def get_family_id_for_scheme(self, scheme_code):
            self.family_calls += 1
            return "family-101"

        def _delayed(self, result):
            self.active += 1
            self.max_active = max(self.max_active, self.active)
            time.sleep(0.03)
            self.active -= 1
            return result

        def get_latest_holdings_for_resolved_family(self, scheme_code, family_id):
            return self._delayed([{"security_name": "HDFC Bank", "as_of_date": "2026-07-01"}])

        def get_sector_rows_for_resolved_family(self, scheme_code, family_id):
            return self._delayed([{"sector": "Financials", "weight_pct": 30.0}])

    repository = ParallelRepository()
    holdings, sectors, as_of = asyncio.run(
        CompareDataService(repository)._load_holdings_and_sectors("101")
    )

    assert repository.family_calls == 1
    assert repository.max_active == 2
    assert holdings[0]["security_name"] == "HDFC Bank"
    assert sectors[0]["sector"] == "Financials"
    assert as_of == "2026-07-01"


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
