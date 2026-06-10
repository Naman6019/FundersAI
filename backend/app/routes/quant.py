from fastapi import APIRouter, HTTPException, Query
from typing import Optional, Any
from datetime import datetime, timezone
from dataclasses import asdict
import logging

logger = logging.getLogger(__name__)

from app.repositories.stock_repository import StockRepository
from app.models.stock_models import StockProfile, FinancialStatement, StockPriceDaily, RatioSnapshot
from app.providers.manual_provider import ManualFundamentalsProvider
from app.providers.finedge_provider import FinEdgeProvider
from app.providers.indianapi_provider import IndianAPIProvider
from app.providers.nse_provider import NSEProvider
from app.providers.yfinance_provider import YFinanceProvider
from app.stock_universe import load_stock_universe
from app.services.quant_service import (
    build_stock_compare,
    build_stock_profile,
    get_stock_financials as get_stock_financials_service,
    get_stock_price_history as get_stock_price_history_service,
)

router = APIRouter(prefix="/api/quant", tags=["quant"])
repository = StockRepository()

class ProviderRegistry:
    @staticmethod
    def get_status() -> dict[str, list[str]]:
        providers = [
            ManualFundamentalsProvider(),
            FinEdgeProvider(),
            IndianAPIProvider(),
            NSEProvider(),
            YFinanceProvider()
        ]
        
        status = {
            "configured": [],
            "available": [],
            "unavailable": []
        }
        
        for p in providers:
            status["configured"].append(p.name)
            if p.is_available():
                status["available"].append(p.name)
            else:
                status["unavailable"].append(p.name)
                
        return status

registry = ProviderRegistry()

def _safe_asdict(obj: Any) -> Any:
    if obj is None:
        return None
    d = asdict(obj)
    if hasattr(obj, 'metadata'):
        d['metadata'] = getattr(obj, 'metadata')
    return d

def _safe_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None

@router.get("/stocks/compare")
def compare_stocks(symbols: str = Query(..., description="Comma separated symbols")):
    if not symbols or not symbols.strip():
        raise HTTPException(status_code=400, detail="Missing required param: symbols")

    try:
        return build_stock_compare(symbols)
    except Exception as exc:
        logger.exception("Unexpected error during stock comparison for symbols: %s", symbols)
        raise HTTPException(status_code=500, detail="Unexpected error during comparison")

@router.get("/stocks/nifty50/ticker")
def get_nifty50_ticker():
    try:
        universe = load_stock_universe("NIFTY50")
        symbols = list(universe.keys())[:50]
        recent_prices = repository.get_recent_prices_for_symbols(symbols, limit_per_symbol=2)
        items = []

        for symbol in symbols:
            prices = recent_prices.get(symbol) or []
            latest = prices[-1] if prices else None
            previous = prices[-2] if len(prices) > 1 else None
            close = _safe_float(getattr(latest, "close", None))
            prev_close = _safe_float(getattr(previous, "close", None))
            change_pct = ((close - prev_close) / prev_close * 100) if close is not None and prev_close not in (None, 0) else None

            items.append({
                "symbol": symbol,
                "name": universe.get(symbol, {}).get("company_name") or symbol,
                "price": close,
                "change_pct": round(change_pct, 2) if change_pct is not None else None,
                "date": getattr(latest, "date", None).isoformat() if latest else None,
            })

        return {
            "index": "NIFTY50",
            "items": items,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    except Exception as exc:
        logger.exception("Unexpected error in get_nifty50_ticker")
        raise HTTPException(status_code=500, detail="Unexpected error")

@router.get("/stocks/{symbol}/profile")
def get_stock_profile(symbol: str):
    try:
        return build_stock_profile(symbol)
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error in get_stock_profile for symbol: %s", symbol)
        raise HTTPException(status_code=500, detail="Unexpected error")

@router.get("/stocks/{symbol}/financials")
def get_stock_financials(symbol: str, period_type: Optional[str] = None):
    try:
        data = get_stock_financials_service(symbol)
        if period_type:
            key = period_type.strip().lower()
            return data.get(key, [])
        return data
    except Exception as exc:
        logger.exception("Unexpected error in get_stock_financials for symbol: %s", symbol)
        raise HTTPException(status_code=500, detail="Unexpected error")

@router.get("/stocks/{symbol}/price-history")
def get_stock_price_history(symbol: str, start_date: Optional[str] = None, end_date: Optional[str] = None):
    try:
        # Current service API is day-count based and Supabase-first.
        history = get_stock_price_history_service(symbol, days=365)
        return history
    except Exception as exc:
        logger.exception("Unexpected error in get_stock_price_history for symbol: %s", symbol)
        raise HTTPException(status_code=500, detail="Unexpected error")

@router.get("/providers/status")
def get_provider_status():
    try:
        status = registry.get_status()
        if not status.get("configured"):
            raise HTTPException(status_code=503, detail={"error": "provider_unavailable"})
        return status
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error in get_provider_status")
        raise HTTPException(status_code=500, detail="Unexpected error")
