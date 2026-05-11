from __future__ import annotations

import hashlib
import json
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from app.database import supabase
from app.providers.indianapi_client import IndianAPIClient, ProviderResult
from app.services import cache_policy
from app.services.indianapi_quota_guard import evaluate as evaluate_quota
from app.services.provider_usage import log_provider_usage

logger = logging.getLogger(__name__)

PROVIDER = "indianapi"
UNAVAILABLE_MESSAGE = "This data is currently unavailable from the provider."
DISABLE_SECONDS_ON_403 = 24 * 60 * 60

ENDPOINT_TTL_POLICY: dict[str, str] = {
    "industry_search": "stock_profile",
    "stock": "stock_profile",
    "historical_stats": "stock_fundamentals",
    "corporate_actions": "stock_profile",
    "recent_announcements": "stock_profile",
    "historical_data": "stock_price_history",
    "mutual_fund_search": "mutual_fund_nav",
    "mutual_funds": "mutual_fund_nav",
    "mutual_funds_details": "mutual_fund_enrichment",
    "stock_target_price": "stock_profile",
    "stock_forecasts": "stock_profile",
}


def resolve_stock(query: str) -> dict[str, Any]:
    return _cached_call("industry_search", {"query": query}, lambda client: client.search_stocks(query))


def get_stock_research_profile(stock_name: str) -> dict[str, Any]:
    return _cached_call(
        "stock",
        {"name": stock_name},
        lambda client: client.get_stock_details(stock_name),
        normalized_table="stock_profiles",
        normalized_key={"stock_name": stock_name},
    )


def get_stock_fundamentals(stock_name: str, stats: str) -> dict[str, Any]:
    return _cached_call(
        "historical_stats",
        {"stock_name": stock_name, "stats": stats},
        lambda client: client.get_historical_stats(stock_name, stats),
        normalized_table="stock_financial_stats",
        normalized_key={"stock_name": stock_name, "stats": stats},
    )


def get_stock_corporate_actions(stock_name: str) -> dict[str, Any]:
    return _cached_call(
        "corporate_actions",
        {"stock_name": stock_name},
        lambda client: client.get_corporate_actions(stock_name),
        normalized_table="stock_corporate_actions",
        normalized_key={"stock_name": stock_name},
    )


def get_stock_recent_announcements(stock_name: str) -> dict[str, Any]:
    return _cached_call(
        "recent_announcements",
        {"stock_name": stock_name},
        lambda client: client.get_recent_announcements(stock_name),
        normalized_table="stock_recent_announcements",
        normalized_key={"stock_name": stock_name},
    )


def resolve_mutual_fund(query: str) -> dict[str, Any]:
    return _cached_call("mutual_fund_search", {"query": query}, lambda client: client.search_mutual_funds(query))


def get_mutual_fund_universe() -> dict[str, Any]:
    return _cached_call(
        "mutual_funds",
        {},
        lambda client: client.get_mutual_funds(),
        normalized_table="mutual_funds",
        normalized_key={},
    )


def get_mutual_fund_research_profile(fund_name: str) -> dict[str, Any]:
    return _cached_call(
        "mutual_funds_details",
        {"stock_name": fund_name},
        lambda client: client.get_mutual_fund_details(fund_name),
        normalized_table="mutual_fund_details",
        normalized_key={"stock_name": fund_name},
    )


def get_stock_historical_data_optional(stock_name: str, period: str, filter: str) -> dict[str, Any]:
    return _cached_call(
        "historical_data",
        {"stock_name": stock_name, "period": period, "filter": filter},
        lambda client: client.get_historical_data(stock_name, period, filter),
        optional=True,
    )


def get_stock_analyst_target_optional(stock_id: str) -> dict[str, Any]:
    return _cached_call(
        "stock_target_price",
        {"stock_id": stock_id},
        lambda client: client.get_stock_target_price(stock_id),
        optional=True,
    )


def get_stock_forecasts_optional(
    stock_id: str,
    measure_code: str,
    period_type: str,
    data_type: str,
    age: str,
) -> dict[str, Any]:
    return _cached_call(
        "stock_forecasts",
        {
            "stock_id": stock_id,
            "measure_code": measure_code,
            "period_type": period_type,
            "data_type": data_type,
            "age": age,
        },
        lambda client: client.get_stock_forecasts(stock_id, measure_code, period_type, data_type, age),
        optional=True,
    )


# Camel-case aliases match the requested service names.
resolveStock = resolve_stock
getStockResearchProfile = get_stock_research_profile
getStockFundamentals = get_stock_fundamentals
getStockCorporateActions = get_stock_corporate_actions
getStockRecentAnnouncements = get_stock_recent_announcements
resolveMutualFund = resolve_mutual_fund
getMutualFundUniverse = get_mutual_fund_universe
getMutualFundResearchProfile = get_mutual_fund_research_profile
getStockHistoricalDataOptional = get_stock_historical_data_optional
getStockAnalystTargetOptional = get_stock_analyst_target_optional
getStockForecastsOptional = get_stock_forecasts_optional


def _cached_call(
    endpoint_name: str,
    params: dict[str, Any],
    fetcher: Callable[[IndianAPIClient], ProviderResult],
    optional: bool = False,
    normalized_table: str | None = None,
    normalized_key: dict[str, Any] | None = None,
) -> dict[str, Any]:
    now = _now()
    ttl_seconds = cache_policy.ttl_seconds(ENDPOINT_TTL_POLICY.get(endpoint_name, "stock_profile"), 24 * 60 * 60)
    cache_key = _cache_key(endpoint_name, params)
    symbol, scheme_code = _extract_symbol_and_scheme(params)

    fresh = _read_generic_cache(endpoint_name, cache_key, now, allow_stale=False)
    if fresh:
        log_provider_usage(
            provider=PROVIDER,
            endpoint=endpoint_name,
            symbol=symbol,
            scheme_code=scheme_code,
            cache_hit=True,
            status_code=200,
            success=True,
            request_cost=0,
        )
        return _service_ok(endpoint_name, fresh["response_json"], fresh["fetched_at"], "cache", stale=False)

    stale = _read_generic_cache(endpoint_name, cache_key, now, allow_stale=True)
    enabled = os.environ.get("INDIANAPI_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        log_provider_usage(
            provider=PROVIDER,
            endpoint=endpoint_name,
            symbol=symbol,
            scheme_code=scheme_code,
            cache_hit=False,
            status_code=None,
            success=False,
            error_message="provider_disabled",
            request_cost=0,
        )
        if stale:
            return _service_ok(
                endpoint_name,
                stale["response_json"],
                stale["fetched_at"],
                "cache",
                stale=True,
                warning="Using stale cache because IndianAPI is disabled.",
            )
        return _service_error(endpoint_name, "provider_disabled", UNAVAILABLE_MESSAGE, stale=True)

    if _endpoint_feature_disabled(endpoint_name):
        log_provider_usage(
            provider=PROVIDER,
            endpoint=endpoint_name,
            symbol=symbol,
            scheme_code=scheme_code,
            cache_hit=False,
            status_code=None,
            success=False,
            error_message="feature_flag_disabled",
            request_cost=0,
        )
        if stale:
            return _service_ok(
                endpoint_name,
                stale["response_json"],
                stale["fetched_at"],
                "cache",
                stale=True,
                warning=f"Using stale cache because {endpoint_name} is disabled by feature flag.",
            )
        return _service_error(endpoint_name, "endpoint_disabled", UNAVAILABLE_MESSAGE, stale=True)

    disabled = _disabled_until(endpoint_name, now)
    if disabled:
        log_provider_usage(
            provider=PROVIDER,
            endpoint=endpoint_name,
            symbol=symbol,
            scheme_code=scheme_code,
            cache_hit=False,
            status_code=None,
            success=False,
            error_message="endpoint_temporarily_disabled",
            request_cost=0,
        )
        if stale:
            return _service_ok(
                endpoint_name,
                stale["response_json"],
                stale["fetched_at"],
                "cache",
                stale=True,
                warning=f"Using stale cache because {endpoint_name} is temporarily disabled.",
            )
        return _service_error(endpoint_name, "endpoint_disabled", UNAVAILABLE_MESSAGE, stale=True)

    quota = evaluate_quota(scheduled=False, now=now)
    if not quota.allowed:
        log_provider_usage(
            provider=PROVIDER,
            endpoint=endpoint_name,
            symbol=symbol,
            scheme_code=scheme_code,
            cache_hit=False,
            status_code=None,
            success=False,
            error_message=f"quota_guard:{quota.reason}",
            request_cost=0,
        )
        if stale:
            return _service_ok(
                endpoint_name,
                stale["response_json"],
                stale["fetched_at"],
                "cache",
                stale=True,
                warning=f"Using stale cache because IndianAPI quota guard blocked live call ({quota.reason}).",
            )
        return _service_error(endpoint_name, "quota_guard_blocked", UNAVAILABLE_MESSAGE, stale=True)

    client = IndianAPIClient()
    if not client.api_key:
        log_provider_usage(
            provider=PROVIDER,
            endpoint=endpoint_name,
            symbol=symbol,
            scheme_code=scheme_code,
            cache_hit=False,
            status_code=None,
            success=False,
            error_message="missing_api_key",
            request_cost=0,
        )
        if stale:
            return _service_ok(endpoint_name, stale["response_json"], stale["fetched_at"], "cache", stale=True)
        return _service_error(endpoint_name, "missing_api_key", UNAVAILABLE_MESSAGE, stale=optional)

    result = fetcher(client)
    status = (result.get("error") or {}).get("status")

    if result.get("ok"):
        fetched_at = now.isoformat()
        data = result.get("data")
        _mark_success(endpoint_name)
        _write_generic_cache(endpoint_name, cache_key, params, data, fetched_at, now + timedelta(seconds=ttl_seconds))
        _write_normalized_cache(normalized_table, normalized_key or params, endpoint_name, data, fetched_at)
        _log_ingestion(endpoint_name, "success", params, status=200)
        log_provider_usage(
            provider=PROVIDER,
            endpoint=endpoint_name,
            symbol=symbol,
            scheme_code=scheme_code,
            cache_hit=False,
            status_code=200,
            success=True,
            request_cost=1,
        )
        return _service_ok(endpoint_name, data, fetched_at, PROVIDER, stale=False)

    _mark_failure(endpoint_name, status, (result.get("error") or {}).get("message"))
    _log_ingestion(endpoint_name, "failed", params, status=status, error=result.get("error"))
    log_provider_usage(
        provider=PROVIDER,
        endpoint=endpoint_name,
        symbol=symbol,
        scheme_code=scheme_code,
        cache_hit=False,
        status_code=status,
        success=False,
        error_message=(result.get("error") or {}).get("message"),
        request_cost=1,
    )

    if stale:
        return _service_ok(
            endpoint_name,
            stale["response_json"],
            stale["fetched_at"],
            "cache",
            stale=True,
            warning=f"Provider failed for {endpoint_name}. Returned stale cached data.",
        )

    error = result.get("error") or {}
    message = UNAVAILABLE_MESSAGE if optional or status == 403 else error.get("message") or UNAVAILABLE_MESSAGE
    return _service_error(endpoint_name, error.get("code") or "provider_error", message, status=status, stale=optional)


def _service_ok(
    endpoint: str,
    data: Any,
    fetched_at: str | None,
    source: str,
    stale: bool,
    warning: str | None = None,
) -> dict[str, Any]:
    response = {
        "ok": True,
        "provider": PROVIDER,
        "source": source,
        "endpoint": endpoint,
        "data": data,
        "fetchedAt": fetched_at,
        "stale": stale,
    }
    if warning:
        response["warning"] = warning
    return response


def _service_error(endpoint: str, code: str, message: str, status: int | None = None, stale: bool = False) -> dict[str, Any]:
    error = {"code": code, "message": message}
    if status is not None:
        error["status"] = status
    return {"ok": False, "provider": PROVIDER, "source": PROVIDER, "endpoint": endpoint, "error": error, "stale": stale}


def _read_generic_cache(endpoint: str, cache_key: str, now: datetime, allow_stale: bool) -> dict[str, Any] | None:
    if not supabase:
        return None
    try:
        response = (
            supabase.table("provider_response_cache")
            .select("*")
            .eq("provider", PROVIDER)
            .eq("endpoint", endpoint)
            .eq("cache_key", cache_key)
            .eq("status", "success")
            .order("fetched_at", desc=True)
            .limit(1)
            .execute()
        )
        row = (response.data or [None])[0]
        if not row:
            return None
        expires_at = _parse_dt(row.get("expires_at"))
        if allow_stale or not expires_at or expires_at > now:
            return row
    except Exception as exc:
        logger.warning("IndianAPI cache read failed for %s: %s", endpoint, exc)
    return None


def _write_generic_cache(endpoint: str, cache_key: str, params: dict[str, Any], data: Any, fetched_at: str, expires_at: datetime) -> None:
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
        logger.warning("IndianAPI cache write failed for %s: %s", endpoint, exc)


def _write_normalized_cache(table: str | None, key: dict[str, Any], endpoint: str, data: Any, fetched_at: str) -> None:
    if not table or not supabase:
        return
    if table == "mutual_funds":
        return
    row = {
        **{k: v for k, v in key.items() if v not in (None, "")},
        "provider": PROVIDER,
        "endpoint": endpoint,
        "response_json": data,
        "fetched_at": fetched_at,
        "updated_at": fetched_at,
    }
    try:
        conflict = "provider,endpoint," + ",".join(row_key for row_key in key.keys() if row_key in row)
        supabase.table(table).upsert(row, on_conflict=conflict).execute()
    except Exception as exc:
        logger.warning("IndianAPI normalized cache write failed for %s: %s", table, exc)


def _disabled_until(endpoint: str, now: datetime) -> datetime | None:
    if not supabase:
        return None
    try:
        response = (
            supabase.table("provider_endpoint_health")
            .select("disabled_until")
            .eq("provider", PROVIDER)
            .eq("endpoint_name", endpoint)
            .limit(1)
            .execute()
        )
        row = (response.data or [None])[0]
        disabled = _parse_dt((row or {}).get("disabled_until"))
        if disabled and disabled > now:
            return disabled
    except Exception as exc:
        logger.warning("IndianAPI health read failed for %s: %s", endpoint, exc)
    return None


def _mark_success(endpoint: str) -> None:
    if not supabase:
        return
    now = _now().isoformat()
    row = {
        "provider": PROVIDER,
        "endpoint_name": endpoint,
        "last_success_at": now,
        "last_status_code": 200,
        "failure_count": 0,
        "disabled_until": None,
        "last_error_message": None,
    }
    try:
        supabase.table("provider_endpoint_health").upsert(row, on_conflict="provider,endpoint_name").execute()
    except Exception as exc:
        logger.warning("IndianAPI health success write failed for %s: %s", endpoint, exc)


def _mark_failure(endpoint: str, status: int | None, message: str | None) -> None:
    if not supabase:
        return
    now = _now()
    disabled_until = now + timedelta(seconds=DISABLE_SECONDS_ON_403) if status == 403 else None
    failure_count = 1
    try:
        response = (
            supabase.table("provider_endpoint_health")
            .select("failure_count")
            .eq("provider", PROVIDER)
            .eq("endpoint_name", endpoint)
            .limit(1)
            .execute()
        )
        row = (response.data or [None])[0] or {}
        failure_count = int(row.get("failure_count") or 0) + 1
    except Exception:
        pass

    row = {
        "provider": PROVIDER,
        "endpoint_name": endpoint,
        "last_failure_at": now.isoformat(),
        "last_status_code": status,
        "failure_count": failure_count,
        "disabled_until": disabled_until.isoformat() if disabled_until else None,
        "last_error_message": (message or UNAVAILABLE_MESSAGE)[:500],
    }
    try:
        supabase.table("provider_endpoint_health").upsert(row, on_conflict="provider,endpoint_name").execute()
    except Exception as exc:
        logger.warning("IndianAPI health failure write failed for %s: %s", endpoint, exc)


def _log_ingestion(endpoint: str, status_text: str, params: dict[str, Any], status: int | None = None, error: Any = None) -> None:
    if not supabase:
        return
    row = {
        "provider": PROVIDER,
        "endpoint": endpoint,
        "status": status_text,
        "status_code": status,
        "params_json": params,
        "error_json": error or None,
        "created_at": _now().isoformat(),
    }
    try:
        supabase.table("provider_ingestion_logs").insert(row).execute()
    except Exception as exc:
        logger.warning("IndianAPI ingestion log failed for %s: %s", endpoint, exc)


def _cache_key(endpoint: str, params: dict[str, Any]) -> str:
    payload = json.dumps({"endpoint": endpoint, "params": params}, sort_keys=True, default=str)
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


def _endpoint_feature_disabled(endpoint_name: str) -> bool:
    env_map = {
        "corporate_actions": "ENABLE_CORPORATE_ACTIONS_SYNC",
        "recent_announcements": "ENABLE_STOCK_NEWS",
        "stock_target_price": "ENABLE_ANALYST_DATA",
        "stock_forecasts": "ENABLE_ANALYST_DATA",
        "historical_data": "INDIANAPI_ENABLE_STOCK_HISTORY",
        "mutual_fund_search": "INDIANAPI_ENABLE_MF_ENDPOINTS",
        "mutual_funds": "INDIANAPI_ENABLE_MF_ENDPOINTS",
        "mutual_funds_details": "INDIANAPI_ENABLE_MF_ENDPOINTS",
    }
    env_name = env_map.get(endpoint_name)
    if not env_name:
        return False
    return os.getenv(env_name, "0").strip().lower() not in {"1", "true", "yes", "on"}


def _extract_symbol_and_scheme(params: dict[str, Any]) -> tuple[str | None, str | None]:
    symbol = params.get("name") or params.get("stock_name") or params.get("symbol")
    scheme_code = params.get("scheme_code") or params.get("fund_id")
    if scheme_code is None and "stock_name" in params and "mutual" in str(params.get("stock_name", "")).lower():
        scheme_code = str(params.get("stock_name"))
    return (str(symbol).upper() if symbol else None, str(scheme_code) if scheme_code else None)
