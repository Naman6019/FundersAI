from __future__ import annotations

import os
import sys
from collections import defaultdict
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.database import supabase
from app.services.supported_amcs import SUPPORTED_MF_AMC_MARKERS


AMC_LABELS = {label.lower(): markers for label, markers in SUPPORTED_MF_AMC_MARKERS.items()}


def _get_all(table: str, columns: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    offset = 0
    limit = 1000
    while True:
        page = supabase.table(table).select(columns).range(offset, offset + limit - 1).execute().data or []
        if not page:
            return rows
        rows.extend(page)
        offset += limit


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except ValueError:
        return default


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


def _configured_amcs() -> list[str]:
    raw = os.getenv("MF_DISCLOSURE_STRICT_COVERAGE_AMCS") or os.getenv(
        "MF_DISCLOSURE_COVERAGE_AMCS",
        "axis,hdfc,sbi,icici,ppfas,nippon",
    )
    return [token.strip().lower() for token in raw.split(",") if token.strip()]


def _matches_amc(row: dict[str, Any], amc: str) -> bool:
    labels = AMC_LABELS.get(amc, (amc,))
    text = " ".join(str(row.get(field) or "").lower() for field in ("amc_name", "scheme_name"))
    return any(label in text for label in labels)


def _has_value(value: Any) -> bool:
    return value not in (None, "")


def _ratio(count: int, total: int) -> float:
    return count / total if total else 0.0


def check_disclosure_coverage() -> int:
    if not supabase:
        print("MF disclosure coverage failed: Supabase is not configured.")
        return 1

    min_count = _env_int("MF_DISCLOSURE_MIN_FIELD_COUNT", 1)
    min_core_ratio = _env_float("MF_DISCLOSURE_MIN_CORE_FIELD_RATIO", 0.01)
    min_portfolio_ratio = _env_float("MF_DISCLOSURE_MIN_PORTFOLIO_FAMILY_RATIO", 0.01)

    mappings = _get_all("mutual_fund_family_mapping", "scheme_code,family_id")
    scheme_to_family = {str(row.get("scheme_code")): row.get("family_id") for row in mappings if row.get("scheme_code")}

    holdings = _get_all("mutual_fund_holdings", "family_id")
    sectors = _get_all("mutual_fund_sectors", "family_id")
    holding_families = {row.get("family_id") for row in holdings if row.get("family_id")}
    sector_families = {row.get("family_id") for row in sectors if row.get("family_id")}

    snapshot_rows = _get_all(
        "mutual_fund_core_snapshot",
        "scheme_code,scheme_name,amc_name,aum,expense_ratio,benchmark",
    )

    failures: list[str] = []
    print("MF disclosure strict coverage:")
    for amc in _configured_amcs():
        rows = [row for row in snapshot_rows if _matches_amc(row, amc)]
        families: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            scheme_code = str(row.get("scheme_code") or "")
            family_id = scheme_to_family.get(scheme_code) or f"scheme-{scheme_code}"
            families[str(family_id)].append(row)

        total_families = len(families)
        if total_families == 0:
            failures.append(f"{amc}: no snapshot families found")
            print(f"{amc}: total_families=0")
            continue

        counts = {
            "aum": sum(1 for family_rows in families.values() if any(_has_value(row.get("aum")) for row in family_rows)),
            "expense_ratio": sum(1 for family_rows in families.values() if any(_has_value(row.get("expense_ratio")) for row in family_rows)),
            "benchmark": sum(1 for family_rows in families.values() if any(_has_value(row.get("benchmark")) for row in family_rows)),
            "holdings": sum(1 for family_id in families if family_id in holding_families),
            "sectors": sum(1 for family_id in families if family_id in sector_families),
        }
        print(
            f"{amc}: total_families={total_families} "
            f"aum={counts['aum']} expense_ratio={counts['expense_ratio']} "
            f"benchmark={counts['benchmark']} holdings={counts['holdings']} sectors={counts['sectors']}"
        )

        for field in ("aum", "expense_ratio", "benchmark"):
            field_ratio = _ratio(counts[field], total_families)
            if counts[field] < min_count or field_ratio < min_core_ratio:
                failures.append(f"{amc}: {field} coverage {counts[field]}/{total_families} below threshold")

        for field in ("holdings", "sectors"):
            field_ratio = _ratio(counts[field], total_families)
            if counts[field] < min_count or field_ratio < min_portfolio_ratio:
                failures.append(f"{amc}: {field} coverage {counts[field]}/{total_families} below threshold")

    if failures:
        print("MF disclosure coverage failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print("MF disclosure coverage passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(check_disclosure_coverage())
