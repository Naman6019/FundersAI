from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / "backend" / ".env")
load_dotenv(ROOT / ".env")
sys.path.insert(0, str(ROOT / "backend"))

from app.database import supabase
from app.repositories.mutual_fund_repository import MutualFundRepository
from app.services.asset_resolver import AssetResolution
from app.services.compare_data_service import CompareDataService
from app.services.mf_holdings_quality import is_holding_summary_or_noise


def _resolution(row: dict, scheme_code: str) -> AssetResolution:
    name = str(row.get("scheme_name") or scheme_code)
    return AssetResolution(
        input=name,
        resolved_name=name,
        asset_type="mutual_fund",
        id=scheme_code,
        confidence=1.0,
        coverage_status="supported",
        amc=row.get("amc_name"),
        match_reason="exact_scheme_code_diagnostic",
    )


async def _diagnose(scheme_codes: list[str]) -> dict:
    if not supabase:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be configured.")

    repository = MutualFundRepository(supabase)
    rows: list[dict] = []
    resolutions: list[AssetResolution] = []
    missing_codes: list[str] = []
    raw_holding_noise: dict[str, list[str]] = {}

    for code in scheme_codes:
        row = repository.get_fund_by_scheme_code(code)
        if not row:
            missing_codes.append(code)
            continue
        rows.append(row)
        resolutions.append(_resolution(row, code))
        raw_holdings = repository.get_latest_holdings(code)
        raw_holding_noise[code] = [
            str(item.get("security_name"))
            for item in raw_holdings
            if is_holding_summary_or_noise(item.get("security_name"))
        ]

    if not resolutions:
        return {"coverage_status": "unavailable", "missing_scheme_codes": missing_codes, "funds": []}

    result = await CompareDataService(repository).build_mutual_fund_compare(
        [str(row.get("scheme_name")) for row in rows],
        pre_resolutions=resolutions,
        trace_id="manual-mf-coverage-diagnostic",
    )
    comparison = result.get("quant_data", {}).get("comparison", {})
    funds = []
    for name, item in comparison.items():
        code = str(item.get("scheme_code") or "")
        quality = item.get("data_quality") or {}
        history = item.get("history_coverage") or {}
        funds.append({
            "scheme_code": code,
            "name": name,
            "category": item.get("category"),
            "benchmark": item.get("benchmark"),
            "benchmark_source": item.get("benchmark_source"),
            "risk_level": item.get("risk_level"),
            "nav_date": item.get("nav_date"),
            "history_points": item.get("history_points"),
            "history_supports": history.get("supports"),
            "history_stale": history.get("stale"),
            "returns": {period: item.get(period) for period in ("return_1y", "return_3y", "return_5y")},
            "risk": {metric: item.get(metric) for metric in ("volatility_1y", "max_drawdown_1y", "sharpe_ratio", "alpha_vs_nifty", "beta")},
            "cost": {"expense_ratio": item.get("expense_ratio"), "aum": item.get("aum")},
            "holdings_count": len(item.get("holdings") or []),
            "raw_holding_noise": raw_holding_noise.get(code, []),
            "coverage_status": quality.get("coverage_status"),
            "missing_fields": quality.get("missing_fields") or [],
            "limitations": quality.get("limitations") or [],
        })

    return {
        "coverage_status": result.get("coverage_status"),
        "missing_scheme_codes": missing_codes,
        "funds": funds,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only mutual-fund comparison coverage diagnostic.")
    parser.add_argument("scheme_codes", nargs="+", help="AMFI scheme codes, for example 118955 122639")
    args = parser.parse_args()
    print(json.dumps(asyncio.run(_diagnose(args.scheme_codes)), indent=2, default=str))


if __name__ == "__main__":
    main()
