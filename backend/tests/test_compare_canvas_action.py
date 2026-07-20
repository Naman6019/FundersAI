from __future__ import annotations

import asyncio
from datetime import date, timedelta
from types import SimpleNamespace


class _FakeQuery:
    def __init__(self, root, table_name: str):
        self.root = root
        self.table_name = table_name
        self.ilike_filters: list[tuple[str, str]] = []
        self.eq_filters: list[tuple[str, object]] = []
        self.order_by: list[tuple[str, bool]] = []
        self.limit_value: int | None = None

    def select(self, _fields: str, count=None):
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
            rows = [row for row in rows if all(needle in str(row.get(key) or "").lower() for needle in needles)]
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

    def table(self, name: str):
        return _FakeQuery(self, name)


def _nav_rows(scheme_code: str) -> list[dict]:
    start = date(2025, 1, 1)
    return [
        {"scheme_code": scheme_code, "nav_date": (start + timedelta(days=i)).isoformat(), "nav": 100 + i}
        for i in range(260)
    ]


def test_compare_canvas_action_opens_for_hdfc_mid_cpa_typo(monkeypatch):
    from app.services import chat_service as main

    fake = _FakeSupabase(
        {
            "mutual_fund_core_snapshot": [
                {
                    "scheme_code": "axis-idcw",
                    "scheme_name": "Axis Large Cap Fund - Direct Plan - IDCW",
                    "amc_name": "Axis Mutual Fund",
                    "nav": 100,
                    "nav_date": "2026-06-01",
                    "expense_ratio": 1.0,
                    "aum": 1000,
                },
                {
                    "scheme_code": "axis-growth",
                    "scheme_name": "Axis Large Cap Fund - Direct Plan - Growth",
                    "amc_name": "Axis Mutual Fund",
                    "nav": 110,
                    "nav_date": "2026-06-01",
                    "expense_ratio": 0.9,
                    "aum": 1200,
                },
                {
                    "scheme_code": "hdfc-mid",
                    "scheme_name": "HDFC Mid-Cap Opportunities Fund - Direct Plan - Growth",
                    "amc_name": "HDFC Mutual Fund",
                    "nav": 130,
                    "nav_date": "2026-06-01",
                    "expense_ratio": 0.8,
                    "aum": 1400,
                },
            ],
            "mutual_funds": [],
            "mutual_fund_nav_history": _nav_rows("axis-growth") + _nav_rows("hdfc-mid"),
            "mutual_fund_holdings": [],
            "mutual_fund_sectors": [],
            "stock_prices_daily": [
                {"symbol": "NIFTY", "date": "2026-06-01", "close": 23000},
                {"symbol": "NIFTY", "date": "2026-05-31", "close": 22900},
            ],
        }
    )

    async def fake_synthesis_response(*_args, **_kwargs):
        return "ok"

    monkeypatch.setattr(main, "synthesis_response", fake_synthesis_response)
    monkeypatch.setattr(main, "fetch_news", lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("news fetch called")))

    req = main.ChatRequest(
        query="Compare Axis Large cap and Hdfc mid cpa",
        asset_type="mutual_fund",
        comparison_view_mode="canvas",
    )
    response = asyncio.run(main.ChatService(fake).handle_chat(req))

    assert response["system_action"]["type"] == "COMPARE"
    assert response["system_action"]["ids"] == ["axis-growth", "hdfc-mid"]
    assert response["debug_intent"]["compare_entities"] == [
        "Axis Large Cap Fund - Direct Plan - Growth",
        "HDFC Mid-Cap Opportunities Fund - Direct Plan - Growth",
    ]
    assert response["reasoning_summary"]["title"] == "Reasoning summary"
    assert [step["label"] for step in response["reasoning_summary"]["steps"]] == ["Resolved", "Compared", "View"]
    assert response["reasoning_summary"]["steps"][2]["detail"] == "Opened canvas for the full comparison table."
