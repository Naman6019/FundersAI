from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.database import supabase
from app.services.mf_metrics_service import compute_nav_metrics
from app.services.provider_usage import log_provider_usage

logger = logging.getLogger(__name__)

PROVIDER = "mfapi"
BASE_URL = os.getenv("MFAPI_BASE_URL", "https://api.mfapi.in").rstrip("/")
TIMEOUT_SECONDS = float(os.getenv("MFAPI_TIMEOUT_SECONDS", "20"))
MAX_RETRIES = max(int(os.getenv("MFAPI_MAX_RETRIES", "1")), 0)
NAV_CACHE_TTL_SECONDS = max(int(os.getenv("MF_NAV_CACHE_TTL_SECONDS", "86400")), 1)
NAV_CACHE_MAX_STALE_SECONDS = max(int(os.getenv("MF_NAV_CACHE_MAX_STALE_SECONDS", "604800")), 0)
NAV_CACHE_RETENTION_DAYS = max(int(os.getenv("MF_NAV_CACHE_RETENTION_DAYS", "30")), 1)

_scheme_locks: dict[str, threading.Lock] = {}
_scheme_locks_guard = threading.Lock()


def _request(path: str, params: dict[str, Any] | None = None, scheme_code: str | None = None) -> dict[str, Any]:
    endpoint = path.strip("/")
    last_error: str | None = None
    status_code: int | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = httpx.get(f"{BASE_URL}{path}", params=params, timeout=TIMEOUT_SECONDS)
            status_code = response.status_code
            if response.status_code >= 400:
                last_error = f"http_{response.status_code}"
                if response.status_code >= 500 and attempt < MAX_RETRIES:
                    continue
                log_provider_usage(
                    provider=PROVIDER,
                    endpoint=endpoint,
                    scheme_code=scheme_code,
                    cache_hit=False,
                    status_code=response.status_code,
                    success=False,
                    error_message=last_error,
                    request_cost=1,
                )
                return {"ok": False, "error": last_error, "status_code": response.status_code, "data": None}
            data = response.json()
            log_provider_usage(
                provider=PROVIDER,
                endpoint=endpoint,
                scheme_code=scheme_code,
                cache_hit=False,
                status_code=response.status_code,
                success=True,
                error_message=None,
                request_cost=1,
            )
            return {"ok": True, "error": None, "status_code": response.status_code, "data": data}
        except Exception as exc:
            last_error = str(exc)
            if attempt < MAX_RETRIES:
                time.sleep(0.2 * (attempt + 1))
                continue
    log_provider_usage(
        provider=PROVIDER,
        endpoint=endpoint,
        scheme_code=scheme_code,
        cache_hit=False,
        status_code=status_code,
        success=False,
        error_message=last_error,
        request_cost=1,
    )
    return {"ok": False, "error": last_error or "request_error", "status_code": status_code, "data": None}


def _to_date_iso(value: Any) -> str | None:
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d-%b-%Y"):
        try:
            return datetime.strptime(raw[:11], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).astimezone(timezone.utc)
    except (TypeError, ValueError):
        return None


def _lock_for_scheme(scheme_code: str) -> threading.Lock:
    with _scheme_locks_guard:
        return _scheme_locks.setdefault(scheme_code, threading.Lock())


def _normalize_history_rows(scheme_code: str, rows: Any) -> list[dict[str, Any]]:
    if not isinstance(rows, list):
        return []
    by_date: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        nav_date = _to_date_iso(row.get("nav_date") or row.get("date"))
        nav = _to_float(row.get("nav") if row.get("nav") is not None else row.get("value"))
        if not nav_date or nav is None or nav <= 0:
            continue
        by_date[nav_date] = {
            "scheme_code": scheme_code,
            "nav_date": nav_date,
            "nav": nav,
            "data_source": PROVIDER,
        }
    return [by_date[nav_date] for nav_date in sorted(by_date)]


def _read_cache_row(scheme_code: str, *, include_payload: bool = True) -> dict[str, Any] | None:
    if not supabase:
        return None
    fields = "*" if include_payload else (
        "scheme_code,point_count,first_nav_date,last_nav_date,source,fetched_at,expires_at,updated_at"
    )
    try:
        response = (
            supabase.table("nav_api_cache")
            .select(fields)
            .eq("scheme_code", scheme_code)
            .limit(1)
            .execute()
        )
        row = (response.data or [None])[0]
        return row if isinstance(row, dict) else None
    except Exception as exc:
        logger.warning("NAV cache lookup failed for %s: %s", scheme_code, exc)
        return None


def _cache_status(row: dict[str, Any] | None, now: datetime) -> str:
    if not row:
        return "miss"
    expires_at = _parse_timestamp(row.get("expires_at"))
    return "fresh" if expires_at and expires_at > now else "expired"


def get_nav_cache_summary(scheme_code: str) -> dict[str, Any]:
    """Read cache metadata only. This function never calls MFAPI."""
    code = str(scheme_code or "").strip()
    default = {
        "available": False,
        "count": 0,
        "point_count": 0,
        "first_nav_date": None,
        "last_nav_date": None,
        "source": None,
        "fetched_at": None,
        "expires_at": None,
        "updated_at": None,
        "cache_status": "miss",
        "stale": False,
    }
    if not code:
        return default
    row = _read_cache_row(code, include_payload=False)
    if not row:
        return default
    now = _utc_now()
    status = _cache_status(row, now)
    count = max(int(row.get("point_count") or 0), 0)
    return {
        **default,
        **row,
        "available": True,
        "count": count,
        "point_count": count,
        "cache_status": status,
        "stale": status != "fresh",
    }


def _cache_result(row: dict[str, Any], *, status: str, stale: bool) -> dict[str, Any]:
    payload = row.get("payload") if isinstance(row.get("payload"), list) else []
    return {
        "ok": True,
        "data": payload,
        "error": None,
        "cache_status": status,
        "stale": stale,
        "fetched_at": row.get("fetched_at"),
        "expires_at": row.get("expires_at"),
        "point_count": int(row.get("point_count") or len(payload)),
    }


def _record_cache_usage(scheme_code: str, endpoint: str) -> None:
    log_provider_usage(
        provider=PROVIDER,
        endpoint=endpoint,
        scheme_code=scheme_code,
        cache_hit=True,
        status_code=200,
        success=True,
        request_cost=0,
    )


def _record_refresh_usage(scheme_code: str) -> None:
    log_provider_usage(
        provider=PROVIDER,
        endpoint="nav_cache/refresh",
        scheme_code=scheme_code,
        cache_hit=False,
        status_code=200,
        success=True,
        request_cost=0,
    )


def _refresh_active_snapshot_metrics(scheme_code: str, rows: list[dict[str, Any]], now: datetime) -> None:
    if not supabase or not rows:
        return
    metrics = {key: value for key, value in compute_nav_metrics(rows).items() if value is not None}
    latest = rows[-1]
    payload = {
        **metrics,
        "nav": latest["nav"],
        "nav_date": latest["nav_date"],
        "last_updated": now.isoformat(),
    }
    try:
        supabase.table("mutual_fund_core_snapshot").update(payload).eq("scheme_code", scheme_code).execute()
    except Exception as exc:
        logger.warning("NAV metric refresh failed for %s: %s", scheme_code, exc)


def _upsert_cache(scheme_code: str, rows: list[dict[str, Any]], now: datetime) -> dict[str, Any]:
    expires_at = now + timedelta(seconds=NAV_CACHE_TTL_SECONDS)
    row = {
        "scheme_code": scheme_code,
        "payload": rows,
        "point_count": len(rows),
        "first_nav_date": rows[0]["nav_date"],
        "last_nav_date": rows[-1]["nav_date"],
        "source": PROVIDER,
        "fetched_at": now.isoformat(),
        "expires_at": expires_at.isoformat(),
        "updated_at": now.isoformat(),
    }
    if supabase:
        supabase.table("nav_api_cache").upsert(row, on_conflict="scheme_code").execute()
        _refresh_active_snapshot_metrics(scheme_code, rows, now)
    return row


def _usable_stale_row(row: dict[str, Any] | None, now: datetime) -> bool:
    if not row or not isinstance(row.get("payload"), list) or not row.get("payload"):
        return False
    fetched_at = _parse_timestamp(row.get("fetched_at"))
    return bool(fetched_at and now - fetched_at <= timedelta(seconds=NAV_CACHE_MAX_STALE_SECONDS))


def list_schemes(limit: int = 1000, offset: int = 0) -> dict[str, Any]:
    result = _request("/mf", {"limit": limit, "offset": offset})
    payload = result.get("data")
    rows: list[dict[str, Any]] = []
    if isinstance(payload, dict):
        rows = payload.get("data") or []
    elif isinstance(payload, list):
        rows = payload
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        scheme_code = row.get("schemeCode") or row.get("scheme_code")
        scheme_name = row.get("schemeName") or row.get("scheme_name")
        if scheme_code is None or not scheme_name:
            continue
        normalized.append(
            {
                "scheme_code": str(scheme_code),
                "scheme_name": str(scheme_name).strip(),
                "isin_growth": row.get("isinGrowth") or row.get("isin_growth"),
                "isin_div_reinvestment": row.get("isinDivReinvestment") or row.get("isin_div_reinvestment"),
            }
        )
    return {"ok": bool(result.get("ok")), "data": normalized, "error": result.get("error")}


def search_schemes(query: str) -> dict[str, Any]:
    result = _request("/mf/search", {"q": query})
    payload = result.get("data")
    rows = payload if isinstance(payload, list) else []
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        scheme_code = row.get("schemeCode") or row.get("scheme_code")
        scheme_name = row.get("schemeName") or row.get("scheme_name")
        if scheme_code is None or not scheme_name:
            continue
        normalized.append({"scheme_code": str(scheme_code), "scheme_name": str(scheme_name).strip()})
    return {"ok": bool(result.get("ok")), "data": normalized, "error": result.get("error")}


def get_latest_nav(scheme_code: str) -> dict[str, Any]:
    code = str(scheme_code)
    result = _request(f"/mf/{code}/latest", scheme_code=code)
    payload = result.get("data")
    if not isinstance(payload, dict):
        return {"ok": False, "data": None, "error": result.get("error") or "invalid_payload"}
    meta = payload.get("meta") or {}
    rows = payload.get("data") or []
    latest = rows[0] if isinstance(rows, list) and rows else {}
    normalized = {
        "scheme_code": code,
        "scheme_name": meta.get("scheme_name"),
        "amc_name": meta.get("fund_house"),
        "category": meta.get("scheme_category"),
        "fund_type": meta.get("scheme_type"),
        "isin_growth": meta.get("isin_growth"),
        "isin_div_reinvestment": meta.get("isin_div_reinvestment"),
        "nav": _to_float(latest.get("nav")),
        "nav_date": _to_date_iso(latest.get("date")),
        "provider_payload": payload,
    }
    return {"ok": bool(result.get("ok")), "data": normalized, "error": result.get("error")}


def get_nav_history(scheme_code: str, start_date: str | None = None, end_date: str | None = None) -> dict[str, Any]:
    code = str(scheme_code)
    params: dict[str, Any] = {}
    if start_date:
        params["startDate"] = start_date
    if end_date:
        params["endDate"] = end_date
    result = _request(f"/mf/{code}", params=params or None, scheme_code=code)
    payload = result.get("data")
    if not isinstance(payload, dict):
        return {"ok": False, "data": [], "error": result.get("error") or "invalid_payload"}
    rows = payload.get("data") or []
    normalized: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        nav_date = _to_date_iso(row.get("date"))
        nav = _to_float(row.get("nav"))
        if not nav_date or nav is None:
            continue
        normalized.append({"scheme_code": code, "nav_date": nav_date, "nav": nav, "data_source": PROVIDER})
    return {"ok": bool(result.get("ok")), "data": normalized, "error": result.get("error"), "payload": payload}


def get_cached_nav_history(scheme_code: str, force_refresh: bool = False) -> dict[str, Any]:
    code = str(scheme_code or "").strip()
    if not code:
        return {
            "ok": False,
            "data": [],
            "error": {"code": "invalid_scheme_code", "provider": PROVIDER, "retryable": False},
            "cache_status": "miss",
            "stale": False,
        }

    now = _utc_now()
    cached = _read_cache_row(code)
    initial_fetched_at = cached.get("fetched_at") if cached else None
    if not force_refresh and _cache_status(cached, now) == "fresh":
        logger.info("NAV cache hit scheme_code=%s", code)
        _record_cache_usage(code, "nav_cache/hit")
        return _cache_result(cached or {}, status="hit", stale=False)

    with _lock_for_scheme(code):
        # Another request may have refreshed this scheme while we waited.
        now = _utc_now()
        cached = _read_cache_row(code)
        if not force_refresh and _cache_status(cached, now) == "fresh":
            logger.info("NAV cache hit after single-flight wait scheme_code=%s", code)
            _record_cache_usage(code, "nav_cache/hit")
            return _cache_result(cached or {}, status="hit", stale=False)
        if (
            force_refresh
            and _cache_status(cached, now) == "fresh"
            and cached
            and cached.get("fetched_at") != initial_fetched_at
        ):
            logger.info("NAV cache force-refresh coalesced scheme_code=%s", code)
            _record_cache_usage(code, "nav_cache/hit")
            return _cache_result(cached, status="hit", stale=False)

        logger.info("NAV cache refresh scheme_code=%s force_refresh=%s", code, force_refresh)
        provider_result = get_nav_history(code)
        rows = _normalize_history_rows(code, provider_result.get("data"))
        if provider_result.get("ok") and rows:
            try:
                cache_row = _upsert_cache(code, rows, now)
            except Exception as exc:
                logger.warning("NAV cache upsert failed for %s: %s", code, exc)
                cache_row = {
                    "payload": rows,
                    "point_count": len(rows),
                    "fetched_at": now.isoformat(),
                    "expires_at": (now + timedelta(seconds=NAV_CACHE_TTL_SECONDS)).isoformat(),
                }
            _record_refresh_usage(code)
            return _cache_result(cache_row, status="refreshed", stale=False)

        provider_error = provider_result.get("error") or "invalid_or_empty_history"
        logger.warning("NAV provider failure scheme_code=%s error=%s", code, provider_error)
        if provider_result.get("ok"):
            log_provider_usage(
                provider=PROVIDER,
                endpoint="nav_cache/invalid_payload",
                scheme_code=code,
                cache_hit=False,
                status_code=502,
                success=False,
                error_message=str(provider_error),
                request_cost=0,
            )
        if _usable_stale_row(cached, now):
            logger.warning("NAV cache stale fallback scheme_code=%s", code)
            _record_cache_usage(code, "nav_cache/stale_fallback")
            return _cache_result(cached or {}, status="stale_fallback", stale=True)

        return {
            "ok": False,
            "data": [],
            "error": {
                "code": "nav_provider_unavailable",
                "provider": PROVIDER,
                "message": str(provider_error),
                "retryable": True,
            },
            "cache_status": "miss" if not cached else "stale_too_old",
            "stale": False,
            "fetched_at": cached.get("fetched_at") if cached else None,
            "expires_at": cached.get("expires_at") if cached else None,
            "point_count": 0,
        }


def delete_expired_nav_cache_rows(now: datetime | None = None) -> int:
    if not supabase:
        return 0
    cutoff = (now or _utc_now()) - timedelta(days=NAV_CACHE_RETENTION_DAYS)
    try:
        response = supabase.table("nav_api_cache").delete().lt("updated_at", cutoff.isoformat()).execute()
        deleted = len(response.data or [])
        logger.info("NAV cache retention deleted_rows=%s cutoff=%s", deleted, cutoff.isoformat())
        return deleted
    except Exception as exc:
        logger.error("NAV cache retention failed: %s", exc)
        raise
