"""Bounded catalog backfill/readiness audit; read-only unless --apply is supplied."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))

from app.services.mf_catalog_service import assess_history, identity_reasons


def snapshot_batch(client, after, limit):
    return (client.table("mutual_fund_core_snapshot")
            .select("scheme_code,scheme_name,amc_name,category,plan_type,option_type")
            .gt("scheme_code", after).order("scheme_code").limit(limit).execute().data or [])


def stored_history(client, code):
    # Do not use the serving helper: it converts database errors to empty histories.
    rows = client.table("nav_api_cache").select("payload").eq("scheme_code", str(code)).execute().data or []
    return rows[0].get("payload") or [] if rows else []


def run_batch(client, snapshots, *, apply=False, refresh=None, max_seconds=300, delay=1, today=None):
    started = time.monotonic()
    results = []
    for snapshot in snapshots:
        if time.monotonic() - started >= max_seconds:
            break  # Only stop between requests; the provider owns per-request timeouts.
        code = str(snapshot["scheme_code"])
        reasons = identity_reasons(snapshot)
        row = {"scheme_code": code, "identity_reasons": reasons}
        try:
            history = stored_history(client, code)
            before = assess_history(history, today=today)
            if apply and not reasons and before["gate_reasons"]:
                response = refresh(code, force_refresh=True)
                row["refresh_status"] = response.get("cache_status")
                # A returned provider payload is not evidence of a successful persisted backfill.
                history = stored_history(client, code)
                time.sleep(delay)
            row.update(assess_history(history, today=today))
        except Exception as exc:
            row["error"] = type(exc).__name__
        results.append(row)
    return {"scanned": len(results), "complete": len(results) == len(snapshots),
            "eligible": sum(not r["identity_reasons"] for r in results),
            "ready": sum(not r["identity_reasons"] and not r.get("gate_reasons", ["error"]) and "error" not in r for r in results),
            "next_after": results[-1]["scheme_code"] if results else None,
            "elapsed_seconds": round(time.monotonic() - started, 3), "rows": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, required=True, help="Snapshot rows scanned, at most 500")
    parser.add_argument("--after", default="0", help="Resume after scheme_code from previous report")
    parser.add_argument("--max-seconds", type=int, default=300)
    parser.add_argument("--delay", type=float, default=1)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--require-ready", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not 1 <= args.limit <= 500 or not 1 <= args.max_seconds <= 1800 or not 0.25 <= args.delay <= 60 or not args.after.isdigit():
        parser.error("limit 1..500, max-seconds 1..1800, delay 0.25..60 and numeric after required")
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")
    from app.repositories.stock_repository import StockRepository
    from app.services.mfapi_service import get_cached_nav_history
    client = StockRepository().supabase
    if client is None:
        raise RuntimeError("Supabase is not configured")
    report = run_batch(client, snapshot_batch(client, args.after, args.limit), apply=args.apply,
                       refresh=get_cached_nav_history, max_seconds=args.max_seconds, delay=args.delay,
                       today=datetime.now(timezone.utc).date())
    report.update(mode="apply" if args.apply else "readiness", as_of=datetime.now(timezone.utc).date().isoformat())
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}))
    failures = any("error" in r for r in report["rows"])
    return int(failures or not report["complete"] or (args.require_ready and (not report["eligible"] or report["ready"] != report["eligible"])))


if __name__ == "__main__":
    raise SystemExit(main())
