from __future__ import annotations

import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace

from app.services import mfapi_service
from app.services import fund_service


NOW = datetime(2026, 7, 17, 12, 0, tzinfo=timezone.utc)


def _row(*, fetched_delta: timedelta = timedelta(hours=-1), expires_delta: timedelta = timedelta(hours=1)):
    return {
        "scheme_code": "100",
        "payload": [{"scheme_code": "100", "nav_date": "2026-07-16", "nav": 10.0, "data_source": "mfapi"}],
        "point_count": 1,
        "first_nav_date": "2026-07-16",
        "last_nav_date": "2026-07-16",
        "source": "mfapi",
        "fetched_at": (NOW + fetched_delta).isoformat(),
        "expires_at": (NOW + expires_delta).isoformat(),
        "updated_at": (NOW + fetched_delta).isoformat(),
    }


def test_fresh_cache_hit_does_not_call_provider(monkeypatch):
    monkeypatch.setattr(mfapi_service, "_utc_now", lambda: NOW)
    monkeypatch.setattr(mfapi_service, "_read_cache_row", lambda *_args, **_kwargs: _row())
    monkeypatch.setattr(mfapi_service, "_record_cache_usage", lambda *_args: None)
    monkeypatch.setattr(mfapi_service, "get_nav_history", lambda *_args: (_ for _ in ()).throw(AssertionError("provider called")))

    result = mfapi_service.get_cached_nav_history("100")

    assert result["ok"] is True
    assert result["cache_status"] == "hit"
    assert result["point_count"] == 1


def test_expired_cache_refresh_normalizes_deduplicates_and_sorts(monkeypatch):
    monkeypatch.setattr(mfapi_service, "_utc_now", lambda: NOW)
    monkeypatch.setattr(mfapi_service, "_read_cache_row", lambda *_args, **_kwargs: _row(expires_delta=timedelta(seconds=-1)))
    monkeypatch.setattr(
        mfapi_service,
        "get_nav_history",
        lambda *_args: {
            "ok": True,
            "data": [
                {"date": "17-07-2026", "nav": "12"},
                {"nav_date": "2026-07-15", "nav": "10"},
                {"date": "17-07-2026", "nav": "12.5"},
                {"date": "bad", "nav": "9"},
            ],
        },
    )
    monkeypatch.setattr(mfapi_service, "supabase", None)

    result = mfapi_service.get_cached_nav_history("100")

    assert result["cache_status"] == "refreshed"
    assert [(row["nav_date"], row["nav"]) for row in result["data"]] == [
        ("2026-07-15", 10.0),
        ("2026-07-17", 12.5),
    ]
    assert result["point_count"] == 2


def test_missing_cache_and_invalid_provider_response_fails_without_write(monkeypatch):
    monkeypatch.setattr(mfapi_service, "_utc_now", lambda: NOW)
    monkeypatch.setattr(mfapi_service, "_read_cache_row", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(mfapi_service, "get_nav_history", lambda *_args: {"ok": True, "data": [{"date": "bad", "nav": "x"}]})
    monkeypatch.setattr(mfapi_service, "_upsert_cache", lambda *_args: (_ for _ in ()).throw(AssertionError("cache overwritten")))

    result = mfapi_service.get_cached_nav_history("100")

    assert result["ok"] is False
    assert result["error"]["code"] == "nav_provider_unavailable"
    assert result["cache_status"] == "miss"


def test_provider_failure_serves_cache_within_stale_window(monkeypatch):
    monkeypatch.setattr(mfapi_service, "_utc_now", lambda: NOW)
    monkeypatch.setattr(mfapi_service, "_read_cache_row", lambda *_args, **_kwargs: _row(fetched_delta=timedelta(days=-2), expires_delta=timedelta(days=-1)))
    monkeypatch.setattr(mfapi_service, "get_nav_history", lambda *_args: {"ok": False, "data": [], "error": "outage"})
    monkeypatch.setattr(mfapi_service, "_record_cache_usage", lambda *_args: None)

    result = mfapi_service.get_cached_nav_history("100")

    assert result["ok"] is True
    assert result["stale"] is True
    assert result["cache_status"] == "stale_fallback"


def test_provider_failure_rejects_cache_older_than_stale_window(monkeypatch):
    monkeypatch.setattr(mfapi_service, "_utc_now", lambda: NOW)
    monkeypatch.setattr(mfapi_service, "_read_cache_row", lambda *_args, **_kwargs: _row(fetched_delta=timedelta(days=-8), expires_delta=timedelta(days=-7)))
    monkeypatch.setattr(mfapi_service, "get_nav_history", lambda *_args: {"ok": False, "data": [], "error": "outage"})

    result = mfapi_service.get_cached_nav_history("100")

    assert result["ok"] is False
    assert result["cache_status"] == "stale_too_old"
    assert result["data"] == []


def test_summary_is_metadata_only(monkeypatch):
    row = _row()
    row.pop("payload")
    monkeypatch.setattr(mfapi_service, "_utc_now", lambda: NOW)
    monkeypatch.setattr(mfapi_service, "_read_cache_row", lambda *_args, **kwargs: row if kwargs["include_payload"] is False else None)
    monkeypatch.setattr(mfapi_service, "get_nav_history", lambda *_args: (_ for _ in ()).throw(AssertionError("provider called")))

    summary = mfapi_service.get_nav_cache_summary("100")

    assert summary["available"] is True
    assert summary["count"] == 1
    assert summary["cache_status"] == "fresh"


def test_stored_history_returns_expired_cache_without_provider_refresh(monkeypatch):
    monkeypatch.setattr(mfapi_service, "_utc_now", lambda: NOW)
    monkeypatch.setattr(
        mfapi_service,
        "_read_cache_row",
        lambda *_args, **_kwargs: _row(fetched_delta=timedelta(days=-2), expires_delta=timedelta(days=-1)),
    )
    monkeypatch.setattr(
        mfapi_service,
        "get_nav_history",
        lambda *_args: (_ for _ in ()).throw(AssertionError("provider called")),
    )

    result = mfapi_service.get_stored_nav_history("100")

    assert result["ok"] is True
    assert result["cache_status"] == "stale_cache"
    assert result["stale"] is True
    assert result["point_count"] == 1


def test_same_scheme_refresh_is_single_flight(monkeypatch):
    monkeypatch.setattr(mfapi_service, "_utc_now", lambda: NOW)
    mfapi_service._scheme_locks.clear()
    cache: dict[str, object] = {}
    calls = 0
    calls_guard = threading.Lock()

    monkeypatch.setattr(mfapi_service, "_read_cache_row", lambda *_args, **_kwargs: cache.get("row"))

    def provider(_scheme_code):
        nonlocal calls
        with calls_guard:
            calls += 1
        time.sleep(0.05)
        return {"ok": True, "data": [{"nav_date": "2026-07-17", "nav": 10}]}

    def upsert(_scheme_code, rows, now):
        cache["row"] = {
            **_row(),
            "payload": rows,
            "fetched_at": now.isoformat(),
            "expires_at": (now + timedelta(hours=1)).isoformat(),
        }
        return cache["row"]

    monkeypatch.setattr(mfapi_service, "get_nav_history", provider)
    monkeypatch.setattr(mfapi_service, "_upsert_cache", upsert)
    monkeypatch.setattr(mfapi_service, "_record_cache_usage", lambda *_args: None)
    results: list[dict] = []
    threads = [threading.Thread(target=lambda: results.append(mfapi_service.get_cached_nav_history("100"))) for _ in range(5)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert calls == 1
    assert len(results) == 5
    assert all(result["ok"] for result in results)


def test_retention_uses_configured_cutoff(monkeypatch):
    captured: dict[str, str] = {}

    class Query:
        def delete(self):
            return self

        def lt(self, column, value):
            captured[column] = value
            return self

        def execute(self):
            return SimpleNamespace(data=[{"scheme_code": "old"}])

    monkeypatch.setattr(mfapi_service, "supabase", SimpleNamespace(table=lambda _name: Query()))
    monkeypatch.setattr(mfapi_service, "NAV_CACHE_RETENTION_DAYS", 30)

    assert mfapi_service.delete_expired_nav_cache_rows(NOW) == 1
    assert captured["updated_at"].startswith("2026-06-17")


def test_cache_upsert_writes_summary_metadata_and_refreshes_metrics(monkeypatch):
    captured: dict[str, object] = {}

    class Query:
        def upsert(self, row, on_conflict=None):
            captured["row"] = row
            captured["on_conflict"] = on_conflict
            return self

        def execute(self):
            return SimpleNamespace(data=[])

    monkeypatch.setattr(mfapi_service, "supabase", SimpleNamespace(table=lambda _name: Query()))
    monkeypatch.setattr(
        mfapi_service,
        "_refresh_active_snapshot_metrics",
        lambda scheme_code, rows, now: captured.update(metric_scheme=scheme_code, metric_rows=rows, metric_now=now),
    )
    rows = [
        {"scheme_code": "100", "nav_date": "2026-07-16", "nav": 10.0, "data_source": "mfapi"},
        {"scheme_code": "100", "nav_date": "2026-07-17", "nav": 11.0, "data_source": "mfapi"},
    ]

    result = mfapi_service._upsert_cache("100", rows, NOW)

    assert result["point_count"] == 2
    assert result["first_nav_date"] == "2026-07-16"
    assert result["last_nav_date"] == "2026-07-17"
    assert captured["on_conflict"] == "scheme_code"
    assert captured["metric_scheme"] == "100"


def test_production_runtime_has_no_legacy_nav_table_reference():
    backend_root = Path(__file__).parents[1]
    allowed = {
        backend_root / "app" / "mf_ingestion" / "jobs" / "archive_mf_nav_history.py",
        backend_root / "migrations" / "20260512_quota_safe_provider_architecture.sql",
        backend_root / "manual_migrations" / "drop_mutual_fund_nav_history_after_readiness.sql",
        backend_root / "scripts" / "check_nav_cache_drop_readiness.py",
    }
    offenders = []
    for path in backend_root.rglob("*"):
        if not path.is_file() or path in allowed or "tests" in path.parts or "__pycache__" in path.parts:
            continue
        if path.suffix not in {".py", ".sql"}:
            continue
        if "mutual_fund_nav_history" in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(str(path.relative_to(backend_root)))
    assert offenders == []


def test_legacy_nav_drop_is_manual_only_and_fail_closed():
    backend_root = Path(__file__).parents[1]
    automatic_drop = backend_root / "migrations" / "20260724_drop_mutual_fund_nav_history.sql"
    manual_drop = backend_root / "manual_migrations" / "drop_mutual_fund_nav_history_after_readiness.sql"

    assert not automatic_drop.exists()
    text = manual_drop.read_text(encoding="utf-8")
    assert "current_setting('fundersai.nav_drop_verified', true)" in text
    assert "DROP TABLE public.mutual_fund_nav_history" in text


def test_frontend_mf_route_is_fastapi_only():
    route = Path(__file__).parents[2] / "frontend" / "app" / "api" / "mf" / "[schemeCode]" / "route.ts"
    text = route.read_text(encoding="utf-8")
    assert "fetchFromBackend" in text
    assert "mutual_fund_nav_history" not in text
    assert "@/lib/supabase" not in text
    assert "calculateCAGR" not in text


def test_backend_mf_response_uses_full_history_and_freshness_contract():
    chat_service = Path(__file__).parents[1] / "app" / "services" / "chat_service.py"
    text = chat_service.read_text(encoding="utf-8")
    assert '"chartData": [pt.model_dump() for pt in profile.nav_history]' in text
    assert '"fullData": [pt.model_dump() for pt in profile.full_nav_history]' in text
    assert '"nav_history": {' in text
    assert '"fetched_at": nav_freshness.get("fetched_at")' in text


def test_fund_history_applies_2200_point_consumer_limit(monkeypatch):
    rows = [
        {"nav_date": (datetime(2018, 1, 1) + timedelta(days=index)).date().isoformat(), "nav": index + 1}
        for index in range(2500)
    ]
    monkeypatch.setattr(fund_service, "get_cached_nav_history", lambda _code: {"ok": True, "data": rows})

    frame = fund_service.FundService.get_mf_history_df("100", days=2200)

    assert len(frame) == 2200
    assert frame.index.min().date().isoformat() == rows[-2200]["nav_date"]
    assert frame.index.max().date().isoformat() == rows[-1]["nav_date"]


def test_candidate_scoring_treats_uncached_history_as_unknown(monkeypatch):
    calls = []
    monkeypatch.setattr(
        fund_service,
        "get_nav_cache_summary",
        lambda code: calls.append(code) or {"available": False, "count": 0, "first_nav_date": None, "last_nav_date": None},
    )
    rows = [{"scheme_code": "100", "scheme_name": "Axis Small Cap Direct Growth"}]

    scored = fund_service.FundService.score_fund_candidates("Axis Small Cap", rows, min_history_points=252)

    assert calls == ["100"]
    assert "nav_history_unknown:no_penalty" in scored[0]["notes"]
    assert not any(note.startswith("min_history_penalty") for note in scored[0]["notes"])


def test_auto_heal_force_refreshes_cache_instead_of_writing_history():
    service = Path(__file__).parents[1] / "app" / "services" / "auto_heal.py"
    text = service.read_text(encoding="utf-8")
    assert "get_cached_nav_history(scheme_code_str, force_refresh=True)" in text
    assert "mutual_fund_" + "nav_history" not in text


def test_github_actions_use_cache_retention_and_gated_archive():
    repo_root = Path(__file__).parents[2]
    workflows = repo_root / ".github" / "workflows"
    combined = "\n".join(path.read_text(encoding="utf-8") for path in workflows.glob("*.yml"))
    assert "sync_mf_history.py" not in combined
    assert "compact_mf_nav_5y" not in combined
    assert "python -m backend.app.jobs.sync_mf_nav" not in combined

    compact = (workflows / "compact-mf-storage.yml").read_text(encoding="utf-8")
    assert "cleanup_nav_api_cache" in compact
    archive = (workflows / "archive-mf-nav-history.yml").read_text(encoding="utf-8")
    assert "archive_mf_nav_history --verify" in archive
    assert "check_nav_cache_drop_readiness.py" in archive
    assert 'MF_NAV_CACHE_OBSERVATION_DAYS: "7"' in archive
