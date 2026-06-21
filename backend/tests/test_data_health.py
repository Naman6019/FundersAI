from __future__ import annotations

from types import SimpleNamespace


class _FakeQuery:
    def __init__(self, root, table_name: str):
        self.root = root
        self.table_name = table_name
        self.eq_filters = {}
        self.order_field = None
        self.order_desc = False
        self.limit_value = None
        self.count_requested = False

    def select(self, _fields: str, count=None):
        self.count_requested = count == "exact"
        return self

    def eq(self, key: str, value):
        self.eq_filters[key] = value
        return self

    def order(self, field: str, desc: bool = False):
        self.order_field = field
        self.order_desc = desc
        return self

    def limit(self, value: int):
        self.limit_value = value
        return self

    def execute(self):
        rows = list(self.root.tables.get(self.table_name, []))
        for key, value in self.eq_filters.items():
            rows = [row for row in rows if str(row.get(key)) == str(value)]
        if self.order_field:
            rows.sort(key=lambda row: str(row.get(self.order_field) or ""), reverse=self.order_desc)
        count = len(rows) if self.count_requested else None
        if self.limit_value is not None:
            rows = rows[: self.limit_value]
        return SimpleNamespace(data=rows, count=count)


class _FakeSupabase:
    def __init__(self, tables: dict[str, list[dict]]):
        self.tables = tables

    def table(self, name: str):
        return _FakeQuery(self, name)


def test_data_health_counts_aum_and_ter_outside_newest_nav_sample(monkeypatch):
    from app.services import admin_service as app_main

    nav_only_rows = [
        {
            "scheme_code": str(index),
            "amc_name": "Other AMC",
            "nav_date": "2026-06-04",
            "last_updated": f"2026-06-08T00:{index % 60:02d}:00+00:00",
            "aum": None,
            "expense_ratio": None,
            "volatility_1y": 1.0,
            "max_drawdown_1y": -2.0,
        }
        for index in range(301)
    ]
    enriched_rows = [
        {
            "scheme_code": "120503",
            "amc_name": "HDFC Mutual Fund",
            "nav_date": "2026-05-01",
            "last_updated": "2026-05-01T00:00:00+00:00",
            "aum": 1000.0,
            "expense_ratio": None,
        },
        {
            "scheme_code": "120504",
            "amc_name": "ICICI Prudential Mutual Fund",
            "nav_date": "2026-05-01",
            "last_updated": "2026-05-02T00:00:00+00:00",
            "aum": None,
            "expense_ratio": 0.61,
        },
        {
            "scheme_code": "120505",
            "scheme_name": "Parag Parikh Flexi Cap Fund",
            "amc_name": "PPFAS Mutual Fund",
            "nav_date": "2026-05-01",
            "last_updated": "2026-05-03T00:00:00+00:00",
            "aum": 500.0,
            "expense_ratio": 0.52,
            "benchmark": "Nifty 500 TRI",
            "risk_level": "Very High",
        },
        {
            "scheme_code": "120506",
            "scheme_name": "Axis Flexi Cap Fund",
            "amc_name": "Axis Mutual Fund",
            "nav_date": "2026-05-01",
            "last_updated": "2026-05-04T00:00:00+00:00",
            "aum": 700.0,
            "expense_ratio": 0.7,
            "benchmark": "Nifty 500 TRI",
            "risk_level": "Very High",
        },
    ]
    fake = _FakeSupabase(
        {
            "mutual_fund_core_snapshot": nav_only_rows + enriched_rows,
            "mf_raw_documents": [
                {
                    "id": "doc-1",
                    "amc_code": "AXIS",
                    "source_document_type": "factsheet",
                    "parse_status": "parsed",
                    "report_month": "2026-03-01",
                    "downloaded_at": "2026-06-01T00:00:00+00:00",
                    "parsed_at": "2026-06-01T00:00:00+00:00",
                }
            ],
            "mf_parse_review_queue": [
                {"amc_code": "AXIS", "status": "pending_review", "report_month": "2026-03-01"}
            ],
        }
    )
    app_main._current_admin_repository.set(fake)

    payload = app_main.data_health()

    metric = next(item for item in payload["metrics"] if item["label"] == "AUM / TER")
    assert metric["status"] != "Missing"
    assert "AUM rows=3" in metric["note"]
    assert "TER rows=3" in metric["note"]
    assert "both=2" in metric["note"]

    axis_quality = next(item for item in payload["amc_parser_quality"] if item["amc"] == "AXIS")
    assert axis_quality["latest_factsheet_month"] == "2026-03"
    assert axis_quality["latest_holdings_month"] == "2026-03"
    assert axis_quality["ter_coverage"] == 1.0
    assert axis_quality["benchmark_coverage"] == 1.0
    assert axis_quality["risk_label_coverage"] == 1.0
    assert axis_quality["parse_review_count"] == 1
    assert "% of NAV" in axis_quality["holdings_source_note"]
    assert any(item["amc"] == "NIPPON" for item in payload["amc_parser_quality"])
