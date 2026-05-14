from __future__ import annotations

import logging
import os
import time
from datetime import datetime
from typing import Any

import httpx

from app.services.provider_usage import log_provider_usage

logger = logging.getLogger(__name__)

PROVIDER = "mfdata"
BASE_URL = os.getenv("MFDATA_BASE_URL", "https://mfdata.in/api/v1").rstrip("/")
TIMEOUT_SECONDS = float(os.getenv("MFDATA_TIMEOUT_SECONDS", "20"))
MAX_RETRIES = max(int(os.getenv("MFDATA_MAX_RETRIES", "1")), 0)


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
                if response.status_code in {429, 500, 502, 503, 504} and attempt < MAX_RETRIES:
                    time.sleep(0.5 * (attempt + 1))
                    continue
                _log(endpoint, scheme_code, status_code, False, last_error)
                return {"ok": False, "error": last_error, "status_code": status_code, "data": None}
            payload = response.json()
            _log(endpoint, scheme_code, status_code, True, None)
            return {"ok": True, "error": None, "status_code": status_code, "data": payload}
        except Exception as exc:
            last_error = str(exc)
            if attempt < MAX_RETRIES:
                time.sleep(0.5 * (attempt + 1))
                continue
    _log(endpoint, scheme_code, status_code, False, last_error or "request_error")
    return {"ok": False, "error": last_error or "request_error", "status_code": status_code, "data": None}


def get_scheme_details(scheme_code: str) -> dict[str, Any]:
    code = str(scheme_code)
    result = _request(f"/schemes/{code}", scheme_code=code)
    payload = _payload_data(result)
    if not isinstance(payload, dict):
        return {"ok": False, "data": None, "error": result.get("error") or "invalid_payload"}
    return {"ok": bool(result.get("ok")), "data": _normalize_scheme(payload, code), "error": result.get("error")}


def get_nav_history(scheme_code: str, limit: int = 252) -> dict[str, Any]:
    code = str(scheme_code)
    result = _request(f"/schemes/{code}/nav/history", {"limit": limit}, scheme_code=code)
    rows = _payload_data(result)
    if not isinstance(rows, list):
        return {"ok": False, "data": [], "error": result.get("error") or "invalid_payload"}
    normalized = []
    for row in rows:
        if not isinstance(row, dict):
            continue
        nav_date = _to_date_iso(row.get("date") or row.get("nav_date"))
        nav = _to_float(row.get("nav"))
        if nav_date and nav is not None:
            normalized.append({"scheme_code": code, "nav_date": nav_date, "nav": nav, "data_source": PROVIDER})
    return {"ok": bool(result.get("ok")), "data": normalized, "error": result.get("error")}


def get_family_holdings(family_id: str | int, scheme_code: str | None = None) -> dict[str, Any]:
    result = _request(f"/families/{family_id}/holdings", scheme_code=scheme_code)
    payload = _payload_data(result)
    if not isinstance(payload, dict):
        return {"ok": False, "data": [], "month": None, "error": result.get("error") or "invalid_payload"}
    rows = []
    month = payload.get("month")
    for holding_type in ("equity", "debt", "other"):
        for item in payload.get(holding_type) or []:
            if not isinstance(item, dict):
                continue
            rows.append({
                "scheme_code": str(scheme_code) if scheme_code else None,
                "family_id": str(family_id),
                "as_of_date": _month_to_date(month) or datetime.now().date().replace(day=1).isoformat(),
                "holding_type": holding_type,
                "security_name": item.get("name") or item.get("security_name"),
                "isin": item.get("isin") or "",
                "sector": item.get("sector"),
                "weight_pct": _to_float(item.get("weight_pct") or item.get("weight")),
                "quantity": _to_float(item.get("quantity")),
                "market_value_cr": _to_float(item.get("market_value_cr") or item.get("market_value")),
                "source": PROVIDER,
                "provider_payload": item,
            })
    return {"ok": bool(result.get("ok")), "data": rows, "month": month, "error": result.get("error")}


def get_family_sectors(family_id: str | int, scheme_code: str | None = None) -> dict[str, Any]:
    result = _request(f"/families/{family_id}/sectors", scheme_code=scheme_code)
    rows = _payload_data(result)
    if not isinstance(rows, list):
        return {"ok": False, "data": [], "error": result.get("error") or "invalid_payload"}
    normalized = []
    for item in rows:
        if not isinstance(item, dict):
            continue
        normalized.append({
            "scheme_code": str(scheme_code) if scheme_code else None,
            "family_id": str(family_id),
            "sector": item.get("sector"),
            "weight_pct": _to_float(item.get("weight_pct") or item.get("weight")),
            "stock_count": _to_int(item.get("stock_count")),
            "market_value_cr": _to_float(item.get("market_value_cr") or item.get("market_value")),
            "source": PROVIDER,
            "provider_payload": item,
        })
    return {"ok": bool(result.get("ok")), "data": normalized, "error": result.get("error")}


def _normalize_scheme(data: dict[str, Any], scheme_code: str) -> dict[str, Any]:
    returns = data.get("returns") if isinstance(data.get("returns"), dict) else {}
    ratios = data.get("ratios") if isinstance(data.get("ratios"), dict) else {}
    return {
        "scheme_code": str(data.get("scheme_code") or scheme_code),
        "scheme_name": data.get("scheme_name"),
        "amc_name": data.get("amc") or data.get("amc_name"),
        "category": data.get("category"),
        "sub_category": data.get("sub_category"),
        "plan_type": data.get("plan_type"),
        "option_type": data.get("option_type"),
        "fund_type": data.get("fund_type"),
        "nav": _to_float(data.get("nav")),
        "nav_date": _to_date_iso(data.get("nav_date")),
        "return_1m": _return_value(returns, "1m"),
        "return_3m": _return_value(returns, "3m"),
        "return_6m": _return_value(returns, "6m"),
        "return_1y": _return_value(returns, "1y"),
        "return_3y": _return_value(returns, "3y"),
        "return_5y": _return_value(returns, "5y"),
        "expense_ratio": _to_float(data.get("expense_ratio")),
        "aum": _to_float(data.get("aum_cr") or data.get("aum")),
        "benchmark": data.get("benchmark"),
        "fund_manager": data.get("fund_manager") or data.get("fundManager") or data.get("manager"),
        "risk_level": data.get("risk_level") or data.get("riskometer"),
        "alpha": _to_float(ratios.get("alpha")),
        "beta": _to_float(ratios.get("beta")),
        "sharpe_ratio": _to_float(ratios.get("sharpe") or ratios.get("sharpe_ratio")),
        "data_source": PROVIDER,
        "provider_payload": data,
    }


def _return_value(returns: dict[str, Any], key: str) -> float | None:
    value = returns.get(key)
    if isinstance(value, dict):
        value = value.get("value")
    return _to_float(value)


def _payload_data(result: dict[str, Any]) -> Any:
    payload = result.get("data")
    if isinstance(payload, dict) and "data" in payload and payload.get("status") in {"success", "SUCCESS", None}:
        return payload.get("data")
    return payload


def _log(endpoint: str, scheme_code: str | None, status_code: int | None, success: bool, error: str | None) -> None:
    log_provider_usage(
        provider=PROVIDER,
        endpoint=endpoint,
        scheme_code=scheme_code,
        cache_hit=False,
        status_code=status_code,
        success=success,
        error_message=error,
        request_cost=1,
    )


def _to_date_iso(value: Any) -> str | None:
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d-%b-%Y"):
        try:
            return datetime.strptime(raw[:11], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _month_to_date(value: Any) -> str | None:
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m", "%b %Y", "%B %Y"):
        try:
            return datetime.strptime(raw, fmt).date().replace(day=1).isoformat()
        except ValueError:
            continue
    return None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return None


def _to_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None
