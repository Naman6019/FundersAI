from __future__ import annotations

import argparse
import logging
import os
import sys
from typing import Any

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.repositories.mutual_fund_repository import MutualFundRepository
from app.services.supported_amcs import supported_amc_label_from_text

logger = logging.getLogger(__name__)

QUALITATIVE_KEYS = ("main_style", "minimum_sip", "mandate", "best_for", "main_risk")


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def _category_text(row: dict[str, Any]) -> str:
    return _clean_text(row.get("category") or row.get("scheme_name")).lower()


def _main_style(row: dict[str, Any]) -> str:
    category = _category_text(row)
    if "small" in category:
        return "Small-cap equity with higher growth and higher volatility."
    if "mid" in category:
        return "Mid-cap equity focused on growth beyond large-cap leaders."
    if "large" in category or "blue" in category:
        return "Large-cap equity focused on established companies."
    if "flexi" in category or "multi cap" in category:
        return "Flexible equity allocation across market-cap segments."
    if "index" in category:
        return "Passive equity exposure that tracks a benchmark index."
    if "debt" in category or "bond" in category or "liquid" in category:
        return "Debt-oriented allocation focused on interest income and stability."
    if "hybrid" in category or "balanced" in category:
        return "Hybrid allocation across equity and debt."
    return "Diversified mutual fund allocation based on the scheme mandate."


def _mandate(row: dict[str, Any]) -> str:
    category = _category_text(row)
    if "small" in category:
        return "Primarily invests in small-cap companies as permitted by the scheme mandate."
    if "mid" in category:
        return "Primarily invests in mid-cap companies as permitted by the scheme mandate."
    if "large" in category or "blue" in category:
        return "Primarily invests in large-cap companies as permitted by the scheme mandate."
    if "flexi" in category or "multi cap" in category:
        return "Can allocate across large, mid, and small-cap companies."
    if "index" in category:
        return "Seeks to track the selected benchmark index."
    if "debt" in category or "bond" in category or "liquid" in category:
        return "Invests mainly in debt and money-market instruments."
    if "hybrid" in category or "balanced" in category:
        return "Allocates between equity and debt within scheme limits."
    return "Follows the investment mandate stated in the AMC scheme documents."


def _best_for(row: dict[str, Any]) -> str:
    category = _category_text(row)
    if "small" in category or "mid" in category:
        return "Investors studying higher-risk long-term equity exposure."
    if "large" in category or "blue" in category:
        return "Investors studying core equity exposure with relatively broader stability."
    if "flexi" in category or "multi cap" in category:
        return "Investors studying flexible diversified equity allocation."
    if "index" in category:
        return "Investors studying low-intervention benchmark exposure."
    if "debt" in category or "bond" in category or "liquid" in category:
        return "Investors studying lower-volatility debt allocation."
    return "Investors comparing the scheme with similar category peers."


def _main_risk(row: dict[str, Any]) -> str:
    category = _category_text(row)
    risk = _clean_text(row.get("risk_level"))
    if risk:
        return f"Official risk label: {risk}."
    if "small" in category:
        return "Higher volatility and drawdowns during small-cap corrections."
    if "mid" in category:
        return "Higher volatility during mid-cap corrections."
    if "debt" in category or "bond" in category:
        return "Interest-rate and credit-quality changes can affect returns."
    if "index" in category:
        return "Returns can lag active peers and will follow benchmark drawdowns."
    return "Market risk and category-specific underperformance."


def build_qualitative_insights(row: dict[str, Any]) -> dict[str, str]:
    return {
        "main_style": _main_style(row),
        "minimum_sip": "Check the AMC or platform for the current minimum SIP.",
        "mandate": _mandate(row),
        "best_for": _best_for(row),
        "main_risk": _main_risk(row),
    }


def _needs_qualitative(payload: Any) -> bool:
    if not isinstance(payload, dict):
        return True
    insights = payload.get("qualitative_insights")
    if not isinstance(insights, dict):
        return True
    return any(not _clean_text(insights.get(key)) for key in QUALITATIVE_KEYS)


def _is_supported_row(row: dict[str, Any]) -> bool:
    return supported_amc_label_from_text(f"{row.get('amc_name') or ''} {row.get('scheme_name') or ''}") is not None


def sync_qualitative_factors(*, limit: int = 100, dry_run: bool = False) -> int:
    repo = MutualFundRepository()
    rows = (
        repo.table("mutual_fund_core_snapshot")
        .select("scheme_code,scheme_name,amc_name,category,risk_level,provider_payload")
        .limit(limit)
        .execute()
        .data
        or []
    )

    updated = 0
    for row in rows:
        if not _is_supported_row(row) or not _needs_qualitative(row.get("provider_payload")):
            continue

        payload = row.get("provider_payload") if isinstance(row.get("provider_payload"), dict) else {}
        payload = dict(payload)
        payload["qualitative_insights"] = build_qualitative_insights(row)

        scheme_code = row.get("scheme_code")
        if dry_run:
            logger.info("Would update qualitative_insights for scheme_code=%s", scheme_code)
        else:
            repo.table("mutual_fund_core_snapshot").update({"provider_payload": payload}).eq("scheme_code", scheme_code).execute()
            logger.info("Updated qualitative_insights for scheme_code=%s", scheme_code)
        updated += 1
    return updated


def main() -> int:
    parser = argparse.ArgumentParser(description="Backfill deterministic mutual-fund qualitative comparison fields.")
    parser.add_argument("--limit", type=int, default=int(os.getenv("MF_QUALITATIVE_SYNC_LIMIT", "100")))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    updated = sync_qualitative_factors(limit=args.limit, dry_run=args.dry_run)
    print(f"qualitative_rows_matched={updated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
