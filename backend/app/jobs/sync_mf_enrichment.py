from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.models.stock_models import DataQualityIssue, ProviderRun
from app.repositories.stock_repository import StockRepository
from app.services import mfdata_service

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _enabled(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main() -> None:
    if not _enabled("ENABLE_MF_ENRICHMENT_SYNC", False):
        logger.info("ENABLE_MF_ENRICHMENT_SYNC is false. Skipping MFdata enrichment.")
        return

    parser = argparse.ArgumentParser()
    parser.add_argument("--scheme-codes", type=str, default="")
    parser.add_argument("--limit", type=int, default=int(os.getenv("MFDATA_SYNC_SCHEME_LIMIT", "200")))
    parser.add_argument("--sleep-seconds", type=float, default=float(os.getenv("MFDATA_REQUEST_SLEEP_SECONDS", "6.5")))
    args = parser.parse_args()

    repo = StockRepository()
    if not repo.supabase:
        logger.error("Supabase client is not configured.")
        return

    scheme_codes = _parse_codes(args.scheme_codes) or _existing_scheme_codes(repo)
    if args.limit > 0:
        scheme_codes = scheme_codes[: args.limit]

    run = ProviderRun(
        provider=mfdata_service.PROVIDER,
        job_name="sync_mf_enrichment",
        status="running",
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        symbols_attempted=len(scheme_codes),
        symbols_succeeded=0,
        symbols_failed=0,
        error_summary=None,
        metadata={"scheme_limit": args.limit or None, "sleep_seconds": args.sleep_seconds},
    )
    run_id = repo.create_provider_run(run)

    for scheme_code in scheme_codes:
        try:
            details = mfdata_service.get_scheme_details(scheme_code)
            data = details.get("data") if details.get("ok") else None
            if not data:
                raise RuntimeError(details.get("error") or "scheme_details_unavailable")

            existing = repo.get_mutual_fund_core_snapshot(scheme_code) or {}
            snapshot = _merge_snapshot(existing, data)
            repo.upsert_mutual_fund_core_snapshot_rows([snapshot])
            _upsert_legacy_mutual_funds_row(repo, snapshot)

            family_id = _family_id(data)
            if family_id:
                holdings = mfdata_service.get_family_holdings(family_id, scheme_code=scheme_code)
                if holdings.get("data"):
                    repo.upsert_mutual_fund_holdings_rows(holdings["data"])
                sectors = mfdata_service.get_family_sectors(family_id, scheme_code=scheme_code)
                if sectors.get("data"):
                    repo.upsert_mutual_fund_sector_rows(sectors["data"])

            run.symbols_succeeded += 1
        except Exception as exc:
            run.symbols_failed += 1
            logger.error("MFdata enrichment failed for %s: %s", scheme_code, exc)
            repo.log_data_quality_issue(
                DataQualityIssue(
                    symbol=f"MF:{scheme_code}",
                    table_name="mutual_fund_core_snapshot",
                    issue_type="sync_error",
                    issue_message=str(exc),
                    source=mfdata_service.PROVIDER,
                )
            )
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    run.status = "success" if run.symbols_failed == 0 else "partial"
    run.finished_at = datetime.now(timezone.utc)
    if run_id:
        repo.update_provider_run(run_id, run)
    logger.info("MFdata enrichment summary: attempted=%s succeeded=%s failed=%s", run.symbols_attempted, run.symbols_succeeded, run.symbols_failed)


def _merge_snapshot(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
    fields = (
        "scheme_code",
        "scheme_name",
        "amc_name",
        "category",
        "sub_category",
        "plan_type",
        "option_type",
        "fund_type",
        "nav",
        "nav_date",
        "return_1m",
        "return_3m",
        "return_6m",
        "return_1y",
        "return_3y",
        "return_5y",
        "volatility_1y",
        "max_drawdown_1y",
        "expense_ratio",
        "aum",
        "benchmark",
        "risk_level",
        "fund_manager",
        "alpha",
        "beta",
        "sharpe_ratio",
        "data_source",
        "provider_payload",
    )
    merged = {field: existing.get(field) for field in fields}
    nav_owned_fields = {
        "nav",
        "nav_date",
        "return_1m",
        "return_3m",
        "return_6m",
        "return_1y",
        "return_3y",
        "return_5y",
        "volatility_1y",
        "max_drawdown_1y",
        "alpha",
        "beta",
        "sharpe_ratio",
    }
    for field in fields:
        value = incoming.get(field)
        if field == "provider_payload":
            merged[field] = _merge_provider_payload(existing.get(field), incoming.get(field))
            continue
        if field in nav_owned_fields and existing.get(field) not in (None, ""):
            continue
        if field not in nav_owned_fields and existing.get(field) not in (None, ""):
            continue
        if value not in (None, ""):
            merged[field] = value
    merged["scheme_code"] = str(incoming.get("scheme_code") or existing.get("scheme_code"))
    merged["data_source"] = _merged_source(existing.get("data_source"), incoming.get("data_source"))
    return merged


def _merged_source(existing: Any, incoming: Any) -> str:
    sources = []
    for value in (existing, incoming):
        for part in str(value or "").split("+"):
            if part and part not in sources:
                sources.append(part)
    return "+".join(sources) if sources else mfdata_service.PROVIDER


def _merge_provider_payload(existing: Any, incoming: Any) -> dict[str, Any]:
    base = existing if isinstance(existing, dict) else {}
    update = incoming if isinstance(incoming, dict) else {}
    merged = dict(base)
    merged.update(update)
    return merged


def _family_id(data: dict[str, Any]) -> str | None:
    payload = data.get("provider_payload") if isinstance(data.get("provider_payload"), dict) else {}
    value = payload.get("family_id") or data.get("family_id")
    return str(value) if value not in (None, "") else None


def _existing_scheme_codes(repo: StockRepository) -> list[str]:
    rows: list[dict[str, Any]] = []
    for table in ("mutual_fund_core_snapshot", "mutual_funds"):
        try:
            res = repo.supabase.table(table).select("scheme_code").limit(20000).execute()
            rows.extend(res.data or [])
        except Exception as exc:
            logger.warning("Failed to load scheme codes from %s: %s", table, exc)
    return sorted({str(row.get("scheme_code")) for row in rows if row.get("scheme_code")})


def _parse_codes(raw: str | None) -> list[str]:
    seen = set()
    codes = []
    for item in (raw or "").split(","):
        code = item.strip()
        if code and code not in seen:
            seen.add(code)
            codes.append(code)
    return codes


def _upsert_legacy_mutual_funds_row(repo: StockRepository, snapshot_row: dict[str, Any]) -> None:
    payload = {
        "scheme_code": int(snapshot_row["scheme_code"]) if str(snapshot_row["scheme_code"]).isdigit() else snapshot_row["scheme_code"],
        "scheme_name": snapshot_row.get("scheme_name"),
        "fund_house": snapshot_row.get("amc_name"),
        "category": snapshot_row.get("category"),
        "sub_category": snapshot_row.get("sub_category"),
        "nav": snapshot_row.get("nav"),
        "nav_date": snapshot_row.get("nav_date"),
        "expense_ratio": snapshot_row.get("expense_ratio"),
        "aum": snapshot_row.get("aum"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    try:
        repo.supabase.table("mutual_funds").upsert(payload, on_conflict="scheme_code").execute()
    except Exception as exc:
        logger.warning("Legacy mutual_funds enrichment upsert failed for %s: %s", snapshot_row.get("scheme_code"), exc)


if __name__ == "__main__":
    main()
