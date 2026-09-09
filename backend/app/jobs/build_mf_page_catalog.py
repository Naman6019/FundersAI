"""Evaluate one bounded snapshot batch, optionally publishing atomic catalog rows."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

BASE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BASE))
from app.jobs.backfill_catalog_nav_history import snapshot_batch, stored_history
from app.services.mf_catalog_service import catalog_row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--limit", type=int, required=True)
    parser.add_argument("--after", default="0")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    if not 1 <= args.limit <= 500 or not args.after.isdigit():
        parser.error("limit must be 1..500 and after numeric")
    from dotenv import load_dotenv
    load_dotenv(BASE / ".env")
    from app.repositories.stock_repository import StockRepository
    client = StockRepository().supabase
    if client is None:
        raise RuntimeError("Supabase is not configured")
    reservations = {r["scheme_code"]: r for r in json.loads((BASE / "config/mf_catalog_legacy_urls.json").read_text())}
    amc_slugs = {r["amc_name"].lower(): r["amc_slug"] for r in reservations.values()}
    amc_slugs.update({"reliance mutual fund": "nippon", "idfc mutual fund": "bandhan",
                      "boi axa mutual fund": "bank-of-india-mutual-fund",
                      "dhfl pramerica mutual fund": "pgim-india-mutual-fund"})
    rows = []
    for snapshot in snapshot_batch(client, args.after, args.limit):
        code = str(snapshot["scheme_code"])
        existing = client.table("mf_page_catalog").select("*").eq("scheme_code", code).execute().data or []
        row = catalog_row(snapshot, stored_history(client, code), existing[0] if existing else None,
                          reservations.get(code), today=datetime.now(timezone.utc).date(),
                          amc_slug=amc_slugs.get(str(snapshot.get("amc_name") or "").lower()))
        row["last_evaluated_at"] = datetime.now(timezone.utc).isoformat()
        if args.apply:
            # Metrics and eligibility commit together; failed reads never demote a page.
            client.table("mf_page_catalog").upsert(row, on_conflict="scheme_code").execute()
        rows.append(row)
    report = {"mode": "apply" if args.apply else "dry_run", "scanned": len(rows),
              "published": sum(r["is_published"] for r in rows),
              "next_after": rows[-1]["scheme_code"] if rows else None, "rows": rows}
    Path(args.output).write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "rows"}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
