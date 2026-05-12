from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

from app.database import supabase
from app.providers import get_fundamentals_provider
from app.providers.base import normalize_symbol
from app.providers.yfinance_provider import YFinanceProvider
from app.services.comparison_reasoning import build_stock_why_better
from app.services import indianapi_service
from app.services.stock_snapshot_service import get_stock_snapshot_with_freshness
from app.stock_universe import load_stock_universe, resolve_stock_symbol

logger = logging.getLogger(__name__)
INDIANAPI_STOCK_EVENTS_ENABLED = os.getenv("INDIANAPI_STOCK_EVENTS_ENABLED", "0").strip().lower() in {"1", "true", "yes", "on"}


def _rows(table: str, symbol: str, order: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
    if not supabase:
        return []
    try:
        query = supabase.table(table).select("*").eq("symbol", normalize_symbol(symbol))
        if order:
            query = query.order(order, desc=True)
        return query.limit(limit).execute().data or []
    except Exception as exc:
        logger.warning("Query failed for %s/%s: %s", table, symbol, exc)
        return []


def _one(table: str, symbol: str, order: str | None = None) -> dict[str, Any] | None:
    rows = _rows(table, symbol, order=order, limit=1)
    return rows[0] if rows else None


def _num(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _empty_comparison_item(symbol: str, message: str) -> dict[str, Any]:
    return {
        "symbol": normalize_symbol(symbol),
        "name": normalize_symbol(symbol) or symbol,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "price": None,
        "change_pct": None,
        "pe_ratio": None,
        "market_cap": None,
        "beta": None,
        "alpha_vs_nifty": None,
        "historical_period": None,
        "rsi_14d": None,
        "tv_recommendation": None,
        "fundamentals": _empty_fundamentals(),
        "ratios": {},
        "financials": {"quarterly": [], "annual": []},
        "shareholding": {},
        "price_history": [],
        "data_quality": {"missing_fields": ["symbol"], "message": message},
        "source_summary": {
            "metadata": None,
            "prices": None,
            "ratios": None,
            "shareholding": None,
        },
        "error": message,
    }


def _empty_fundamentals() -> dict[str, Any]:
    return {
        "industry": None,
        "revenue_qtr": None,
        "net_profit_qtr": None,
        "revenue_ann": None,
        "net_profit_ann": None,
        "market_cap": None,
        "pe": None,
        "pb": None,
        "ps": None,
        "ev_ebitda": None,
        "roe": None,
        "roce": None,
        "roa": None,
        "debt_to_equity": None,
        "dividend_yield": None,
        "sales_growth_1y": None,
        "sales_growth_3y": None,
        "profit_growth_1y": None,
        "profit_growth_3y": None,
        "eps_growth_1y": None,
        "eps_growth_3y": None,
        "eps_ttm": None,
        "promoter_holding": None,
        "fii_holding": None,
        "dii_holding": None,
        "public_holding": None,
        "operating_margin": None,
        "net_profit_margin": None,
        "source": None,
    }


def _provider_context(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": bool(result.get("ok")),
        "data": result.get("data") if result.get("ok") else None,
        "source": result.get("source"),
        "provider": result.get("provider"),
        "fetchedAt": result.get("fetchedAt"),
        "stale": result.get("stale", False),
        "error": result.get("error") if not result.get("ok") else None,
    }


def _metadata_from_indianapi(symbol: str, data: Any) -> dict[str, Any] | None:
    row = _first_dict(data)
    if not row:
        return None
    return {
        "symbol": normalize_symbol(row.get("tickerId") or row.get("symbol") or symbol),
        "exchange": row.get("exchange") or "NSE",
        "company_name": row.get("companyName") or row.get("name") or row.get("company_name") or symbol,
        "isin": row.get("isin") or row.get("ISIN"),
        "series": row.get("series"),
        "sector": row.get("sector") or row.get("mgSector"),
        "industry": row.get("industry") or row.get("mgIndustry"),
        "is_active": True,
        "source": "indianapi",
    }


def _resolve_indianapi_stock_symbol(entity: str) -> str | None:
    result = indianapi_service.resolve_stock(entity)
    if not result.get("ok"):
        return None
    for row in _iter_dicts(result.get("data")):
        value = row.get("tickerId") or row.get("symbol") or row.get("nseCode") or row.get("nse-code")
        if value:
            return normalize_symbol(str(value))
    return None


def _first_dict(data: Any) -> dict[str, Any]:
    if isinstance(data, dict):
        return data
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                return item
    return {}


def _iter_dicts(data: Any):
    if isinstance(data, dict):
        yield data
        for value in data.values():
            yield from _iter_dicts(value)
    elif isinstance(data, list):
        for item in data:
            yield from _iter_dicts(item)


def resolve_stock_request(entity: str) -> str | None:
    clean = normalize_symbol(entity)
    resolved = resolve_stock_symbol(entity) or clean
    if not resolved:
        return None
    universe = load_stock_universe()
    if resolved in universe:
        return resolved
    if (
        _one("stocks", resolved)
        or _one("stock_prices_daily", resolved, "date")
        or _one("stock_history", resolved, "date")
        or _one("stock_core_snapshot", resolved, "last_updated")
    ):
        return resolved
    return resolve_stock_symbol(entity)


def get_stock_metadata(symbol: str) -> dict[str, Any] | None:
    clean = normalize_symbol(symbol)
    row = _one("stocks", clean)
    if row:
        return row
    snapshot = _one("stock_core_snapshot", clean, "last_updated")
    if snapshot:
        return {
            "symbol": clean,
            "exchange": snapshot.get("exchange") or "NSE",
            "company_name": snapshot.get("company_name") or clean,
            "isin": None,
            "series": "EQ",
            "sector": snapshot.get("sector"),
            "industry": snapshot.get("industry"),
            "is_active": True,
            "source": "stock_core_snapshot",
        }
    universe_row = load_stock_universe().get(clean)
    if universe_row:
        return {
            "symbol": clean,
            "exchange": "NSE",
            "company_name": universe_row.get("company_name") or clean,
            "isin": universe_row.get("isin"),
            "series": "EQ",
            "sector": None,
            "industry": universe_row.get("industry"),
            "is_active": True,
            "source": "nse_universe",
        }
    legacy = _one("nifty_stocks", clean)
    if legacy:
        return {
            "symbol": clean,
            "exchange": "NSE",
            "company_name": clean,
            "industry": legacy.get("category"),
            "is_active": True,
            "source": "legacy_nifty_stocks",
        }
    return None


def get_stock_price_history(symbol: str, days: int = 365) -> list[dict[str, Any]]:
    clean = normalize_symbol(symbol)
    rows = _rows("stock_prices_daily", clean, order="date", limit=days)
    if rows:
        return list(reversed(rows))

    legacy_rows = _rows("stock_history", clean, order="date", limit=days)
    if legacy_rows:
        return [
            {
                "symbol": clean,
                "date": row.get("date"),
                "open": row.get("open"),
                "high": row.get("high"),
                "low": row.get("low"),
                "close": row.get("close"),
                "adj_close": row.get("close"),
                "volume": row.get("volume"),
                "source": "legacy_stock_history",
            }
            for row in reversed(legacy_rows)
        ]

    snapshot = _one("stock_core_snapshot", clean, "last_updated")
    if snapshot and snapshot.get("price_date") and snapshot.get("close_price") is not None:
        history = [
            {
                "symbol": clean,
                "date": snapshot.get("price_date"),
                "open": None,
                "high": None,
                "low": None,
                "close": snapshot.get("close_price"),
                "adj_close": snapshot.get("close_price"),
                "volume": snapshot.get("volume"),
                "source": snapshot.get("data_source") or "stock_core_snapshot",
            }
        ]
        prev_close = snapshot.get("previous_close")
        if prev_close is not None:
            history.insert(
                0,
                {
                    "symbol": clean,
                    "date": snapshot.get("price_date"),
                    "open": None,
                    "high": None,
                    "low": None,
                    "close": prev_close,
                    "adj_close": prev_close,
                    "volume": None,
                    "source": snapshot.get("data_source") or "stock_core_snapshot",
                },
            )
        return history
    return []


def get_stock_financials(symbol: str) -> dict[str, Any]:
    clean = normalize_symbol(symbol)
    rows = _rows("financial_statements", clean, order="period_end_date", limit=12)
    return {
        "quarterly": [row for row in rows if row.get("period_type") == "quarterly"],
        "annual": [row for row in rows if row.get("period_type") == "annual"],
    }


def _latest_shareholding(symbol: str) -> dict[str, Any] | None:
    return _one("shareholding_pattern", symbol, "period_end_date")


def _latest_ratios(symbol: str) -> dict[str, Any] | None:
    ratio_rows = _rows("ratios_snapshot", symbol, order="snapshot_date", limit=8)
    if ratio_rows:
        ratio_fields = (
            "market_cap",
            "pe",
            "pb",
            "ev_ebitda",
            "roe",
            "roce",
            "debt_to_equity",
            "dividend_yield",
            "sales_growth_3y",
            "profit_growth_3y",
            "eps_growth_3y",
            "eps_ttm",
        )
        return max(ratio_rows, key=lambda row: sum(row.get(field) is not None for field in ratio_fields))
    legacy = _one("nifty_stocks", symbol)
    if not legacy:
        return None
    return {
        "symbol": normalize_symbol(symbol),
        "snapshot_date": datetime.now(timezone.utc).date().isoformat(),
        "market_cap": legacy.get("market_cap"),
        "pe": legacy.get("pe_ratio"),
        "source": "legacy_nifty_stocks",
    }


def _has_meaningful_values(row: Any, exclude: set[str] | None = None) -> bool:
    if not isinstance(row, dict):
        return False
    ignored = exclude or set()
    return any(value is not None for key, value in row.items() if key not in ignored)


def _merge_sparse(primary: dict[str, Any] | None, fallback: dict[str, Any] | None) -> dict[str, Any]:
    if not primary:
        return fallback or {}
    if not fallback:
        return primary
    merged = dict(primary)
    for key, value in fallback.items():
        if merged.get(key) is None and value is not None:
            merged[key] = value
    primary_source = primary.get("source")
    fallback_source = fallback.get("source")
    if primary_source and fallback_source and primary_source != fallback_source:
        merged["source"] = f"{primary_source}+{fallback_source}"
    return merged


def _first_meaningful_statement(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> dict[str, Any]:
    for row in rows:
        if any(row.get(field) is not None for field in fields):
            return row
    return rows[0] if rows else {}


def _eps_ttm(quarterly_rows: list[dict[str, Any]]) -> float | None:
    values = [_num(row.get("eps")) for row in quarterly_rows]
    values = [value for value in values if value is not None][:4]
    if len(values) != 4:
        return None
    return sum(values)


def build_stock_profile(symbol: str) -> dict[str, Any]:
    clean = normalize_symbol(symbol)
    provider = get_fundamentals_provider()
    metadata = get_stock_metadata(clean)
    indianapi_profile = indianapi_service.get_stock_research_profile(clean)
    try:
        provider_profile = None if metadata else provider.get_company_profile(clean)
    except Exception as exc:
        logger.warning("Provider profile failed for %s via %s: %s", clean, provider.name, exc)
        provider_profile = None

    metadata = metadata or provider_profile or _metadata_from_indianapi(clean, indianapi_profile.get("data")) or {"symbol": clean}
    prices = get_stock_price_history(clean, days=2)
    try:
        provider_ratios = provider.get_ratios_snapshot(clean)
    except Exception as exc:
        logger.warning("Provider ratios failed for %s via %s: %s", clean, provider.name, exc)
        provider_ratios = None
    ratios = _merge_sparse(provider_ratios, _latest_ratios(clean))

    try:
        shareholding_rows = provider.get_shareholding(clean)
    except Exception as exc:
        logger.warning("Provider shareholding failed for %s via %s: %s", clean, provider.name, exc)
        shareholding_rows = []
    provider_shareholding = shareholding_rows[0] if shareholding_rows else None
    if not _has_meaningful_values(provider_shareholding, {"symbol", "period_end_date", "source"}):
        provider_shareholding = None
    shareholding = provider_shareholding or _latest_shareholding(clean)
    shareholding_source = shareholding.get("source") if isinstance(shareholding, dict) else None
    indianapi_actions = indianapi_service.get_stock_corporate_actions(clean) if INDIANAPI_STOCK_EVENTS_ENABLED else {}
    indianapi_announcements = indianapi_service.get_stock_recent_announcements(clean) if INDIANAPI_STOCK_EVENTS_ENABLED else {}
    return {
        "symbol": clean,
        "metadata": metadata,
        "latest_price": prices[-1] if prices else None,
        "ratios": ratios,
        "shareholding": shareholding or {},
        "indianapi": {
            "profile": _provider_context(indianapi_profile),
            "corporate_actions": _provider_context(indianapi_actions),
            "recent_announcements": _provider_context(indianapi_announcements),
        },
        "source_summary": {
            "metadata": metadata.get("source") or provider.name,
            "prices": (prices[-1] or {}).get("source") if prices else None,
            "ratios": ratios.get("source") if isinstance(ratios, dict) else None,
            "shareholding": shareholding_source,
            "indianapi_fetched_at": indianapi_profile.get("fetchedAt"),
        },
    }


def _comparison_item(symbol: str) -> dict[str, Any]:
    clean = normalize_symbol(symbol)
    snapshot_context = get_stock_snapshot_with_freshness(clean)
    snapshot = snapshot_context.get("row") or {}
    metadata = get_stock_metadata(clean) or {"symbol": clean}
    prices = get_stock_price_history(clean, days=365)
    financials = get_stock_financials(clean)
    quarterly = financials["quarterly"]
    annual = financials["annual"]
    latest_quarter = _first_meaningful_statement(quarterly, ("revenue", "net_profit", "eps"))
    latest_annual = _first_meaningful_statement(annual, ("revenue", "net_profit"))
    ratios = _latest_ratios(clean) or {}
    shareholding = _latest_shareholding(clean) or {}
    latest = prices[-1] if prices else {}
    previous = prices[-2] if len(prices) > 1 else {}
    close = _num(snapshot.get("close_price")) if snapshot.get("close_price") is not None else _num(latest.get("close"))
    prev_close = _num(previous.get("close"))
    if prev_close in (None, 0):
        prev_close = _num(snapshot.get("previous_close"))
    change_pct = ((close - prev_close) / prev_close * 100) if close is not None and prev_close not in (None, 0) else None

    fundamentals = {
        **_empty_fundamentals(),
        "industry": snapshot.get("industry") or metadata.get("industry"),
        "revenue_qtr": latest_quarter.get("revenue") or snapshot.get("revenue_ttm"),
        "net_profit_qtr": latest_quarter.get("net_profit") or snapshot.get("net_profit_ttm"),
        "revenue_ann": latest_annual.get("revenue") or snapshot.get("revenue_ttm"),
        "net_profit_ann": latest_annual.get("net_profit") or snapshot.get("net_profit_ttm"),
        "market_cap": snapshot.get("market_cap") if snapshot.get("market_cap") is not None else ratios.get("market_cap"),
        "pe": snapshot.get("pe_ratio") if snapshot.get("pe_ratio") is not None else ratios.get("pe"),
        "pb": snapshot.get("pb_ratio") if snapshot.get("pb_ratio") is not None else ratios.get("pb"),
        "ps": ratios.get("ps"),
        "ev_ebitda": ratios.get("ev_ebitda"),
        "roe": snapshot.get("roe") if snapshot.get("roe") is not None else ratios.get("roe"),
        "roce": snapshot.get("roce") if snapshot.get("roce") is not None else ratios.get("roce"),
        "roa": ratios.get("roa"),
        "debt_to_equity": snapshot.get("debt_to_equity") if snapshot.get("debt_to_equity") is not None else ratios.get("debt_to_equity"),
        "dividend_yield": snapshot.get("dividend_yield") if snapshot.get("dividend_yield") is not None else ratios.get("dividend_yield"),
        "sales_growth_1y": ratios.get("sales_growth_1y"),
        "sales_growth_3y": ratios.get("sales_growth_3y"),
        "profit_growth_1y": ratios.get("profit_growth_1y"),
        "profit_growth_3y": ratios.get("profit_growth_3y"),
        "eps_growth_1y": ratios.get("eps_growth_1y"),
        "eps_growth_3y": ratios.get("eps_growth_3y"),
        "eps_ttm": snapshot.get("eps_ttm") if snapshot.get("eps_ttm") is not None else (ratios.get("eps_ttm") or _eps_ttm(quarterly)),
        "promoter_holding": shareholding.get("promoter_holding"),
        "fii_holding": shareholding.get("fii_holding"),
        "dii_holding": shareholding.get("dii_holding"),
        "public_holding": shareholding.get("public_holding"),
        "operating_margin": snapshot.get("operating_margin"),
        "net_profit_margin": snapshot.get("net_profit_margin"),
        "source": ratios.get("source") or shareholding.get("source"),
    }
    missing = [key for key, value in fundamentals.items() if value is None and key != "source"]
    data_quality = {
        "missing_fields": missing,
        "message": "Some fundamentals are unavailable from local Supabase data." if missing else "Complete for requested fields.",
        "coverage_status": "incomplete" if missing else "complete",
    }
    if snapshot_context.get("stale"):
        data_quality["stale_warning"] = snapshot_context.get("warning") or "Data may be stale."
    return {
        "symbol": clean,
        "name": metadata.get("company_name") or clean,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "price": close,
        "change_pct": round(change_pct, 2) if change_pct is not None else None,
        "pe_ratio": fundamentals.get("pe"),
        "market_cap": fundamentals.get("market_cap"),
        "enterprise_value": ratios.get("enterprise_value"),
        "beta": None,
        "alpha_vs_nifty": None,
        "historical_period": "1y",
        "rsi_14d": None,
        "tv_recommendation": None,
        "fundamentals": fundamentals,
        "ratios": ratios,
        "financials": financials,
        "shareholding": shareholding,
        "price_history": prices,
        "data_quality": data_quality,
        "source_summary": {
            "metadata": metadata.get("source"),
            "prices": (latest or {}).get("source") if latest else None,
            "ratios": ratios.get("source"),
            "shareholding": shareholding.get("source") if isinstance(shareholding, dict) else None,
            "snapshot_last_updated": snapshot.get("last_updated"),
            "price_date": snapshot.get("price_date"),
            "stale": bool(snapshot_context.get("stale")),
            "stale_warning": snapshot_context.get("warning"),
        },
    }


def build_stock_compare(symbols: list[str] | str) -> dict[str, Any]:
    requested = symbols.split(",") if isinstance(symbols, str) else symbols
    requested = [item.strip() for item in requested if item and item.strip()]
    comparison: dict[str, Any] = {}
    available: list[str] = []
    unavailable: list[str] = []
    metrics: dict[str, Any] = {}
    price_history: dict[str, Any] = {}
    fundamentals: dict[str, Any] = {}
    ratios: dict[str, Any] = {}
    data_quality: dict[str, Any] = {}
    source_summary: dict[str, Any] = {}

    for entity in requested:
        resolved = resolve_stock_request(entity)
        if not resolved:
            unavailable.append(entity)
            item = _empty_comparison_item(entity, "Symbol could not be resolved.")
            comparison[entity] = item
            metrics[entity] = _comparison_metrics(item)
            price_history[entity] = item["price_history"]
            fundamentals[entity] = item["financials"]
            ratios[entity] = item["ratios"]
            data_quality[entity] = item["data_quality"]
            source_summary[entity] = item["source_summary"]
            continue

        try:
            item = _comparison_item(resolved)
        except Exception as exc:
            logger.warning("Stock comparison failed for %s: %s", resolved, exc)
            unavailable.append(entity)
            item = _empty_comparison_item(resolved, "Data lookup failed for this symbol.")
            comparison[entity] = item
            metrics[entity] = _comparison_metrics(item)
            price_history[entity] = item["price_history"]
            fundamentals[entity] = item["financials"]
            ratios[entity] = item["ratios"]
            data_quality[entity] = item["data_quality"]
            source_summary[entity] = item["source_summary"]
            continue

        available.append(resolved)
        comparison[entity] = item
        metrics[resolved] = _comparison_metrics(item)
        price_history[resolved] = item["price_history"]
        fundamentals[resolved] = item["financials"]
        ratios[resolved] = item["ratios"]
        data_quality[resolved] = item["data_quality"]
        source_summary[resolved] = item["source_summary"]

    why_better = build_stock_why_better(comparison)

    return {
        "asset_type": "stocks",
        "symbols": requested,
        "available": available,
        "unavailable": unavailable,
        "metrics": metrics,
        "price_history": price_history,
        "fundamentals": fundamentals,
        "ratios": ratios,
        "data_quality": data_quality,
        "source_summary": source_summary,
        "source_freshness": why_better.get("source_freshness"),
        "why_better": why_better,
        "verdict_context": why_better.get("verdict_context"),
        "comparison": comparison,
    }


def _comparison_metrics(item: dict[str, Any]) -> dict[str, Any]:
    fundamentals = item.get("fundamentals") or {}
    return {
        "price": item.get("price"),
        "change_pct": item.get("change_pct"),
        "market_cap": item.get("market_cap"),
        "pe": item.get("pe_ratio"),
        "pb": fundamentals.get("pb"),
        "ev_ebitda": fundamentals.get("ev_ebitda"),
        "roe": fundamentals.get("roe"),
        "roce": fundamentals.get("roce"),
        "debt_to_equity": fundamentals.get("debt_to_equity"),
        "dividend_yield": fundamentals.get("dividend_yield"),
    }
