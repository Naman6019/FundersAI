import pytest
from fastapi import HTTPException


class _FakeResponse:
    def __init__(self, data=None, count=None):
        self.data = data or []
        self.count = count


class _FakeQuery:
    def __init__(self, table: str, rows):
        self.table = table
        self.rows = rows
        self.filters = {}
        self.order_field = None
        self.order_desc = False
        self.limit_value = None
        self.count_requested = False
        self.ilike_filters = {}

    def select(self, _fields, count=None):
        self.count_requested = count == "exact"
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def ilike(self, key, pattern):
        self.ilike_filters[key] = pattern
        return self

    def limit(self, value):
        self.limit_value = value
        return self

    def order(self, field, desc=False):
        self.order_field = field
        self.order_desc = desc
        return self

    def execute(self):
        if self.table == "mutual_fund_core_snapshot":
            data = list(self.rows)
            pattern = self.ilike_filters.get("scheme_name")
            if pattern:
                tokens = [token for token in pattern.lower().split("%") if token]
                data = [
                    row for row in data
                    if all(token in str(row.get("scheme_name", "")).lower() for token in tokens)
                ]
            if self.limit_value is not None:
                data = data[: self.limit_value]
            return _FakeResponse(data=data)

        if self.table == "mutual_fund_nav_history":
            code = self.filters.get("scheme_code")
            data = list(self.rows.get(code, []))

            if self.count_requested:
                return _FakeResponse(data=[], count=len(data))

            if self.order_field == "nav_date":
                data.sort(key=lambda row: row.get("nav_date", ""), reverse=self.order_desc)

            if self.limit_value is not None:
                data = data[: self.limit_value]
            return _FakeResponse(data=data)

        return _FakeResponse(data=[])


class _FakeSupabase:
    def __init__(self, core_rows, nav_rows_by_scheme):
        self.core_rows = core_rows
        self.nav_rows_by_scheme = nav_rows_by_scheme

    def table(self, name):
        if name == "mutual_fund_core_snapshot":
            return _FakeQuery(name, self.core_rows)
        if name == "mutual_fund_nav_history":
            return _FakeQuery(name, self.nav_rows_by_scheme)
        return _FakeQuery(name, [])


def test_require_admin_key_rejects_wrong_key(monkeypatch):
    from app import main as app_main

    monkeypatch.setenv("MF_INTERNAL_ADMIN_KEY", "expected-secret")
    with pytest.raises(HTTPException) as exc:
        app_main._require_admin_key("wrong-secret")
    assert exc.value.status_code == 403


def test_admin_mf_resolver_debug_response_shape(monkeypatch):
    from app import main as app_main

    monkeypatch.setenv("MF_INTERNAL_ADMIN_KEY", "expected-secret")

    core_rows = [
        {
            "scheme_code": "1001",
            "scheme_name": "ICICI Prudential Multi Asset Fund Direct Growth",
            "amc_name": "ICICI Prudential Mutual Fund",
            "category": "Hybrid",
            "sub_category": "Multi Asset Allocation",
            "plan_type": "Direct",
            "option_type": "Growth",
        },
        {
            "scheme_code": "1002",
            "scheme_name": "ICICI Prudential Passive Multi Asset Fund of Funds Direct Growth",
            "amc_name": "ICICI Prudential Mutual Fund",
            "category": "FoF",
            "sub_category": "Passive",
            "plan_type": "Direct",
            "option_type": "Growth",
        },
    ]

    nav_rows_by_scheme = {
        1001: [
            {"nav_date": "2023-01-02"},
            {"nav_date": "2026-05-18"},
        ] * 600,
        1002: [
            {"nav_date": "2026-05-16"},
            {"nav_date": "2026-05-17"},
            {"nav_date": "2026-05-18"},
        ],
    }

    monkeypatch.setattr(app_main, "supabase", _FakeSupabase(core_rows, nav_rows_by_scheme))

    payload = app_main.admin_mf_resolver_debug(
        query="ICICI Multi Asset",
        horizon="3Y",
        limit=5,
        x_admin_key="expected-secret",
    )

    assert payload["input_query"] == "ICICI Multi Asset"
    assert "selected_candidate" in payload
    assert "top_candidates" in payload
    assert payload["scoring_breakdown"]["horizon"] == "3Y"
    assert payload["selected_candidate"]["scheme_code"] == "1001"
    assert payload["top_candidates"][0]["selected"] is True
    assert "penalty_notes" in payload["top_candidates"][0]

