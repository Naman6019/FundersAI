from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.repositories.stock_repository import StockRepository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stale-after-hours", type=float, default=6.0)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    if args.stale_after_hours <= 0:
        parser.error("--stale-after-hours must be positive")

    now = datetime.now(timezone.utc)
    count = StockRepository().reconcile_stale_provider_runs(
        stale_after=timedelta(hours=args.stale_after_hours),
        now=now,
    )
    payload = {
        "status": "success",
        "checked_at": now.isoformat(),
        "stale_after_hours": args.stale_after_hours,
        "reconciled_count": count,
    }
    rendered = json.dumps(payload, indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
