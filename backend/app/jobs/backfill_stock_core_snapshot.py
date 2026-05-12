import argparse
import logging
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.models.stock_models import ProviderRun
from app.repositories.stock_repository import StockRepository
from app.services.stock_snapshot_service import refresh_stock_core_snapshot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _parse_symbols(raw: str | None) -> list[str]:
    seen = set()
    symbols: list[str] = []
    for item in (raw or "").split(","):
        symbol = item.strip().upper()
        if symbol and symbol not in seen:
            seen.add(symbol)
            symbols.append(symbol)
    return symbols


def _load_symbols(repo: StockRepository, only_missing: bool, limit: int) -> list[str]:
    if not repo.supabase:
        return []
    try:
        priced = (
            repo.supabase.table("stock_prices_daily")
            .select("symbol")
            .order("date", desc=True)
            .limit(500000)
            .execute()
        )
        priced_symbols = _parse_symbols(",".join(row["symbol"] for row in (priced.data or []) if row.get("symbol")))
        if not only_missing:
            return priced_symbols[:limit] if limit > 0 else priced_symbols

        existing = repo.supabase.table("stock_core_snapshot").select("symbol").execute()
        existing_symbols = {str(row.get("symbol", "")).upper() for row in (existing.data or []) if row.get("symbol")}
        missing = [symbol for symbol in priced_symbols if symbol not in existing_symbols]
        return missing[:limit] if limit > 0 else missing
    except Exception as exc:
        logger.error("Failed to load symbols for stock_core_snapshot backfill: %s", exc)
        return []


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", type=str, help="Comma-separated symbols to refresh")
    parser.add_argument("--limit", type=int, default=0, help="Optional cap on symbol count")
    parser.add_argument(
        "--only-missing",
        type=str,
        default="true",
        help="When true, backfill only symbols not already present in stock_core_snapshot",
    )
    args = parser.parse_args()

    only_missing = str(args.only_missing).strip().lower() in {"1", "true", "yes", "on"}
    repo = StockRepository()

    symbols = _parse_symbols(args.symbols)
    if not symbols:
        symbols = _load_symbols(repo, only_missing=only_missing, limit=args.limit)
    elif args.limit > 0:
        symbols = symbols[: args.limit]

    run = ProviderRun(
        provider="snapshot_backfill",
        job_name="backfill_stock_core_snapshot",
        status="running",
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        symbols_attempted=len(symbols),
        symbols_succeeded=0,
        symbols_failed=0,
        error_summary=None,
        metadata={"only_missing": only_missing, "limit": args.limit},
    )
    run_id = repo.create_provider_run(run)

    for symbol in symbols:
        try:
            refresh_stock_core_snapshot(symbol, repo)
            run.symbols_succeeded += 1
        except Exception as exc:
            run.symbols_failed += 1
            logger.warning("Snapshot refresh failed for %s: %s", symbol, exc)

    run.status = "success" if run.symbols_failed == 0 else "partial"
    run.finished_at = datetime.now(timezone.utc)
    if run_id:
        repo.update_provider_run(run_id, run)

    print(
        f"Summary: Attempted: {run.symbols_attempted}, "
        f"Succeeded: {run.symbols_succeeded}, Failed: {run.symbols_failed}"
    )


if __name__ == "__main__":
    main()
