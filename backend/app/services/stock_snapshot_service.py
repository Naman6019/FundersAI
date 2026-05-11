from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.services import cache_policy
from app.repositories.stock_repository import StockRepository


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _sum_recent(values: list[float | None], count: int = 4) -> float | None:
    clean = [value for value in values[:count] if value is not None]
    if len(clean) < count:
        return None
    return float(sum(clean))


def build_stock_core_snapshot_row(symbol: str, repo: StockRepository | None = None) -> dict[str, Any]:
    repository = repo or StockRepository()
    clean_symbol = symbol.strip().upper()
    profile = repository.get_stock_profile(clean_symbol)
    ratios = repository.get_latest_ratios(clean_symbol)
    prices = repository.get_recent_price_history(clean_symbol, limit=2)
    quarterly = repository.get_financial_statements(clean_symbol, period_type="quarterly", limit=8)

    latest_price = prices[-1] if prices else None
    previous_price = prices[-2] if len(prices) > 1 else None

    close_price = _to_float(getattr(latest_price, "close", None))
    previous_close = _to_float(getattr(previous_price, "close", None))
    volume = _to_float(getattr(latest_price, "volume", None))
    change_percent = None
    if close_price is not None and previous_close not in (None, 0):
        change_percent = ((close_price - previous_close) / previous_close) * 100

    revenue_ttm = _sum_recent([_to_float(statement.revenue) for statement in quarterly])
    net_profit_ttm = _sum_recent([_to_float(statement.net_profit) for statement in quarterly])
    eps_ttm = _sum_recent([_to_float(statement.eps) for statement in quarterly])

    operating_margin = None
    net_profit_margin = None
    if revenue_ttm not in (None, 0):
        latest_operating_profit = _to_float(quarterly[0].operating_profit) if quarterly else None
        latest_net_profit = _to_float(quarterly[0].net_profit) if quarterly else None
        if latest_operating_profit is not None:
            operating_margin = (latest_operating_profit / revenue_ttm) * 100
        if latest_net_profit is not None:
            net_profit_margin = (latest_net_profit / revenue_ttm) * 100

    snapshot = {
        "symbol": clean_symbol,
        "company_name": getattr(profile, "company_name", None) if profile else None,
        "exchange": getattr(profile, "exchange", None) if profile else "NSE",
        "sector": getattr(profile, "sector", None) if profile else None,
        "industry": getattr(profile, "industry", None) if profile else None,
        "market_cap": _to_float(getattr(ratios, "market_cap", None)) if ratios else None,
        "close_price": close_price,
        "previous_close": previous_close,
        "change_percent": change_percent,
        "volume": volume,
        "price_date": getattr(latest_price, "date", None).isoformat() if latest_price else None,
        "revenue_ttm": revenue_ttm,
        "net_profit_ttm": net_profit_ttm,
        "eps_ttm": eps_ttm,
        "pe_ratio": _to_float(getattr(ratios, "pe", None)) if ratios else None,
        "pb_ratio": _to_float(getattr(ratios, "pb", None)) if ratios else None,
        "roe": _to_float(getattr(ratios, "roe", None)) if ratios else None,
        "roce": _to_float(getattr(ratios, "roce", None)) if ratios else None,
        "debt_to_equity": _to_float(getattr(ratios, "debt_to_equity", None)) if ratios else None,
        "operating_margin": operating_margin,
        "net_profit_margin": net_profit_margin,
        "dividend_yield": _to_float(getattr(ratios, "dividend_yield", None)) if ratios else None,
        "data_source": "supabase_normalized",
        "provider_payload": None,
    }
    return snapshot


def refresh_stock_core_snapshot(symbol: str, repo: StockRepository | None = None) -> dict[str, Any]:
    repository = repo or StockRepository()
    row = build_stock_core_snapshot_row(symbol, repository)
    repository.upsert_stock_core_snapshot_rows([row])
    return row


def get_stock_snapshot_with_freshness(symbol: str, repo: StockRepository | None = None) -> dict[str, Any]:
    repository = repo or StockRepository()
    row = repository.get_stock_core_snapshot(symbol)
    if not row:
        return {"row": None, "stale": True, "warning": "No stock_core_snapshot is available."}
    stale = not cache_policy.is_fresh(row.get("last_updated"), "stock_fundamentals")
    warning = "Stock snapshot is stale." if stale else None
    return {"row": row, "stale": stale, "warning": warning}
