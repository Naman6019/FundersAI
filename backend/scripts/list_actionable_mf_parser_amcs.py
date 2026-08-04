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

from app.mf_ingestion.automation_scope import resolve_automation_scope
from app.mf_ingestion.sources.registry import get_source
from app.supabase_retry import execute_with_retry

ACTIONABLE_STATUSES = "needs_review,failed,parsed_partial"


def _requested(raw: str) -> set[str]:
    return {value.strip().lower() for value in str(raw or "").split(",") if value.strip()}


def actionable_matrix(
    rows: list[dict],
    requested: str = "",
    *,
    lane: str = "green",
    event_name: str = "workflow_dispatch",
    source_document_ids: str = "",
) -> list[str]:
    enabled = list(resolve_automation_scope(
        operation="parser_retry",
        lane=lane,
        raw_amcs=requested,
        event_name=event_name,
        source_document_ids=source_document_ids,
    ))
    selected_ids = _requested(source_document_ids)
    code_to_key = {get_source(key).amc_code.lower(): key for key in enabled}
    actionable = {
        code_to_key[str(row.get("amc_code") or "").strip().lower()]
        for row in rows
        if str(row.get("amc_code") or "").strip().lower() in code_to_key
        and (not selected_ids or str(row.get("id") or "").strip().lower() in selected_ids)
    }
    return [key for key in enabled if key in actionable] or ["__none__"]


def _fetch_rows() -> list[dict]:
    base = os.getenv("SUPABASE_URL", "").rstrip("/")
    key = os.getenv("SUPABASE_KEY", "")
    if not base or not key:
        raise RuntimeError("missing_supabase_configuration")
    query = urlencode(
        {
            "select": "id,amc_code",
            "parse_status": f"in.({ACTIONABLE_STATUSES})",
            "limit": "5000",
        }
    )
    request = Request(
        f"{base}/rest/v1/mf_raw_documents?{query}",
        headers={"apikey": key, "Authorization": f"Bearer {key}"},
    )
    def fetch() -> list[dict]:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return payload if isinstance(payload, list) else []

    return execute_with_retry(fetch, operation_name="load_actionable_parser_amcs")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amcs", default="")
    parser.add_argument("--lane", default="green", choices=("green", "approved_restricted", "validation_only"))
    parser.add_argument("--event-name", default="workflow_dispatch")
    parser.add_argument("--source-document-ids", default="")
    args = parser.parse_args()
    print(json.dumps(actionable_matrix(
        _fetch_rows(),
        args.amcs,
        lane=args.lane,
        event_name=args.event_name,
        source_document_ids=args.source_document_ids,
    )))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
