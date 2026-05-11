from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any

import httpx

from app.services.provider_usage import log_provider_usage

logger = logging.getLogger(__name__)

PROVIDER = "mfapi"
BASE_URL = os.getenv("MFAPI_BASE_URL", "https://api.mfapi.in").rstrip("/")
TIMEOUT_SECONDS = float(os.getenv("MFAPI_TIMEOUT_SECONDS", "20"))
MAX_RETRIES = max(int(os.getenv("MFAPI_MAX_RETRIES", "1")), 0)


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
