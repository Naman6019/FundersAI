from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase
from app.mf_ingestion.services.parsing_service import ParsingService, _normalize_family_scheme_name
from app.mf_ingestion.services.promotion_review_service import upsert_decision

FMP_PATTERN = re.compile(
    r"(?i)\b(?:fmp|fixed\s+maturity\s+plan|fixed\s+term\s+income(?:\s+fund)?)\b"
)
GENERIC_FMP_FAMILIES = {
    "kotak": ("kotak-fmp-series", "102591"),
    "uti": ("uti-fixed-term-income-fund-series", "100668"),
    "hdfc": ("hdfc-fmp-series", "100123"),
    "icici": ("icici-pru-fmp-series", "100345"),
    "sbi": ("sbi-fmp-series", "100456"),
}

KNOWN_AMC_SCHEME_ALIASES: dict[str, dict[str, tuple[str, str]]] = {
    "uti": {
        "uti nifty midcap 150 etf": ("145293", "uti-nifty-midcap-150-etf"),
        "uti nifty next 50 etf": ("145295", "uti-nifty-next-50-etf"),
        "uti bse sensex next 50 etf": ("145296", "uti-bse-sensex-next-50-etf"),
        "uti nifty bank exchange traded fund etf": ("120750", "uti-nifty-bank-etf"),
        "uti mastershare unit scheme": ("100668", "uti-large-cap-fund"),
    },
    "kotak": {
        "kotak nifty alpha low volatility 30 index fund": ("150822", "kotak-nifty-alpha-low-volatility-30-index-fund"),
        "kotak nifty alpha low-volatility 30 index fund": ("150822", "kotak-nifty-alpha-low-volatility-30-index-fund"),
        "kotak multi asset active fof": ("153372", "kotak-multi-asset-active-fof"),
        "kotak silver etf fof": ("150948", "kotak-silver-etf-fof"),
        "kotak income plus arbitrage omni fof": ("153375", "kotak-income-plus-arbitrage-omni-fof"),
        "kotak crisil-ibx financial services 3-6 months debt index fund": ("153376", "kotak-crisil-ibx-financial-services-3-6-months-debt-index-fund"),
    },
}


def auto_resolve_candidates(
    *,
    amc_code: str | None = None,
    report_month: str = "2026-06-01",
    apply: bool = False,
    reviewed_by: str = "automated_review_agent",
) -> dict[str, Any]:
    if not supabase:
        return {"status": "error", "issues": ["supabase_not_configured"]}

    service = ParsingService()
    query = (
        supabase.table("mf_factsheet_candidates")
        .select("id,amc_code,report_month,raw_scheme_name,mapped_scheme_code,mapped_family_id,mapping_confidence,mapping_status,promotion_status,source_document_id")
        .eq("report_month", report_month)
        .in_("mapping_status", ["needs_review", "unmapped"])
    )
    if amc_code:
        query = query.eq("amc_code", amc_code.upper())

    candidates = query.execute().data or []

    resolved_count = 0
    fmp_generic_count = 0
    alias_count = 0
    confidence_recovered_count = 0
    remaining_review = 0
    decisions_upserted = 0
    actions: list[dict[str, Any]] = []

    for candidate in candidates:
        cand_id = str(candidate["id"])
        code = str(candidate.get("amc_code") or "").strip().lower()
        raw_name = str(candidate.get("raw_scheme_name") or "").strip()
        doc_id = candidate.get("source_document_id")

        if candidate.get("promotion_status") in {"promoted", "partially_promoted"}:
            remaining_review += 1
            continue

        target_code: str | None = None
        target_family: str | None = None
        target_confidence: float = 0.0
        resolution_method: str | None = None

        norm_raw = " ".join(raw_name.lower().split())

        if code in KNOWN_AMC_SCHEME_ALIASES and norm_raw in KNOWN_AMC_SCHEME_ALIASES[code]:
            target_code, target_family = KNOWN_AMC_SCHEME_ALIASES[code][norm_raw]
            target_confidence = 100.0
            resolution_method = "known_alias"
            alias_count += 1

        elif FMP_PATTERN.search(raw_name) and code in GENERIC_FMP_FAMILIES:
            generic_slug, fallback_code = GENERIC_FMP_FAMILIES[code]
            target_family = generic_slug
            target_code = fallback_code
            target_confidence = 90.0
            resolution_method = "generic_fmp_family"
            fmp_generic_count += 1

        else:
            resolved_code, resolved_family, conf, status = service._resolve_staged_mapping(code, raw_name)
            if resolved_code and resolved_family and conf >= 85.0:
                target_code = resolved_code
                target_family = resolved_family
                target_confidence = conf
                resolution_method = "confidence_recovery"
                confidence_recovered_count += 1

        if target_code and target_family:
            resolved_count += 1
            action = {
                "candidate_id": cand_id,
                "amc_code": candidate.get("amc_code"),
                "raw_scheme_name": raw_name,
                "mapped_scheme_code": target_code,
                "mapped_family_id": target_family,
                "confidence": target_confidence,
                "resolution_method": resolution_method,
            }
            actions.append(action)

            if apply:
                try:
                    upsert_decision(
                        amc=str(candidate.get("amc_code")),
                        report_month=report_month,
                        scope="risk",
                        subject_key=raw_name,
                        subject_label=raw_name,
                        resolution="use_staged",
                        decided_value={
                            "mapped_scheme_code": target_code,
                            "mapped_family_id": target_family,
                            "mapping_confidence": target_confidence,
                        },
                        source_document_id=doc_id,
                        reviewed_by=reviewed_by,
                        note=f"Automated resolution via {resolution_method}",
                    )
                    decisions_upserted += 1
                except Exception:
                    pass

                supabase.table("mf_factsheet_candidates").update(
                    {
                        "mapped_scheme_code": target_code,
                        "mapped_family_id": target_family,
                        "mapping_confidence": target_confidence,
                        "mapping_status": "mapped",
                    }
                ).eq("id", cand_id).execute()

                if doc_id:
                    supabase.table("mf_scheme_holdings").update(
                        {
                            "mapped_scheme_code": target_code,
                            "mapped_family_id": target_family,
                            "mapping_confidence": target_confidence,
                            "mapping_status": "mapped",
                        }
                    ).eq("source_document_id", doc_id).eq("raw_scheme_name", raw_name).execute()

        else:
            remaining_review += 1

    return {
        "status": "applied" if apply else "dry_run",
        "report_month": report_month,
        "amc_filter": amc_code or "ALL",
        "candidates_evaluated": len(candidates),
        "resolved_total": resolved_count,
        "resolved_via_alias": alias_count,
        "resolved_via_fmp_generic": fmp_generic_count,
        "resolved_via_confidence_recovery": confidence_recovered_count,
        "remaining_needs_review": remaining_review,
        "decisions_upserted": decisions_upserted,
        "sample_actions": actions[:20],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Automate review isolation candidate resolution across 12 AMCs.")
    parser.add_argument("--amc")
    parser.add_argument("--report-month", default="2026-06-01")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    result = auto_resolve_candidates(
        amc_code=args.amc,
        report_month=args.report_month,
        apply=args.apply,
    )
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
