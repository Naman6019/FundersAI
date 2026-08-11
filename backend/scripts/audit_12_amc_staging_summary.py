from __future__ import annotations

import json
import os
import sys
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase

AMCS = [
    "PPFAS",
    "MIRAE",
    "HDFC",
    "ICICI",
    "SBI",
    "AXIS",
    "MOTILAL",
    "NIPPON",
    "KOTAK",
    "ABSL",
    "UTI",
    "DSP",
    "TATA",
    "BANDHAN",
    "EDELWEISS",
    "INVESCO",
    "HSBC",
]


def audit_summary(report_month: str = "2026-06-01") -> dict[str, Any]:
    if not supabase:
        return {"status": "error", "issues": ["supabase_not_configured"]}

    amc_metrics: dict[str, dict[str, int]] = {}
    total_candidates = 0
    total_mapped = 0
    total_needs_review = 0
    total_unmapped = 0
    total_promoted = 0

    for amc in AMCS:
        res = (
            supabase.table("mf_factsheet_candidates")
            .select("id,mapping_status,promotion_status")
            .eq("report_month", report_month)
            .eq("amc_code", amc)
            .execute()
        )
        cands = res.data or []
        count = len(cands)
        mapped = sum(1 for c in cands if c.get("mapping_status") == "mapped")
        review = sum(1 for c in cands if c.get("mapping_status") == "needs_review")
        unmapped = sum(1 for c in cands if c.get("mapping_status") == "unmapped")
        promoted = sum(1 for c in cands if c.get("promotion_status") in {"promoted", "partially_promoted"})

        amc_metrics[amc] = {
            "total_candidates": count,
            "mapped": mapped,
            "needs_review": review,
            "unmapped": unmapped,
            "promoted": promoted,
        }

        total_candidates += count
        total_mapped += mapped
        total_needs_review += review
        total_unmapped += unmapped
        total_promoted += promoted

    return {
        "status": "success",
        "report_month": report_month,
        "total_candidates": total_candidates,
        "total_mapped": total_mapped,
        "resolution_rate_pct": round((total_mapped / total_candidates * 100) if total_candidates else 0, 1),
        "total_needs_review": total_needs_review,
        "total_unmapped": total_unmapped,
        "total_promoted": total_promoted,
        "amc_metrics": amc_metrics,
    }


def main() -> int:
    result = audit_summary()
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
