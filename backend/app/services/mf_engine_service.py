from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from app.database import supabase
from app.services import cache_policy
from app.services.provider_usage import log_provider_usage

logger = logging.getLogger(__name__)

PROVIDER = "mf_engine"
BASE_URL = (os.getenv("MF_ENGINE_BASE_URL") or "https://staging-app.mfapis.club").rstrip("/")
TIMEOUT_SECONDS = float(os.getenv("MF_ENGINE_TIMEOUT_SECONDS", "30"))
MAX_RETRIES = max(int(os.getenv("MF_ENGINE_MAX_RETRIES", "2")), 0)
TOKEN_TTL_SECONDS = int(os.getenv("MF_ENGINE_TOKEN_TTL_SECONDS", str(50 * 60)))

_TOKEN_CACHE: dict[str, Any] = {"token": None, "expires_at": None}


def is_configured() -> bool:
    return bool(os.getenv("MF_ENGINE_PARTNER_TOKEN") or (os.getenv("MF_ENGINE_EMAIL") and os.getenv("MF_ENGINE_PASSWORD")))


def list_schemes(
    *,
    limit: int = 100,
    page: int = 1,
    name: str | None = None,
    amc: str | None = None,
) -> dict[str, Any]:
    params: dict[str, Any] = {"limit": limit, "page": page}
    if name:
        params["name"] = name
    if amc:
        params["amc"] = amc
    result = _cached_request("scheme", "/scheme", params=params, ttl_policy="mutual_fund_enrichment")
    payload = result.get("data")
    rows = _extract_rows(payload)
    total = _pick_value(payload, ("total", "count", "total_count")) if isinstance(payload, dict) else None
    return {
        "ok": bool(result.get("ok")),
        "data": [_normalize_scheme(row) for row in rows],
        "total": _to_int(total),
        "error": result.get("error"),
        "source": result.get("source"),
    }


def list_amcs() -> dict[str, Any]:
    result = _cached_request("scheme_amcs", "/scheme/amcs", ttl_policy="mutual_fund_enrichment")
    return {"ok": bool(result.get("ok")), "data": _extract_rows(result.get("data")), "error": result.get("error")}


def get_scheme(scheme_id: str | int) -> dict[str, Any]:
    sid = str(scheme_id)
    result = _cached_request("scheme_detail", f"/scheme/{sid}", params={"id": sid}, ttl_policy="mutual_fund_enrichment")
    data = _first_object(result.get("data"))
    return {"ok": bool(result.get("ok")), "data": _normalize_scheme(data or {}), "error": result.get("error")}


def get_scheme_mf_data(scheme_id: str | int) -> dict[str, Any]:
    sid = str(scheme_id)
    result = _cached_request("scheme_mf_data", f"/scheme/mf-data/{sid}", params={"id": sid}, ttl_policy="mutual_fund_enrichment")
    data = _first_object(result.get("data"))
    return {"ok": bool(result.get("ok")), "data": _normalize_scheme(data or {}, scheme_id=sid), "error": result.get("error")}


def get_factsheet(isin: str) -> dict[str, Any]:
    clean_isin = str(isin or "").strip().upper()
    if not clean_isin:
        return {"ok": False, "data": None, "error": "missing_isin"}
    result = _cached_request(
        "scheme_factsheet",
        f"/scheme/factsheet/{clean_isin}",
        params={"isin": clean_isin},
        ttl_policy="mutual_fund_enrichment",
    )
    data = _first_object(result.get("data"))
    return {"ok": bool(result.get("ok")), "data": _normalize_factsheet(data or {}, clean_isin), "error": result.get("error")}


def get_holding_changes(
    scheme_id: str | int,
    *,
    months: int | None = None,
    holding_type: str | None = None,
    holding_name: str | None = None,
) -> dict[str, Any]:
    sid = str(scheme_id)
    params: dict[str, Any] = {"id": sid}
    if months:
        params["months"] = months
    if holding_type:
        params["holding_type"] = holding_type
    if holding_name:
        params["holding_name"] = holding_name
    result = _cached_request(
        "scheme_holding_changes",
        f"/scheme/{sid}/holding-changes",
        params=params,
        ttl_policy="mutual_fund_enrichment",
    )
    rows = [_normalize_holding(row, scheme_id=sid) for row in _extract_rows(result.get("data"))]
    return {"ok": bool(result.get("ok")), "data": rows, "error": result.get("error")}


def get_nav(scheme_id: str | int) -> dict[str, Any]:
    sid = str(scheme_id)
    result = _cached_request("nav", f"/nav/{sid}", params={"id": sid}, ttl_policy="mutual_fund_nav")
    rows = [_normalize_nav_row(row, sid) for row in _extract_rows(result.get("data"))]
    rows = [row for row in rows if row.get("nav_date") and row.get("nav") is not None]
    return {"ok": bool(result.get("ok")), "data": rows, "error": result.get("error")}


def normalize_scheme_payload(row: dict[str, Any]) -> dict[str, Any]:
    return _normalize_scheme(row)


def normalize_factsheet_payload(row: dict[str, Any], isin: str | None = None) -> dict[str, Any]:
    return _normalize_factsheet(row, isin)


def normalize_holding_payload(row: dict[str, Any], scheme_id: str | None = None) -> dict[str, Any]:
    return _normalize_holding(row, scheme_id=scheme_id)


def _cached_request(
    endpoint_name: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    ttl_policy: str,
) -> dict[str, Any]:
    now = _now()
    params = params or {}
    cache_key = _cache_key(endpoint_name, path, params)
    ttl = cache_policy.ttl_seconds(ttl_policy, 24 * 60 * 60)

    fresh = _read_cache(endpoint_name, cache_key, now, allow_stale=False)
    if fresh:
        log_provider_usage(
            provider=PROVIDER,
            endpoint=endpoint_name,
            scheme_code=_scheme_code_from_params(params),
            cache_hit=True,
            status_code=200,
            success=True,
            request_cost=0,
        )
        return {"ok": True, "data": fresh.get("response_json"), "source": "cache", "error": None}

    stale = _read_cache(endpoint_name, cache_key, now, allow_stale=True)
    if not is_configured():
        _log_usage(endpoint_name, params, None, False, "provider_not_configured", 0)
        if stale:
            return {"ok": True, "data": stale.get("response_json"), "source": "cache", "error": None, "stale": True}
        return {"ok": False, "data": None, "source": PROVIDER, "error": "provider_not_configured"}

    token = _get_token()
    if not token:
        _log_usage(endpoint_name, params, None, False, "auth_unavailable", 0)
        if stale:
            return {"ok": True, "data": stale.get("response_json"), "source": "cache", "error": None, "stale": True}
        return {"ok": False, "data": None, "source": PROVIDER, "error": "auth_unavailable"}

    last_error: str | None = None
    status_code: int | None = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = httpx.get(
                f"{BASE_URL}{path}",
                params=params or None,
                headers={"Authorization": f"Bearer {token}"},
                timeout=TIMEOUT_SECONDS,
            )
            status_code = response.status_code
            if response.status_code >= 400:
                last_error = f"http_{response.status_code}"
                if response.status_code >= 500 and attempt < MAX_RETRIES:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                _mark_failure(endpoint_name, response.status_code, last_error)
                _log_usage(endpoint_name, params, response.status_code, False, last_error, 1)
                if stale:
                    return {"ok": True, "data": stale.get("response_json"), "source": "cache", "error": None, "stale": True}
                return {"ok": False, "data": None, "source": PROVIDER, "error": last_error, "status_code": response.status_code}
            payload = response.json()
            fetched_at = now.isoformat()
            _write_cache(endpoint_name, cache_key, params, payload, fetched_at, now + timedelta(seconds=ttl))
            _mark_success(endpoint_name)
            _log_usage(endpoint_name, params, response.status_code, True, None, 1)
            return {"ok": True, "data": payload, "source": PROVIDER, "error": None, "status_code": response.status_code}
        except Exception as exc:
            last_error = str(exc)
            if attempt < MAX_RETRIES:
                time.sleep(0.5 * (attempt + 1))
                continue

    _mark_failure(endpoint_name, status_code, last_error)
    _log_usage(endpoint_name, params, status_code, False, last_error or "request_error", 1)
    if stale:
        return {"ok": True, "data": stale.get("response_json"), "source": "cache", "error": None, "stale": True}
    return {"ok": False, "data": None, "source": PROVIDER, "error": last_error or "request_error", "status_code": status_code}


def _get_token() -> str | None:
    direct = os.getenv("MF_ENGINE_PARTNER_TOKEN")
    if direct:
        return direct.strip()

    cached = _TOKEN_CACHE.get("token")
    expires_at = _TOKEN_CACHE.get("expires_at")
    if cached and isinstance(expires_at, datetime) and expires_at > _now():
        return str(cached)

    email = os.getenv("MF_ENGINE_EMAIL")
    password = os.getenv("MF_ENGINE_PASSWORD")
    if not email or not password:
        return None

    payload = {"email": email, "password": password}
    for path in ("/partner/login", "/user/login"):
        try:
            response = httpx.post(f"{BASE_URL}{path}", json=payload, timeout=TIMEOUT_SECONDS)
            if response.status_code >= 400:
                continue
            token = _extract_token(response.json())
            if token:
                _TOKEN_CACHE["token"] = token
                _TOKEN_CACHE["expires_at"] = _now() + timedelta(seconds=TOKEN_TTL_SECONDS)
                return token
        except Exception as exc:
            logger.warning("MF Engine login failed through %s: %s", path, exc)
    return None


def _extract_token(payload: Any) -> str | None:
    if not isinstance(payload, dict):
        return None
    candidates = [
        payload.get("token"),
        payload.get("access_token"),
        payload.get("jwt"),
        payload.get("id_token"),
    ]
    data = payload.get("data")
    if isinstance(data, dict):
        candidates.extend([data.get("token"), data.get("access_token"), data.get("jwt"), data.get("id_token")])
    for candidate in candidates:
        if candidate:
            return str(candidate)
    return None


def _normalize_scheme(row: dict[str, Any], scheme_id: str | None = None) -> dict[str, Any]:
    payload = row if isinstance(row, dict) else {}
    meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
    source = {**meta, **payload}
    raw_name = _pick_value(source, ("scheme_name", "schemeName", "name", "plan_name", "scheme"))
    scheme_code = _pick_value(
        source,
        ("scheme_code", "schemeCode", "amfi_scheme_code", "amfiCode", "amfi_code", "code"),
    )
    api_id = _pick_value(source, ("id", "scheme_id", "schemeId")) or scheme_id
    isin_growth = _pick_value(source, ("isin_growth", "isinGrowth", "isin", "isin_code", "isinCode"))
    isin_div = _pick_value(source, ("isin_div_reinvestment", "isinDivReinvestment", "dividend_isin", "idcw_isin"))
    returns = source.get("returns") if isinstance(source.get("returns"), dict) else {}
    ratios = source.get("ratios") if isinstance(source.get("ratios"), dict) else {}
    return {
        "provider_scheme_id": str(api_id) if api_id not in (None, "") else None,
        "scheme_code": str(scheme_code) if scheme_code not in (None, "") else None,
        "scheme_name": str(raw_name).strip() if raw_name else None,
        "amc_name": _pick_value(source, ("amc", "amc_name", "fund_house", "fundHouse")),
        "category": _pick_value(source, ("category", "scheme_category", "schemeCategory")),
        "sub_category": _pick_value(source, ("sub_category", "subCategory")),
        "plan_type": _pick_value(source, ("plan", "plan_type", "planType")),
        "option_type": _pick_value(source, ("option", "option_type", "optionType")),
        "fund_type": _pick_value(source, ("fund_type", "scheme_type", "type")),
        "isin_growth": str(isin_growth).strip().upper() if isin_growth else None,
        "isin_div_reinvestment": str(isin_div).strip().upper() if isin_div else None,
        "nav": _to_float(_pick_value(source, ("nav", "latest_nav", "latestNav"))),
        "nav_date": _to_date_iso(_pick_value(source, ("nav_date", "navDate", "date"))),
        "return_1m": _return_value(returns, "1m"),
        "return_3m": _return_value(returns, "3m"),
        "return_6m": _return_value(returns, "6m"),
        "return_1y": _return_value(returns, "1y"),
        "return_3y": _return_value(returns, "3y"),
        "return_5y": _return_value(returns, "5y"),
        "expense_ratio": _to_float(_pick_value(source, ("expense_ratio", "expenseRatio", "ter"))),
        "aum": _to_float(_pick_value(source, ("aum", "aum_cr", "aumCr", "asset_under_management"))),
        "benchmark": _pick_value(source, ("benchmark", "benchmark_name", "benchmarkName")),
        "risk_level": _pick_value(source, ("risk_level", "riskometer", "risk")),
        "fund_manager": _pick_value(source, ("fund_manager", "fundManager", "manager")),
        "alpha": _to_float(ratios.get("alpha") if isinstance(ratios, dict) else None),
        "beta": _to_float(ratios.get("beta") if isinstance(ratios, dict) else None),
        "sharpe_ratio": _to_float((ratios.get("sharpe") or ratios.get("sharpe_ratio")) if isinstance(ratios, dict) else None),
        "provider_payload": payload,
    }


def _normalize_factsheet(row: dict[str, Any], isin: str | None = None) -> dict[str, Any]:
    scheme = _normalize_scheme(row)
    return {
        **scheme,
        "isin_growth": scheme.get("isin_growth") or (str(isin).strip().upper() if isin else None),
        "report_month": _month_to_date(_pick_value(row, ("month", "report_month", "as_of_date", "date"))),
        "factsheet_payload": row,
    }


def _normalize_holding(row: dict[str, Any], scheme_id: str | None = None) -> dict[str, Any]:
    payload = row if isinstance(row, dict) else {}
    holding_type = _pick_value(payload, ("holding_type", "holdingType", "type", "asset_type")) or "equity"
    return {
        "provider_scheme_id": str(_pick_value(payload, ("scheme_id", "schemeId")) or scheme_id) if (_pick_value(payload, ("scheme_id", "schemeId")) or scheme_id) else None,
        "scheme_code": str(_pick_value(payload, ("scheme_code", "schemeCode", "amfi_scheme_code", "amfiCode"))) if _pick_value(payload, ("scheme_code", "schemeCode", "amfi_scheme_code", "amfiCode")) else None,
        "as_of_date": _month_to_date(_pick_value(payload, ("as_of_date", "asOfDate", "report_month", "month", "date"))),
        "holding_type": str(holding_type).strip().lower(),
        "security_name": _pick_value(payload, ("security_name", "securityName", "holding_name", "holdingName", "name")),
        "isin": _pick_value(payload, ("isin", "isin_code", "isinCode")),
        "sector": _pick_value(payload, ("sector", "sector_name", "industry")),
        "weight_pct": _to_float(_pick_value(payload, ("weight_pct", "weight", "percentage", "percent", "percent_aum"))),
        "quantity": _to_float(_pick_value(payload, ("quantity", "qty"))),
        "market_value_cr": _to_float(_pick_value(payload, ("market_value_cr", "marketValueCr", "market_value", "value"))),
        "provider_payload": payload,
    }


def _normalize_nav_row(row: dict[str, Any], scheme_id: str) -> dict[str, Any]:
    payload = row if isinstance(row, dict) else {}
    return {
        "provider_scheme_id": scheme_id,
        "scheme_code": str(_pick_value(payload, ("scheme_code", "schemeCode", "amfi_scheme_code", "amfiCode")) or ""),
        "nav_date": _to_date_iso(_pick_value(payload, ("nav_date", "navDate", "date"))),
        "nav": _to_float(_pick_value(payload, ("nav", "value"))),
        "data_source": PROVIDER,
    }


def _extract_rows(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in ("list", "data", "rows", "items", "results", "schemes", "holdings", "nav"):
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
        if isinstance(value, dict):
            nested = _extract_rows(value)
            if nested:
                return nested
    return [payload]


def _first_object(payload: Any) -> dict[str, Any] | None:
    rows = _extract_rows(payload)
    return rows[0] if rows else None


def _pick_value(source: dict[str, Any], keys: tuple[str, ...]) -> Any:
    for key in keys:
        if key in source and source.get(key) not in (None, ""):
            return source.get(key)
    return None


def _return_value(returns: dict[str, Any], key: str) -> float | None:
    value = returns.get(key) or returns.get(key.upper()) or returns.get(key.replace("y", "Y").replace("m", "M"))
    if isinstance(value, dict):
        value = value.get("value") or value.get("return")
    return _to_float(value)


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _to_date_iso(value: Any) -> str | None:
    if not value:
        return None
    raw = str(value).strip()
    if len(raw) >= 10 and raw[4:5] == "-" and raw[7:8] == "-":
        try:
            return datetime.fromisoformat(raw[:10]).date().isoformat()
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y", "%d %b %Y", "%b %d, %Y", "%B %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _month_to_date(value: Any) -> str | None:
    if not value:
        return None
    direct = _to_date_iso(value)
    if direct:
        return direct[:8] + "01"
    raw = str(value).strip()
    for fmt in ("%Y-%m", "%b %Y", "%B %Y"):
        try:
            return datetime.strptime(raw, fmt).date().replace(day=1).isoformat()
        except ValueError:
            continue
    return None


def _read_cache(endpoint: str, cache_key: str, now: datetime, allow_stale: bool) -> dict[str, Any] | None:
    if not supabase:
        return None
    try:
        row = (
            supabase.table("provider_response_cache")
            .select("*")
            .eq("provider", PROVIDER)
            .eq("endpoint", endpoint)
            .eq("cache_key", cache_key)
            .eq("status", "success")
            .order("fetched_at", desc=True)
            .limit(1)
            .execute()
            .data
            or [None]
        )[0]
        if not row:
            return None
        expires_at = _parse_dt(row.get("expires_at"))
        if allow_stale or not expires_at or expires_at > now:
            return row
    except Exception as exc:
        logger.warning("MF Engine cache read failed for %s: %s", endpoint, exc)
    return None


def _write_cache(endpoint: str, cache_key: str, params: dict[str, Any], data: Any, fetched_at: str, expires_at: datetime) -> None:
    if not supabase:
        return
    row = {
        "provider": PROVIDER,
        "endpoint": endpoint,
        "cache_key": cache_key,
        "params_json": params,
        "response_json": data,
        "fetched_at": fetched_at,
        "expires_at": expires_at.isoformat(),
        "status": "success",
    }
    try:
        supabase.table("provider_response_cache").upsert(row, on_conflict="provider,endpoint,cache_key").execute()
    except Exception as exc:
        logger.warning("MF Engine cache write failed for %s: %s", endpoint, exc)


def _mark_success(endpoint: str) -> None:
    if not supabase:
        return
    row = {
        "provider": PROVIDER,
        "endpoint_name": endpoint,
        "last_success_at": _now().isoformat(),
        "last_status_code": 200,
        "failure_count": 0,
        "disabled_until": None,
        "last_error_message": None,
    }
    try:
        supabase.table("provider_endpoint_health").upsert(row, on_conflict="provider,endpoint_name").execute()
    except Exception as exc:
        logger.warning("MF Engine health success write failed for %s: %s", endpoint, exc)


def _mark_failure(endpoint: str, status: int | None, message: str | None) -> None:
    if not supabase:
        return
    row = {
        "provider": PROVIDER,
        "endpoint_name": endpoint,
        "last_failure_at": _now().isoformat(),
        "last_status_code": status,
        "failure_count": 1,
        "last_error_message": (message or "provider_error")[:500],
    }
    try:
        supabase.table("provider_endpoint_health").upsert(row, on_conflict="provider,endpoint_name").execute()
    except Exception as exc:
        logger.warning("MF Engine health failure write failed for %s: %s", endpoint, exc)


def _log_usage(endpoint: str, params: dict[str, Any], status_code: int | None, success: bool, error: str | None, cost: int) -> None:
    log_provider_usage(
        provider=PROVIDER,
        endpoint=endpoint,
        scheme_code=_scheme_code_from_params(params),
        cache_hit=False,
        status_code=status_code,
        success=success,
        error_message=error,
        request_cost=cost,
    )


def _scheme_code_from_params(params: dict[str, Any]) -> str | None:
    value = params.get("scheme_code") or params.get("id") or params.get("isin")
    return str(value) if value not in (None, "") else None


def _cache_key(endpoint: str, path: str, params: dict[str, Any]) -> str:
    payload = json.dumps({"endpoint": endpoint, "path": path, "params": params}, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _parse_dt(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)
