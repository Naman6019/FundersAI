"""Restore runtime MF data from an applied promotion run's captured before-state.

Promotion is the only path from staging into runtime tables, and until now it was
one-way: `promote_mf_holdings_document_v2` deleted live holdings/sector rows without
recording them. `20260824_add_mf_promotion_revert.sql` makes both promotion kinds
capture their before-state, and this job drives the matching
`revert_mf_promotion_run` RPC.

Dry run is the default and reads only. `--apply` performs the restore inside the
RPC's single transaction.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any
from uuid import UUID

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase
from app.mf_ingestion.sources.registry import PRODUCTION_TARGET_AMC_KEYS

RUN_COLUMNS = (
    "id,source_document_id,candidate_id,amc_code,scopes,status,requested_by,"
    "before_snapshot,after_snapshot,validation_report,reverted_at,reverted_by,"
    "revert_of_run_id,created_at,completed_at"
)
CORE_SCOPES = {"risk", "ter_aum", "benchmark", "manager"}
PORTFOLIO_SCOPES = {"holdings", "sectors"}
DEFAULT_LIST_LIMIT = 20


def _parse_run_id(value: str) -> str:
    try:
        return str(UUID(str(value).strip()))
    except (ValueError, AttributeError, TypeError) as exc:
        raise ValueError("run_id_invalid") from exc


def fetch_promotion_run(run_id: str) -> dict[str, Any] | None:
    response = (
        supabase.table("mf_promotion_runs")
        .select(RUN_COLUMNS)
        .eq("id", run_id)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    return rows[0] if rows else None


def list_revertable_runs(amc: str | None, limit: int = DEFAULT_LIST_LIMIT) -> list[dict[str, Any]]:
    query = (
        supabase.table("mf_promotion_runs")
        .select(RUN_COLUMNS)
        .eq("status", "applied")
        .is_("reverted_at", "null")
    )
    if amc:
        query = query.eq("amc_code", amc)
    return query.order("created_at", desc=True).limit(limit).execute().data or []


def _snapshot_rows(snapshot: Any, key: str) -> list[dict[str, Any]]:
    if not isinstance(snapshot, dict):
        return []
    rows = snapshot.get(key)
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _snapshot_codes(snapshot: Any, key: str) -> list[str]:
    if not isinstance(snapshot, dict):
        return []
    codes = snapshot.get(key)
    return [str(code) for code in codes] if isinstance(codes, list) else []


def build_revert_plan(run: dict[str, Any]) -> dict[str, Any]:
    """Describe what reverting this run would restore, and why it might be refused.

    Mirrors the RPC's own guards so a dry run surfaces the same refusals without
    opening a write transaction.
    """
    issues: list[str] = []
    scopes = [str(scope) for scope in (run.get("scopes") or [])]
    snapshot = run.get("before_snapshot")
    is_core = bool(run.get("candidate_id"))
    kind = "core" if is_core else "portfolio"

    if str(run.get("status") or "") != "applied":
        issues.append("promotion_run_not_applied")
    if run.get("reverted_at"):
        issues.append("promotion_run_already_reverted")
    if not isinstance(snapshot, dict) or not snapshot:
        issues.append("promotion_run_before_snapshot_unavailable")

    plan: dict[str, Any] = {
        "run_id": str(run.get("id") or ""),
        "revert_kind": kind,
        "amc_code": run.get("amc_code"),
        "scopes": scopes,
        "promoted_at": run.get("completed_at"),
        "promoted_by": run.get("requested_by"),
    }

    if is_core:
        scheme_code = (snapshot or {}).get("scheme_code") if isinstance(snapshot, dict) else None
        if isinstance(snapshot, dict) and snapshot and not scheme_code:
            issues.append("promotion_run_before_snapshot_unavailable")
        plan["restores"] = {
            "scheme_code": scheme_code,
            "fields": sorted(set(scopes) & CORE_SCOPES),
        }
    else:
        if isinstance(snapshot, dict) and snapshot and not snapshot.get("revertable"):
            # Recorded by a promotion that ran before the before-state capture existed.
            issues.append("promotion_run_before_snapshot_unavailable")
        plan["restores"] = {
            "report_month": (snapshot or {}).get("report_month") if isinstance(snapshot, dict) else None,
            "holdings_rows": len(_snapshot_rows(snapshot, "holdings")),
            "holdings_scheme_codes": len(_snapshot_codes(snapshot, "holdings_scheme_codes")),
            "sectors_rows": len(_snapshot_rows(snapshot, "sectors")),
            "sectors_scheme_codes": len(_snapshot_codes(snapshot, "sectors_scheme_codes")),
        }

    plan["issues"] = sorted(set(issues))
    plan["status"] = "revertable" if not issues else "blocked"
    return plan


def apply_revert(run_id: str, *, requested_by: str) -> dict[str, Any]:
    response = supabase.rpc(
        "revert_mf_promotion_run",
        {"p_run_id": run_id, "p_requested_by": requested_by},
    ).execute()
    data = response.data
    if isinstance(data, list):
        data = data[0] if data else {}
    return data if isinstance(data, dict) else {"status": "unknown", "raw": data}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dry-run or apply a revert of one applied MF promotion run.",
    )
    parser.add_argument("--run-id", help="mf_promotion_runs.id to revert")
    parser.add_argument(
        "--list",
        action="store_true",
        help="List revertable runs instead of reverting one",
    )
    parser.add_argument("--amc", choices=sorted(PRODUCTION_TARGET_AMC_KEYS), help="Filter --list by AMC")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIST_LIMIT)
    parser.add_argument("--requested-by", required=True)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if not supabase:
        print(json.dumps({"status": "error", "issues": ["supabase_not_configured"]}))
        return 2

    if args.list:
        runs = list_revertable_runs(args.amc, max(1, min(args.limit, 100)))
        print(
            json.dumps(
                {
                    "status": "listed",
                    "amc": args.amc,
                    "count": len(runs),
                    "runs": [build_revert_plan(run) for run in runs],
                },
                indent=2,
                default=str,
            )
        )
        return 0

    if not args.run_id:
        print(json.dumps({"status": "error", "issues": ["run_id_required"]}))
        return 2
    try:
        run_id = _parse_run_id(args.run_id)
    except ValueError as exc:
        print(json.dumps({"status": "error", "issues": [str(exc)]}))
        return 2

    run = fetch_promotion_run(run_id)
    if run is None:
        print(json.dumps({"status": "error", "issues": ["promotion_run_not_found"]}))
        return 1

    plan = build_revert_plan(run)
    if plan["status"] != "revertable":
        print(json.dumps(plan, indent=2, default=str))
        return 1
    if not args.apply:
        plan["status"] = "dry_run"
        print(json.dumps(plan, indent=2, default=str))
        return 0

    # Re-read immediately before mutating so a concurrent revert cannot double-apply.
    revalidated = fetch_promotion_run(run_id)
    if revalidated is None:
        print(json.dumps({"status": "error", "issues": ["promotion_run_not_found"]}))
        return 1
    revalidated_plan = build_revert_plan(revalidated)
    if revalidated_plan["status"] != "revertable":
        print(json.dumps(revalidated_plan, indent=2, default=str))
        return 1

    result = apply_revert(run_id, requested_by=args.requested_by)
    print(json.dumps({"plan": revalidated_plan, "result": result}, indent=2, default=str))
    return 0 if str(result.get("status") or "") == "reverted" else 1


if __name__ == "__main__":
    raise SystemExit(main())
