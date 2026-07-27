from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")

from app.database import supabase
from app.services.mf_nav_freshness import assess_nav_freshness


def load_latest_nav_date(*, max_rows: int = 5000) -> str | None:
    if supabase is None:
        raise RuntimeError("Supabase client is not configured.")

    latest: str | None = None
    page_size = 1000
    for offset in range(0, max_rows, page_size):
        rows = (
            supabase.table("mutual_fund_core_snapshot")
            .select("nav_date")
            .order("last_updated", desc=True)
            .range(offset, offset + page_size - 1)
            .execute()
            .data
            or []
        )
        for row in rows:
            nav_date = row.get("nav_date")
            if isinstance(nav_date, str) and (latest is None or nav_date > latest):
                latest = nav_date
        if len(rows) < page_size:
            break
    return latest


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify whether mutual-fund NAV is current for the latest expected business day.")
    parser.add_argument("--output", help="Write the verification JSON to this path.")
    parser.add_argument("--github-output", help="Write needs_retry and nav_freshness values for GitHub Actions.")
    parser.add_argument("--require-fresh", action="store_true", help="Exit non-zero unless NAV is current.")
    parser.add_argument("--max-rows", type=int, default=5000)
    args = parser.parse_args()

    latest_nav_date = load_latest_nav_date(max_rows=max(args.max_rows, 1))
    freshness = assess_nav_freshness(latest_nav_date, now=datetime.now(timezone.utc))
    payload = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "latest_nav_date": latest_nav_date,
        "freshness": freshness,
        "needs_retry": freshness["status"] != "fresh",
    }
    print(json.dumps(payload, sort_keys=True))

    if args.output:
        Path(args.output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.github_output:
        with Path(args.github_output).open("a", encoding="utf-8") as output:
            output.write(f"needs_retry={'true' if payload['needs_retry'] else 'false'}\n")
            output.write(f"nav_freshness={freshness['status']}\n")
    return 1 if args.require_fresh and payload["needs_retry"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
