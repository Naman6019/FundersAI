from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

load_dotenv(BASE_DIR / ".env")

from app.database import supabase
from app.services.mf_nav_freshness import assess_nav_freshness
from app.services.supported_amcs import SUPPORTED_MF_AMC_MARKERS, supported_amc_label_from_text
from scripts.sync_mf import fetch_amfi_nav


def _as_date(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
    except ValueError:
        try:
            return datetime.strptime(text, "%Y-%m-%d").date().isoformat()
        except ValueError:
            return None


def _nav_values_match(expected: object, observed: object) -> bool:
    try:
        # AMFI publishes NAV to four decimal places. A small tolerance avoids a
        # false mismatch when Postgres serializes a numeric value differently.
        return abs(Decimal(str(expected)) - Decimal(str(observed))) <= Decimal("0.0001")
    except (InvalidOperation, ValueError):
        return False


def _supported_amc_label(row: dict[str, Any]) -> str | None:
    return supported_amc_label_from_text(
        " ".join(str(row.get(field) or "") for field in ("amc_name", "scheme_name"))
    )


def load_core_rows(scheme_codes: Iterable[str]) -> dict[str, dict[str, Any]]:
    if supabase is None:
        raise RuntimeError("Supabase client is not configured.")

    rows_by_code: dict[str, dict[str, Any]] = {}
    codes = sorted({str(code).strip() for code in scheme_codes if str(code).strip()})
    for start in range(0, len(codes), 500):
        rows = (
            supabase.table("mutual_fund_core_snapshot")
            .select("scheme_code,nav,nav_date,last_updated")
            .in_("scheme_code", codes[start : start + 500])
            .execute()
            .data
            or []
        )
        for row in rows:
            code = str(row.get("scheme_code") or "").strip()
            if code:
                rows_by_code[code] = row
    return rows_by_code


def build_supported_nav_sync_report(
    amfi_rows: Iterable[dict[str, Any]],
    snapshot_rows: dict[str, dict[str, Any]],
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Compare every supported AMC NAV row in AMFI's feed with its runtime row."""
    per_amc: dict[str, dict[str, Any]] = {
        label: {
            "expected_scheme_count": 0,
            "synced_scheme_count": 0,
            "missing_snapshot_count": 0,
            "missing_nav_count": 0,
            "nav_mismatch_count": 0,
            "nav_date_mismatch_count": 0,
            "status": "missing_from_amfi",
        }
        for label in SUPPORTED_MF_AMC_MARKERS
    }
    expected_by_code: dict[str, tuple[str, dict[str, Any]]] = {}
    duplicate_scheme_codes: list[str] = []

    for row in amfi_rows:
        label = _supported_amc_label(row)
        code = str(row.get("scheme_code") or "").strip()
        if not label or not code:
            continue
        if code in expected_by_code:
            duplicate_scheme_codes.append(code)
            continue
        expected_by_code[code] = (label, row)
        per_amc[label]["expected_scheme_count"] += 1

    missing_snapshot_codes: list[str] = []
    missing_nav_codes: list[str] = []
    nav_mismatch_codes: list[str] = []
    nav_date_mismatch_codes: list[str] = []
    source_dates: list[str] = []
    snapshot_dates: list[str] = []

    for code, (label, expected) in expected_by_code.items():
        bucket = per_amc[label]
        expected_date = _as_date(expected.get("nav_date"))
        if expected_date:
            source_dates.append(expected_date)

        observed = snapshot_rows.get(code)
        if observed is None:
            bucket["missing_snapshot_count"] += 1
            missing_snapshot_codes.append(code)
            continue

        observed_date = _as_date(observed.get("nav_date"))
        if observed_date:
            snapshot_dates.append(observed_date)
        if observed.get("nav") is None:
            bucket["missing_nav_count"] += 1
            missing_nav_codes.append(code)
            continue
        if not _nav_values_match(expected.get("nav"), observed.get("nav")):
            bucket["nav_mismatch_count"] += 1
            nav_mismatch_codes.append(code)
        if expected_date != observed_date:
            bucket["nav_date_mismatch_count"] += 1
            nav_date_mismatch_codes.append(code)
        if _nav_values_match(expected.get("nav"), observed.get("nav")) and expected_date == observed_date:
            bucket["synced_scheme_count"] += 1

    failures: list[str] = []
    for label, bucket in per_amc.items():
        if not bucket["expected_scheme_count"]:
            failures.append(f"amfi_missing_supported_amc:{label}")
            bucket["status"] = "missing_from_amfi"
        elif any(
            bucket[field]
            for field in (
                "missing_snapshot_count",
                "missing_nav_count",
                "nav_mismatch_count",
                "nav_date_mismatch_count",
            )
        ):
            failures.append(f"snapshot_out_of_sync:{label}")
            bucket["status"] = "out_of_sync"
        else:
            bucket["status"] = "fresh"

    if duplicate_scheme_codes:
        failures.append("duplicate_supported_amfi_scheme_codes")
    if missing_snapshot_codes:
        failures.append("snapshot_missing_schemes")
    if missing_nav_codes:
        failures.append("snapshot_missing_nav_values")
    if nav_mismatch_codes:
        failures.append("snapshot_nav_values_mismatch")
    if nav_date_mismatch_codes:
        failures.append("snapshot_nav_dates_mismatch")

    source_latest_nav_date = max(source_dates, default=None)
    snapshot_latest_nav_date = max(snapshot_dates, default=None)
    current = now or datetime.now(timezone.utc)
    return {
        "checked_at": current.isoformat(),
        "source": "amfi_navall",
        "source_latest_nav_date": source_latest_nav_date,
        "latest_nav_date": snapshot_latest_nav_date,
        "freshness": assess_nav_freshness(source_latest_nav_date, now=current),
        "supported_amc_count": len(per_amc),
        "expected_scheme_count": len(expected_by_code),
        "synced_scheme_count": sum(int(bucket["synced_scheme_count"]) for bucket in per_amc.values()),
        "missing_snapshot_count": len(missing_snapshot_codes),
        "missing_nav_count": len(missing_nav_codes),
        "nav_mismatch_count": len(nav_mismatch_codes),
        "nav_date_mismatch_count": len(nav_date_mismatch_codes),
        "duplicate_scheme_code_count": len(duplicate_scheme_codes),
        "sample_missing_snapshot_codes": missing_snapshot_codes[:20],
        "sample_missing_nav_codes": missing_nav_codes[:20],
        "sample_nav_mismatch_codes": nav_mismatch_codes[:20],
        "sample_nav_date_mismatch_codes": nav_date_mismatch_codes[:20],
        "per_amc": per_amc,
        "failures": failures,
        "needs_retry": bool(failures),
        "status": "fresh" if not failures else "out_of_sync",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Reconcile every runtime-supported AMC NAV row against AMFI NAVAll.")
    parser.add_argument("--output", help="Write the verification JSON to this path.")
    parser.add_argument("--github-output", help="Write needs_retry and nav_freshness values for GitHub Actions.")
    parser.add_argument("--require-fresh", action="store_true", help="Exit non-zero unless NAV is current.")
    args = parser.parse_args()

    amfi_rows = fetch_amfi_nav()
    if not amfi_rows:
        raise RuntimeError("AMFI NAV feed returned no supported scheme updates for verification.")
    target_codes = [str(row.get("scheme_code") or "") for row in amfi_rows if _supported_amc_label(row)]
    payload = build_supported_nav_sync_report(
        amfi_rows,
        load_core_rows(target_codes),
        now=datetime.now(timezone.utc),
    )
    print(json.dumps(payload, sort_keys=True))

    if args.output:
        Path(args.output).write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    if args.github_output:
        with Path(args.github_output).open("a", encoding="utf-8") as output:
            output.write(f"needs_retry={'true' if payload['needs_retry'] else 'false'}\n")
            output.write(f"nav_freshness={payload['status']}\n")
    return 1 if args.require_fresh and payload["needs_retry"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
