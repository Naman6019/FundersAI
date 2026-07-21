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

    daily_rows = [
        {"nav_date": f"2026-04-{day:02d}", "nav": 100 + day + (day % 3)}
        for day in range(1, 31)
    ] + [{"nav_date": "2026-05-01", "nav": 133}]
    risk_metrics = compute_nav_metrics(daily_rows, risk_free_rate=0.06)
    assert risk_metrics["sharpe_ratio"] is not None
    assert risk_metrics["alpha"] is None
    assert risk_metrics["beta"] is None

    short_metrics = compute_nav_metrics([{"nav_date": "2026-05-10", "nav": 100}])
    assert short_metrics["return_1m"] is None
    assert short_metrics["return_3m"] is None
    assert short_metrics["volatility_1y"] is None


def test_amfi_metadata_source_trace_merges_existing_payload():
    from backend.scripts import sync_mf_metadata

    payload = sync_mf_metadata._merge_official_source_trace(
        {"amc_trace": {"holdings": {"source_document_id": "doc-1"}}},
        "AMFI TER API",
        {"expense_ratio": 0.52, "aum": None},
    )

    assert payload["amc_trace"]["holdings"]["source_document_id"] == "doc-1"
    assert payload["official_source_trace"]["amfi_ter_api"]["fields"] == ["expense_ratio"]


def test_amfi_holdings_tries_next_quarter_after_404(monkeypatch):
    from backend.scripts import sync_mf_metadata

    class _Response:
        status_code = 404

    class _Http404(Exception):
        response = _Response()

    calls = []
    written = {}

    monkeypatch.setattr(
        sync_mf_metadata,
        "parse_amfi_payload_options",
        lambda session: (
            [{"mf_id": "9", "mf_name": "HDFC Mutual Fund"}],
            [
                {"QuarterDate": "2026-01-01T00:00:00"},
                {"QuarterDate": "2025-10-01T00:00:00"},
            ],
        ),
    )

    def fake_get_json(session, path, params=None):
        calls.append(dict(params or {}))
        if params["strMonth"] == "01-Jan-2026":
            raise _Http404()
        return [
            {
                "Scheme_Name": "Fund A",
                "Company_Name": "HDFC Bank Ltd.",
                "MarketValuePercentage": "8.5",
                "ISIN": "INE040A01034",
                "Security_Type": "Equity",
            }
        ]

    def fake_upsert(_supabase, holdings):
        written["holdings"] = holdings
        return len(holdings)

    monkeypatch.setattr(sync_mf_metadata, "amfi_get_json", fake_get_json)
    monkeypatch.setattr(sync_mf_metadata, "upsert_holdings", fake_upsert)

    count = sync_mf_metadata.sync_amfi_holdings_api(
        object(),
        sync_mf_metadata.build_scheme_index([
            {
                "scheme_code": 120503,
                "scheme_name": "Fund A",
                "fund_house": "HDFC Mutual Fund",
                "category": "Equity",
                "sub_category": "Large Cap",
                "nav": 100,
                "nav_date": "2026-05-25",
            }
        ]),
        object(),
    )

    assert count == 1
    assert [call["strMonth"] for call in calls] == ["01-Jan-2026", "01-Oct-2025"]
    assert written["holdings"][0]["as_of_date"] == "2025-10-01"
    assert written["holdings"][0]["security_name"] == "HDFC Bank Ltd."
