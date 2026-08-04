from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.models.stock_models import ProviderRun, StockPriceDaily
from app.providers.yfinance_provider import YFinanceProvider
from app.repositories.stock_repository import StockRepository

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

MAX_LAG_BUSINESS_DAYS = max(
    int(os.getenv("MF_METRIC_BENCHMARK_MAX_LAG_BUSINESS_DAYS", "3")),
    0,
)


def _business_day_lag(latest: date, current: date) -> int:
    if latest >= current:
        return 0
    lag = 0
    cursor = latest + timedelta(days=1)
    while cursor <= current:
        if cursor.weekday() < 5:
            lag += 1
        cursor += timedelta(days=1)
    return lag


def _stored_latest_date(repo: StockRepository) -> date | None:
    response = (
        repo.supabase.table("stock_prices_daily")
        .select("date")
        .eq("symbol", "NIFTY")
        .order("date", desc=True)
        .limit(1)
        .execute()
    )
    value = (response.data or [{}])[0].get("date")
    try:
        return date.fromisoformat(str(value)[:10])
    except (TypeError, ValueError):
        return None


def _to_price(row: dict[str, Any]) -> StockPriceDaily | None:
    try:
        close = float(row["close"])
        row_date = date.fromisoformat(str(row["date"])[:10])
    except (KeyError, TypeError, ValueError):
        return None
    if close <= 0:
        return None
    return StockPriceDaily(
        symbol="NIFTY",
        date=row_date,
        open=row.get("open"),
        high=row.get("high"),
        low=row.get("low"),
        close=close,
        adj_close=row.get("adj_close") or close,
        volume=int(row.get("volume") or 0),
        value_traded=None,
        delivery_qty=None,
        delivery_percent=None,
        source=str(row.get("source") or "yfinance"),
    )


def _write_output(path: str | None, payload: dict[str, Any]) -> None:
    if path:
        Path(path).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh the NIFTY proxy series used by MF metrics.")
    parser.add_argument("--period", default=os.getenv("MF_METRIC_BENCHMARK_PERIOD", "10y"))
    parser.add_argument("--output", default=os.getenv("MF_BENCHMARK_SYNC_OUTPUT", ""))
    args = parser.parse_args()

    repo = StockRepository()
    if not repo.supabase:
        logger.error("Supabase client is not configured.")
        return 1

    started_at = datetime.now(timezone.utc)
    run = ProviderRun(
        provider="yfinance",
        job_name="sync_nifty_benchmark",
        status="running",
        started_at=started_at,
        finished_at=None,
        symbols_attempted=1,
        symbols_succeeded=0,
        symbols_failed=0,
        error_summary=None,
        metadata={"period": args.period, "benchmark_mode": "proxy"},
    )
    run_id = repo.create_provider_run(run)
    existing_latest = _stored_latest_date(repo)
    raw_rows = YFinanceProvider().get_price_history("NIFTY", period=args.period)
    prices = [price for price in (_to_price(row) for row in raw_rows) if price is not None]
    if prices:
        repo.upsert_stock_prices_daily(prices)

    provider_latest = max((price.date for price in prices), default=None)
    latest = max([item for item in (existing_latest, provider_latest) if item], default=None)
    lag = _business_day_lag(latest, started_at.date()) if latest else None
    fresh = bool(latest and lag is not None and lag <= MAX_LAG_BUSINESS_DAYS)
    used_last_known_good = not prices and fresh
    status = "success" if fresh else "failed"
    reason = None if fresh else "benchmark_stale_or_missing"
    payload = {
        "status": status,
        "reason": reason,
        "benchmark": "NIFTY",
        "benchmark_mode": "proxy",
        "provider": "yfinance",
        "rows_received": len(raw_rows),
        "rows_upserted": len(prices),
        "existing_latest_date": existing_latest.isoformat() if existing_latest else None,
        "latest_date": latest.isoformat() if latest else None,
        "business_day_lag": lag,
        "maximum_business_day_lag": MAX_LAG_BUSINESS_DAYS,
        "last_known_good_used": used_last_known_good,
    }
    _write_output(args.output, payload)

    run.status = status
    run.finished_at = datetime.now(timezone.utc)
    run.symbols_succeeded = int(fresh)
    run.symbols_failed = int(not fresh)
    run.error_summary = reason
    run.metadata = payload
    if run_id:
        repo.update_provider_run(run_id, run)

    logger.info("NIFTY benchmark sync: %s", json.dumps(payload, default=str))
    return 0 if fresh else 1


if __name__ == "__main__":
    raise SystemExit(main())
