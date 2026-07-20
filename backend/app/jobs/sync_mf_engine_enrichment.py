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
from app.services import mf_engine_service
from app.services.mf_metrics_service import compute_nav_metrics

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PROVIDER = mf_engine_service.PROVIDER


def _enabled(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def main() -> int:
    if not _enabled("ENABLE_MF_ENGINE_SYNC", False):
        logger.info("ENABLE_MF_ENGINE_SYNC is false. Skipping MF Engine enrichment.")
        return 0

    parser = argparse.ArgumentParser()
    parser.add_argument("--scheme-codes", default="", help="Comma-separated AMFI scheme codes.")
    parser.add_argument("--amc", default="", help="Optional AMC filter passed to MF Engine.")
    parser.add_argument("--limit", type=int, default=int(os.getenv("MF_ENGINE_SYNC_SCHEME_LIMIT", "200")))
    parser.add_argument("--page-size", type=int, default=int(os.getenv("MF_ENGINE_PAGE_SIZE", "100")))
    parser.add_argument("--sleep-seconds", type=float, default=float(os.getenv("MF_ENGINE_REQUEST_SLEEP_SECONDS", "0.5")))
    parser.add_argument("--holding-months", type=int, default=int(os.getenv("MF_ENGINE_HOLDING_MONTHS", "2")))
    args = parser.parse_args()

    if not mf_engine_service.is_configured():
        logger.info("MF Engine credentials are not configured. Skipping.")
        return 0

    repo = StockRepository()
    if not repo.supabase:
        logger.error("Supabase client is not configured.")
        return 1

    scheme_filter = _parse_codes(args.scheme_codes)
    run = ProviderRun(
        provider=PROVIDER,
        job_name="sync_mf_engine_enrichment",
        status="running",
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        symbols_attempted=0,
        symbols_succeeded=0,
        symbols_failed=0,
        error_summary=None,
        metadata={
            "scheme_limit": args.limit or None,
            "amc": args.amc or None,
            "holding_months": args.holding_months,
        },
    )
    run_id = repo.create_provider_run(run)

    schemes = _load_schemes(args.page_size, args.limit, args.amc or None)
    if scheme_filter:
        schemes = [scheme for scheme in schemes if str(scheme.get("scheme_code") or "") in scheme_filter]
    run.symbols_attempted = len(schemes)

    for scheme in schemes:
        try:
            normalized = _build_enriched_scheme(repo, scheme, args.holding_months)
            scheme_code = normalized.get("scheme_code")
            if not scheme_code:
                raise RuntimeError("scheme_code_not_resolved")

            nav_rows = normalized.get("nav_history") or []
            for key, value in compute_nav_metrics(nav_rows).items() if nav_rows else []:
                if value is not None:
                    normalized[key] = value

            core_row = _merge_core_snapshot(repo.get_mutual_fund_core_snapshot(str(scheme_code)) or {}, normalized)
            repo.upsert_mutual_fund_core_snapshot_rows([core_row])
            _upsert_legacy_mutual_funds_row(repo, core_row)

            holdings = normalized.get("holdings") or []
            if holdings:
                repo.upsert_mutual_fund_holdings_rows(holdings)
                sectors = _build_sector_rows(str(scheme_code), holdings)
                repo.upsert_mutual_fund_sector_rows(sectors)

            run.symbols_succeeded += 1
        except Exception as exc:
            run.symbols_failed += 1
            logger.error("MF Engine sync failed for %s: %s", scheme.get("scheme_name") or scheme.get("scheme_code"), exc)
            repo.log_data_quality_issue(
                DataQualityIssue(
                    symbol=f"MF:{scheme.get('scheme_code') or scheme.get('provider_scheme_id') or 'unknown'}",
                    table_name="mutual_fund_core_snapshot",
                    issue_type="sync_error",
                    issue_message=str(exc),
                    source=PROVIDER,
                )
            )
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    run.status = "success" if run.symbols_failed == 0 else "partial"
    run.finished_at = datetime.now(timezone.utc)
    run.metadata = {**(run.metadata or {}), "schemes_succeeded": run.symbols_succeeded}
    if run_id:
        repo.update_provider_run(run_id, run)
    logger.info(
        "MF Engine sync summary: attempted=%s succeeded=%s failed=%s",
        run.symbols_attempted,
        run.symbols_succeeded,
        run.symbols_failed,
    )
    return 0 if run.symbols_failed == 0 else 1


def _load_schemes(page_size: int, limit: int, amc: str | None) -> list[dict[str, Any]]:
    schemes: list[dict[str, Any]] = []
    page = 1
    max_rows = max(limit, 1) if limit > 0 else 20000
    while len(schemes) < max_rows:
        result = mf_engine_service.list_schemes(limit=page_size, page=page, amc=amc)
        if not result.get("ok"):
            raise RuntimeError(result.get("error") or "scheme_list_unavailable")
        rows = result.get("data") or []
        if not rows:
            break
        schemes.extend(rows)
        if len(rows) < page_size:
            break
        total = result.get("total")
        if total and len(schemes) >= int(total):
            break
        page += 1
    return schemes[:max_rows]


def _build_enriched_scheme(repo: StockRepository, scheme: dict[str, Any], holding_months: int) -> dict[str, Any]:
    provider_scheme_id = scheme.get("provider_scheme_id")
    merged = dict(scheme)

    if provider_scheme_id:
        detail = mf_engine_service.get_scheme_mf_data(provider_scheme_id)
        if detail.get("data"):
            merged = _merge_non_empty(merged, detail["data"])
        if not merged.get("scheme_name"):
            detail = mf_engine_service.get_scheme(provider_scheme_id)
            if detail.get("data"):
                merged = _merge_non_empty(merged, detail["data"])

    isin = merged.get("isin_growth") or merged.get("isin_div_reinvestment")
    factsheet: dict[str, Any] = {}
    if isin:
        factsheet_result = mf_engine_service.get_factsheet(str(isin))
        if factsheet_result.get("data"):
            factsheet = factsheet_result["data"]
            merged = _merge_non_empty(merged, factsheet)

    scheme_code = _resolve_scheme_code(repo, merged)
    merged["scheme_code"] = scheme_code
    if not scheme_code:
        return merged

    holdings: list[dict[str, Any]] = []
    if provider_scheme_id:
        changes = mf_engine_service.get_holding_changes(provider_scheme_id, months=holding_months)
        for row in changes.get("data") or []:
            holding = _holding_row(str(scheme_code), row)
            if holding:
                holdings.append(holding)

    nav_history: list[dict[str, Any]] = []
    if provider_scheme_id:
        nav = mf_engine_service.get_nav(provider_scheme_id)
        for row in nav.get("data") or []:
            nav_row = dict(row)
            nav_row["scheme_code"] = str(scheme_code)
            if nav_row.get("nav_date") and nav_row.get("nav") is not None:
                nav_history.append(nav_row)

    merged["holdings"] = holdings
    merged["nav_history"] = nav_history
    merged["factsheet"] = factsheet
    return merged


def _merge_core_snapshot(existing: dict[str, Any], incoming: dict[str, Any]) -> dict[str, Any]:
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
        "expense_ratio",
        "aum",
        "benchmark",
        "risk_level",
        "fund_manager",
        "alpha",
        "beta",
        "sharpe_ratio",
    )
    nav_owned = {"nav", "nav_date"}
    row = {field: existing.get(field) for field in fields}
    for field in fields:
        value = incoming.get(field)
        if field in nav_owned and existing.get(field) not in (None, ""):
            continue
        if value not in (None, ""):
            row[field] = value

    payload = existing.get("provider_payload") if isinstance(existing.get("provider_payload"), dict) else {}
    payload = dict(payload)
    trace = payload.get("mf_engine_trace") if isinstance(payload.get("mf_engine_trace"), dict) else {}
    trace["scheme"] = {
        "provider_scheme_id": incoming.get("provider_scheme_id"),
        "isin_growth": incoming.get("isin_growth"),
        "isin_div_reinvestment": incoming.get("isin_div_reinvestment"),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if incoming.get("factsheet"):
        trace["factsheet"] = {
            "report_month": incoming.get("report_month"),
            "isin": incoming.get("isin_growth") or incoming.get("isin_div_reinvestment"),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    if incoming.get("holdings"):
        months = sorted({str(row.get("as_of_date")) for row in incoming["holdings"] if row.get("as_of_date")})
        trace["holdings"] = {"report_months": months, "updated_at": datetime.now(timezone.utc).isoformat()}
    payload["mf_engine_trace"] = trace
    payload["mf_engine_payload"] = incoming.get("provider_payload") or incoming.get("factsheet") or {}

    row["scheme_code"] = str(incoming.get("scheme_code") or existing.get("scheme_code"))
    row["data_source"] = _merged_source(existing.get("data_source"), PROVIDER)
    row["provider_payload"] = payload
    return row


def _resolve_scheme_code(repo: StockRepository, data: dict[str, Any]) -> str | None:
    direct = data.get("scheme_code")
    if direct not in (None, ""):
        return str(direct)

    isin = data.get("isin_growth") or data.get("isin_div_reinvestment")
    if isin and repo.supabase:
        for table in ("mutual_fund_core_snapshot", "mutual_funds"):
            try:
                rows = (
                    repo.supabase.table(table)
                    .select("scheme_code")
                    .or_(f"isin_growth.eq.{isin},isin_div_reinvestment.eq.{isin}")
                    .limit(1)
                    .execute()
                    .data
                    or []
                )
                if rows and rows[0].get("scheme_code") not in (None, ""):
                    return str(rows[0]["scheme_code"])
            except Exception:
                continue

    name = str(data.get("scheme_name") or "").strip()
    if name and repo.supabase:
        pattern = f"%{'%'.join(name.lower().replace('.', ' ').replace(',', ' ').split())}%"
        for table in ("mutual_fund_core_snapshot", "mutual_funds"):
            try:
                rows = (
                    repo.supabase.table(table)
                    .select("scheme_code,scheme_name")
                    .ilike("scheme_name", pattern)
                    .limit(1)
                    .execute()
                    .data
                    or []
                )
                if rows and rows[0].get("scheme_code") not in (None, ""):
                    return str(rows[0]["scheme_code"])
            except Exception:
                continue
    return None


def _holding_row(scheme_code: str, row: dict[str, Any]) -> dict[str, Any] | None:
    name = str(row.get("security_name") or "").strip()
    weight = row.get("weight_pct")
    if not name or weight is None:
        return None
    as_of_date = row.get("as_of_date") or datetime.now(timezone.utc).date().replace(day=1).isoformat()
    return {
        "scheme_code": int(scheme_code) if str(scheme_code).isdigit() else scheme_code,
        "as_of_date": as_of_date,
        "family_id": row.get("provider_scheme_id"),
        "holding_type": row.get("holding_type") or "equity",
        "security_name": name,
        "isin": row.get("isin") or "",
        "sector": row.get("sector"),
        "weight_pct": weight,
        "quantity": row.get("quantity"),
        "market_value_cr": row.get("market_value_cr"),
        "source": PROVIDER,
        "provider_payload": row.get("provider_payload") or row,
    }


def _build_sector_rows(scheme_code: str, holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for row in holdings:
        sector = str(row.get("sector") or "").strip()
        if not sector:
            continue
        try:
            weight = float(row.get("weight_pct") or 0)
        except (TypeError, ValueError):
            continue
        totals[sector] = totals.get(sector, 0.0) + weight
        counts[sector] = counts.get(sector, 0) + 1
    return [
        {
            "scheme_code": str(scheme_code),
            "family_id": None,
            "sector": sector,
            "weight_pct": round(weight, 6),
            "stock_count": counts.get(sector),
            "source": PROVIDER,
            "provider_payload": {"source": PROVIDER},
        }
        for sector, weight in totals.items()
    ]


def _merge_non_empty(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in update.items():
        if value not in (None, "", [], {}):
            merged[key] = value
    return merged


def _merged_source(existing: Any, incoming: str) -> str:
    sources = []
    for value in (existing, incoming):
        for part in str(value or "").split("+"):
            part = part.strip()
            if part and part not in sources:
                sources.append(part)
    return "+".join(sources)


def _parse_codes(raw: str | None) -> set[str]:
    return {item.strip() for item in str(raw or "").split(",") if item.strip()}


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
        logger.warning("Legacy mutual_funds MF Engine upsert failed for %s: %s", snapshot_row.get("scheme_code"), exc)


if __name__ == "__main__":
    raise SystemExit(main())
