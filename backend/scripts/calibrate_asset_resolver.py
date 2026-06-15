from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from dotenv import load_dotenv

load_dotenv(ROOT / "backend" / ".env")
load_dotenv(ROOT / ".env")

from app.database import supabase
from app.services.asset_resolver import AssetResolver


def _fetch_recent_user_queries(limit: int) -> list[str]:
    if not supabase:
        return []
    rows = (
        supabase.table("chat_messages")
        .select("content,created_at")
        .eq("role", "user")
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
        .data or []
    )
    return [str(row.get("content") or "").strip() for row in rows if str(row.get("content") or "").strip()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Dry-run recent chat queries through the asset resolver.")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--asset-type", choices=["auto", "stock", "mutual_fund"], default="auto")
    parser.add_argument("--json", action="store_true", help="Print full JSON rows instead of a compact report.")
    args = parser.parse_args()

    resolver = AssetResolver(supabase)
    rows = []
    for query in _fetch_recent_user_queries(args.limit):
        resolution = resolver.resolve(query, asset_type=args.asset_type)
        rows.append(resolution.client_payload())

    if args.json:
        print(json.dumps(rows, indent=2, sort_keys=True))
        return

    status_counts = Counter(str(row.get("coverage_status")) for row in rows)
    confidence_buckets = Counter(
        "high" if float(row.get("confidence") or 0) >= 0.88
        else "medium" if float(row.get("confidence") or 0) >= 0.68
        else "low"
        for row in rows
    )
    print("Asset resolver calibration dry run")
    print(f"Queries checked: {len(rows)}")
    print(f"Coverage status: {dict(status_counts)}")
    print(f"Confidence buckets: {dict(confidence_buckets)}")
    print("\nLowest-confidence non-empty resolutions:")
    resolved = [row for row in rows if row.get("resolved_name")]
    for row in sorted(resolved, key=lambda item: float(item.get("confidence") or 0))[:10]:
        print(
            f"- {row.get('confidence')}: {row.get('input')} -> {row.get('resolved_name')} "
            f"({row.get('coverage_status')}, {row.get('match_reason')})"
        )


if __name__ == "__main__":
    main()

