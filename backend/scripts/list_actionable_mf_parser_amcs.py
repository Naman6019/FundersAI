from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.mf_ingestion.sources.registry import capability_keys, get_source

ACTIONABLE_STATUSES = "needs_review,failed,parsed_partial"


def _requested(raw: str) -> set[str]:
    return {value.strip().lower() for value in str(raw or "").split(",") if value.strip()}


def actionable_matrix(rows: list[dict], requested: str = "") -> list[str]:
    enabled = list(capability_keys("portfolio_parser_enabled"))
    code_to_key = {get_source(key).amc_code.lower(): key for key in enabled}
    actionable = {
        code_to_key[str(row.get("amc_code") or "").strip().lower()]
        for row in rows
        if str(row.get("amc_code") or "").strip().lower() in code_to_key
    }
    requested_keys = _requested(requested)
    if requested_keys:
        actionable &= requested_keys
    return [key for key in enabled if key in actionable] or ["__none__"]


def _fetch_rows() -> list[dict]:
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_KEY", "")
    if not base or not key:
        raise RuntimeError("missing_supabase_configuration")
    query = urlencode(
        {
            "select": "amc_code",
            "parse_status": f"in.({ACTIONABLE_STATUSES})",
            "limit": "5000",
        }
    )
    request = Request(
        f"{base}/rest/v1/mf_raw_documents?{query}",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    with urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return payload if isinstance(payload, list) else []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amcs", default="")
    args = parser.parse_args()
    print(json.dumps(actionable_matrix(_fetch_rows(), args.amcs)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
