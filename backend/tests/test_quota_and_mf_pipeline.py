from __future__ import annotations

from datetime import datetime, timedelta, timezone


def test_indianapi_quota_guard_blocks_live_calls_when_disabled(monkeypatch):
    from app.services import indianapi_quota_guard

    monkeypatch.setenv("INDIANAPI_ENABLE_LIVE_CALLS", "false")
    monkeypatch.setenv("INDIANAPI_ENABLE_SCHEDULED_SYNC", "true")
    monkeypatch.setattr(indianapi_quota_guard, "get_monthly_request_cost", lambda provider, now=None: 0)
    monkeypatch.setattr(indianapi_quota_guard, "get_daily_request_cost", lambda provider, now=None: 0)

    decision = indianapi_quota_guard.evaluate(scheduled=False)

    assert decision.allowed is False
    assert decision.reason == "live_calls_disabled"


def test_indianapi_quota_guard_blocks_at_reserve(monkeypatch):
    from app.services import indianapi_quota_guard

    monkeypatch.setenv("INDIANAPI_ENABLE_LIVE_CALLS", "true")
    monkeypatch.setenv("INDIANAPI_MONTHLY_LIMIT", "5000")
    monkeypatch.setenv("INDIANAPI_MONTHLY_RESERVE", "500")
    monkeypatch.setattr(indianapi_quota_guard, "get_monthly_request_cost", lambda provider, now=None: 4500)
    monkeypatch.setattr(indianapi_quota_guard, "get_daily_request_cost", lambda provider, now=None: 12)

    decision = indianapi_quota_guard.evaluate(scheduled=False)

    assert decision.allowed is False
    assert decision.reason == "reserve_protected"
    assert decision.remaining_safe == 0


def test_indianapi_service_uses_fresh_cache_first(monkeypatch):
    from app.services import indianapi_service

    now = datetime.now(timezone.utc).isoformat()

    monkeypatch.setattr(
        indianapi_service,
        "_read_generic_cache",
        lambda endpoint, cache_key, current, allow_stale: {"response_json": {"value": 1}, "fetched_at": now} if not allow_stale else None,
    )

    result = indianapi_service.get_stock_research_profile("TCS")

    assert result["ok"] is True
    assert result["source"] == "cache"
    assert result["stale"] is False
    assert result["data"] == {"value": 1}


def test_indianapi_service_returns_stale_cache_when_quota_blocks(monkeypatch):
    from app.services import indianapi_quota_guard
    from app.services import indianapi_service

    stale_at = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()

    monkeypatch.setenv("INDIANAPI_ENABLED", "true")
    monkeypatch.setattr(
        indianapi_service,
        "_read_generic_cache",
        lambda endpoint, cache_key, current, allow_stale: None
        if not allow_stale
        else {"response_json": {"cached": True}, "fetched_at": stale_at},
    )
    monkeypatch.setattr(indianapi_service, "_endpoint_feature_disabled", lambda endpoint: False)
    monkeypatch.setattr(indianapi_service, "_disabled_until", lambda endpoint, now: None)
    monkeypatch.setattr(
        indianapi_service,
        "evaluate_quota",
        lambda scheduled=False, now=None: indianapi_quota_guard.QuotaDecision(
            allowed=False,
            reason="reserve_protected",
            monthly_limit=5000,
            monthly_reserve=500,
            scheduled_budget=4000,
            month_used=4700,
            day_used=50,
            remaining_total=300,
            remaining_safe=0,
            live_calls_enabled=True,
            scheduled_sync_enabled=True,
        ),
    )

    result = indianapi_service.get_stock_research_profile("RELIANCE")

    assert result["ok"] is True
    assert result["stale"] is True
    assert result["data"] == {"cached": True}
    assert "quota guard" in result.get("warning", "").lower()


def test_indianapi_service_does_not_call_client_when_quota_blocked(monkeypatch):
    from app.services import indianapi_quota_guard
    from app.services import indianapi_service

    monkeypatch.setenv("INDIANAPI_ENABLED", "true")
    monkeypatch.setattr(indianapi_service, "_read_generic_cache", lambda *args, **kwargs: None)
    monkeypatch.setattr(indianapi_service, "_endpoint_feature_disabled", lambda endpoint: False)
    monkeypatch.setattr(indianapi_service, "_disabled_until", lambda endpoint, now: None)
    monkeypatch.setattr(
        indianapi_service,
        "evaluate_quota",
        lambda scheduled=False, now=None: indianapi_quota_guard.QuotaDecision(
            allowed=False,
            reason="scheduled_budget_reached",
            monthly_limit=5000,
            monthly_reserve=500,
            scheduled_budget=4000,
            month_used=4100,
            day_used=40,
            remaining_total=900,
            remaining_safe=400,
            live_calls_enabled=True,
            scheduled_sync_enabled=True,
        ),
    )

    called = {"value": False}

    class FailIfConstructed:
        def __init__(self):
            called["value"] = True
            raise AssertionError("IndianAPIClient should not be called when quota blocks")

    monkeypatch.setattr(indianapi_service, "IndianAPIClient", FailIfConstructed)

    result = indianapi_service.get_stock_research_profile("INFY")

    assert called["value"] is False
    assert result["ok"] is False
    assert result["error"]["code"] == "quota_guard_blocked"


def test_provider_usage_dashboard_aggregation(monkeypatch):
    from app.services import provider_usage

    now = datetime.now(timezone.utc)
    rows = [
        {"endpoint": "stock", "request_cost": 1, "success": True, "cache_hit": False, "created_at": now.isoformat(), "status_code": 200, "error_message": None},
        {"endpoint": "stock", "request_cost": 0, "success": True, "cache_hit": True, "created_at": now.isoformat(), "status_code": 200, "error_message": None},
        {"endpoint": "historical_data", "request_cost": 1, "success": False, "cache_hit": False, "created_at": now.isoformat(), "status_code": 403, "error_message": "blocked"},
    ]

    monkeypatch.setattr(provider_usage, "get_usage_rows", lambda provider, start, end, limit=10000: rows)

    summary = provider_usage.build_usage_dashboard("indianapi", now=now)

    assert summary["month_request_cost"] == 2
    assert summary["cache_hit_ratio"] == 0.3333
    assert summary["usage_by_endpoint"]["stock"]["calls"] == 2
    assert len(summary["recent_failures"]) == 1


def test_mfapi_normalization(monkeypatch):
    from app.services import mfapi_service

    def fake_request(path, params=None, scheme_code=None):
        if path == "/mf":
            return {"ok": True, "data": {"data": [{"schemeCode": "120503", "schemeName": "Fund A", "isinGrowth": "INF123"}]}}
        if path.endswith("/latest"):
            return {
                "ok": True,
                "data": {
                    "meta": {"scheme_name": "Fund A", "fund_house": "AMC A", "scheme_category": "Equity", "scheme_type": "Open Ended"},
                    "data": [{"date": "10-05-2026", "nav": "123.45"}],
                },
            }
        if path.startswith("/mf/"):
            return {"ok": True, "data": {"data": [{"date": "09-05-2026", "nav": "120.00"}, {"date": "10-05-2026", "nav": "123.45"}]}}
        return {"ok": False, "error": "unknown", "data": None}

    monkeypatch.setattr(mfapi_service, "_request", fake_request)

    listed = mfapi_service.list_schemes()
    latest = mfapi_service.get_latest_nav("120503")
    history = mfapi_service.get_nav_history("120503")

    assert listed["ok"] is True
    assert listed["data"][0]["scheme_code"] == "120503"
    assert latest["data"]["nav"] == 123.45
    assert latest["data"]["nav_date"] == "2026-05-10"
    assert history["data"][0]["scheme_code"] == "120503"


def test_amfi_nav_core_snapshot_preserves_existing_provider_payload():
    from backend.scripts import sync_mf

    row = sync_mf._build_core_snapshot_row(
        {"scheme_code": 120503, "scheme_name": "Fund A", "nav": 123.45, "nav_date": "2026-05-10"},
        {
            "data_source": "mfapi+AMFI TER API",
            "provider_payload": {"official_source_trace": {"amfi_ter_api": {"fields": ["expense_ratio"]}}},
        },
    )

    assert row["data_source"] == "mfapi+AMFI TER API+amfi_navall"
    assert row["provider_payload"]["official_source_trace"]["amfi_ter_api"]["fields"] == ["expense_ratio"]


def test_mfapi_nav_sync_preserves_equal_or_fresher_existing_nav():
    from app.jobs import sync_mf_nav

    nav, nav_date = sync_mf_nav._select_nav(
        {"nav": 124.0, "nav_date": "2026-05-11"},
        {"nav": 123.0, "nav_date": "2026-05-10"},
    )

    assert nav == 124.0
    assert nav_date == "2026-05-11"


def test_mfdata_enrichment_normalization(monkeypatch):
    from app.services import mfdata_service

    def fake_request(path, params=None, scheme_code=None):
        if path == "/schemes/120503":
            return {
                "ok": True,
                "data": {
                    "status": "success",
                    "data": {
                        "scheme_code": 120503,
                        "scheme_name": "Fund A",
                        "amc": "AMC A",
                        "category": "Flexi Cap",
                        "nav": 123.45,
                        "nav_date": "2026-05-10",
                        "aum_cr": 1000,
                        "expense_ratio": 0.5,
                        "returns": {"1y": {"value": 12.3}},
                        "ratios": {"beta": 0.9, "sharpe": 1.1},
                        "family_id": 99,
                    },
                },
            }
        if path == "/families/99/holdings":
            return {
                "ok": True,
                "data": {
                    "status": "success",
                    "data": {
                        "month": "2026-04",
                        "equity": [{"name": "HDFC Bank Ltd.", "sector": "Financial Services", "weight_pct": 8.5}],
                    },
                },
            }
        return {"ok": False, "error": "unknown", "data": None}

    monkeypatch.setattr(mfdata_service, "_request", fake_request)

    details = mfdata_service.get_scheme_details("120503")
    holdings = mfdata_service.get_family_holdings(99, scheme_code="120503")

    assert details["data"]["scheme_code"] == "120503"
    assert details["data"]["aum"] == 1000
    assert details["data"]["return_1y"] == 12.3
    assert details["data"]["beta"] == 0.9
    assert holdings["data"][0]["as_of_date"] == "2026-04-01"
    assert holdings["data"][0]["security_name"] == "HDFC Bank Ltd."


def test_mf_metrics_compute_and_null_safety():
    from app.services.mf_metrics_service import compute_nav_metrics

    rows = [
        {"nav_date": "2021-05-10", "nav": 100},
        {"nav_date": "2022-05-10", "nav": 110},
        {"nav_date": "2023-05-10", "nav": 120},
        {"nav_date": "2024-05-10", "nav": 132},
        {"nav_date": "2025-05-10", "nav": 145},
        {"nav_date": "2026-05-10", "nav": 160},
    ]
    metrics = compute_nav_metrics(rows)

    assert metrics["return_1y"] is not None
    assert metrics["return_3y"] is not None
    assert metrics["return_5y"] is not None
    assert metrics["alpha"] is None
    assert metrics["beta"] is None
    assert metrics["sharpe_ratio"] is None

    short_metrics = compute_nav_metrics([{"nav_date": "2026-05-10", "nav": 100}])
    assert short_metrics["return_1m"] is None
    assert short_metrics["return_3m"] is None
    assert short_metrics["volatility_1y"] is None


def test_mf_enrichment_merge_preserves_nav_owned_fields_and_amc_trace():
    from app.jobs import sync_mf_enrichment

    existing = {
        "scheme_code": "120503",
        "nav": 123.45,
        "nav_date": "2026-05-10",
        "return_1y": 10.2,
        "expense_ratio": None,
        "provider_payload": {"amc_trace": {"holdings": {"source_document_id": "doc-1"}}, "legacy": True},
        "data_source": "mfapi+amc_disclosure",
    }
    incoming = {
        "scheme_code": "120503",
        "nav": 111.11,
        "nav_date": "2026-05-01",
        "return_1y": 2.0,
        "expense_ratio": 0.52,
        "provider_payload": {"family_id": 99},
        "data_source": "mfdata",
    }

    merged = sync_mf_enrichment._merge_snapshot(existing, incoming)

    assert merged["nav"] == 123.45
    assert merged["nav_date"] == "2026-05-10"
    assert merged["return_1y"] == 10.2
    assert merged["expense_ratio"] == 0.52
    assert merged["provider_payload"]["amc_trace"]["holdings"]["source_document_id"] == "doc-1"
    assert merged["provider_payload"]["family_id"] == 99
    assert merged["data_source"] == "mfapi+amc_disclosure+mfdata"


def test_mfdata_fallback_does_not_overwrite_existing_enrichment_fields():
    from app.jobs import sync_mf_enrichment

    existing = {
        "scheme_code": "120503",
        "scheme_name": "Fund A",
        "aum": 1000,
        "expense_ratio": 0.52,
        "benchmark": "Nifty 500 TRI",
        "data_source": "mfapi+AMFI TER API+AMFI AUM API",
        "provider_payload": {},
    }
    incoming = {
        "scheme_code": "120503",
        "scheme_name": "Fund A New",
        "aum": 900,
        "expense_ratio": 0.75,
        "benchmark": "Other Index",
        "fund_manager": "Jane Doe",
        "data_source": "mfdata",
        "provider_payload": {"family_id": 99},
    }

    merged = sync_mf_enrichment._merge_snapshot(existing, incoming)

    assert merged["scheme_name"] == "Fund A"
    assert merged["aum"] == 1000
    assert merged["expense_ratio"] == 0.52
    assert merged["benchmark"] == "Nifty 500 TRI"
    assert merged["fund_manager"] == "Jane Doe"


def test_amfi_metadata_source_trace_merges_existing_payload():
    from backend.scripts import sync_mf_metadata

    payload = sync_mf_metadata._merge_official_source_trace(
        {"amc_trace": {"holdings": {"source_document_id": "doc-1"}}},
        "AMFI TER API",
        {"expense_ratio": 0.52, "aum": None},
    )

    assert payload["amc_trace"]["holdings"]["source_document_id"] == "doc-1"
    assert payload["official_source_trace"]["amfi_ter_api"]["fields"] == ["expense_ratio"]
