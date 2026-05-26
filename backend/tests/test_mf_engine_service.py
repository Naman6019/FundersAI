from __future__ import annotations


def test_mf_engine_normalizes_scheme_factsheet_holdings_and_nav(monkeypatch):
    from app.services import mf_engine_service

    def fake_cached_request(endpoint_name, path, params=None, ttl_policy="mutual_fund_enrichment"):
        if endpoint_name == "scheme":
            return {
                "ok": True,
                "data": {
                    "list": [
                        {
                            "id": 77,
                            "schemeCode": "120503",
                            "schemeName": "Fund A - Direct Plan - Growth",
                            "amc": "AMC A",
                            "isinGrowth": "INF123",
                            "aumCr": "1,000.5",
                            "expenseRatio": "0.52%",
                            "returns": {"1y": {"value": "12.3"}},
                        }
                    ],
                    "total": 1,
                },
                "error": None,
            }
        if endpoint_name == "scheme_factsheet":
            return {
                "ok": True,
                "data": {
                    "scheme_name": "Fund A - Direct Plan - Growth",
                    "month": "Apr 2026",
                    "benchmark": "Nifty 500 TRI",
                    "fundManager": "Jane Doe",
                },
                "error": None,
            }
        if endpoint_name == "scheme_holding_changes":
            return {
                "ok": True,
                "data": {
                    "list": [
                        {
                            "holdingName": "HDFC Bank Ltd.",
                            "isin": "INE040A01034",
                            "sector": "Financial Services",
                            "weight": "8.5",
                            "date": "2026-04-30",
                        }
                    ]
                },
                "error": None,
            }
        if endpoint_name == "nav":
            return {"ok": True, "data": {"data": [{"date": "2026-05-10", "nav": "123.45"}]}, "error": None}
        return {"ok": False, "data": None, "error": "unknown"}

    monkeypatch.setattr(mf_engine_service, "_cached_request", fake_cached_request)

    schemes = mf_engine_service.list_schemes()
    factsheet = mf_engine_service.get_factsheet("INF123")
    holdings = mf_engine_service.get_holding_changes(77)
    nav = mf_engine_service.get_nav(77)

    assert schemes["data"][0]["provider_scheme_id"] == "77"
    assert schemes["data"][0]["scheme_code"] == "120503"
    assert schemes["data"][0]["aum"] == 1000.5
    assert schemes["data"][0]["return_1y"] == 12.3
    assert factsheet["data"]["report_month"] == "2026-04-01"
    assert factsheet["data"]["benchmark"] == "Nifty 500 TRI"
    assert holdings["data"][0]["security_name"] == "HDFC Bank Ltd."
    assert holdings["data"][0]["weight_pct"] == 8.5
    assert nav["data"][0]["nav_date"] == "2026-05-10"
    assert nav["data"][0]["nav"] == 123.45


def test_mf_engine_merge_preserves_existing_mfapi_nav():
    from app.jobs import sync_mf_engine_enrichment

    existing = {
        "scheme_code": "120503",
        "scheme_name": "Fund A",
        "nav": 123.45,
        "nav_date": "2026-05-10",
        "data_source": "mfapi",
        "provider_payload": {"mfapi": True},
    }
    incoming = {
        "scheme_code": "120503",
        "scheme_name": "Fund A - Direct Plan - Growth",
        "nav": 111.11,
        "nav_date": "2026-05-01",
        "expense_ratio": 0.52,
        "aum": 1000,
        "provider_scheme_id": "77",
        "provider_payload": {"id": 77},
    }

    merged = sync_mf_engine_enrichment._merge_core_snapshot(existing, incoming)

    assert merged["nav"] == 123.45
    assert merged["nav_date"] == "2026-05-10"
    assert merged["expense_ratio"] == 0.52
    assert merged["aum"] == 1000
    assert merged["data_source"] == "mfapi+mf_engine"
    assert merged["provider_payload"]["mf_engine_trace"]["scheme"]["provider_scheme_id"] == "77"
