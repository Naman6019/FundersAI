from __future__ import annotations

import logging
import os
import sys
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.models.stock_models import DataQualityIssue, ProviderRun
from app.repositories.stock_repository import StockRepository
from app.services.mf_metrics_service import compute_nav_metrics
from app.services.mfapi_service import get_latest_nav, get_nav_history, list_schemes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _enabled(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _existing_scheme_codes(repo: StockRepository) -> list[str]:
    codes: list[str] = []
    try:
        res = repo.supabase.table("mutual_funds").select("scheme_code").limit(20000).execute()
        for row in res.data or []:
            value = row.get("scheme_code")
            if value is not None:
                codes.append(str(value))
    except Exception:
        pass
    if codes:
        return sorted(set(codes))

    offset = 0
    while len(codes) < 20000:
        batch = list_schemes(limit=1000, offset=offset)
        if not batch.get("ok"):
            break
        rows = batch.get("data") or []
        if not rows:
            break
        codes.extend([row["scheme_code"] for row in rows if row.get("scheme_code")])
        offset += 1000
    return sorted(set(codes))


def _latest_nav_date(repo: StockRepository, scheme_code: str) -> str | None:
    history = repo.get_mutual_fund_nav_history(scheme_code, limit=1)
    if not history:
        return None
    return history[0].get("nav_date")


def _nav_history_count(repo: StockRepository, scheme_code: str, sample_limit: int) -> int:
    sample = repo.get_mutual_fund_nav_history(scheme_code, limit=max(sample_limit, 1))
    return len(sample)


def _merge_sources(*values: object) -> str:
    ordered: list[str] = []
    for value in values:
        for part in str(value or "").split("+"):
            clean = part.strip()
            if clean and clean not in ordered:
                ordered.append(clean)
    return "+".join(ordered)


def _merge_provider_payload(existing: object, incoming: object) -> dict:
    base = existing if isinstance(existing, dict) else {}
    update = incoming if isinstance(incoming, dict) else {}
    merged = dict(base)
    merged.update(update)
    return merged


def _to_date_value(value: object):
    if value in (None, ""):
        return None
    try:
        return datetime.fromisoformat(str(value)[:10]).date()
    except ValueError:
        return None


def _select_nav(existing: dict, latest: dict) -> tuple[object, object]:
    existing_date = _to_date_value(existing.get("nav_date"))
    latest_date = _to_date_value(latest.get("nav_date"))
    if existing.get("nav") not in (None, "") and existing_date and latest_date and existing_date >= latest_date:
        return existing.get("nav"), existing.get("nav_date")
    return latest.get("nav"), latest.get("nav_date")


def _upsert_legacy_mutual_funds_row(repo: StockRepository, snapshot_row: dict) -> None:
    if not repo.supabase:
        return
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
        logger.warning("Legacy mutual_funds upsert failed for %s: %s", snapshot_row.get("scheme_code"), exc)


def main() -> None:
    if not _enabled("ENABLE_MF_NAV_SYNC", True):
        logger.info("ENABLE_MF_NAV_SYNC is false. Skipping MF NAV sync.")
        return

    repo = StockRepository()
    if not repo.supabase:
        logger.error("Supabase client is not configured.")
        return

    scheme_codes = _existing_scheme_codes(repo)
    limit = int(os.getenv("MF_SYNC_SCHEME_LIMIT", "0"))
    min_history_rows = int(os.getenv("MF_NAV_MIN_HISTORY_ROWS", "750"))
    if limit > 0:
        scheme_codes = scheme_codes[:limit]

    run = ProviderRun(
        provider="mfapi",
        job_name="sync_mf_nav",
        status="running",
        started_at=datetime.now(timezone.utc),
        finished_at=None,
        symbols_attempted=len(scheme_codes),
        symbols_succeeded=0,
        symbols_failed=0,
        error_summary=None,
        metadata={"scheme_limit": limit or None, "min_history_rows": min_history_rows},
    )
    run_id = repo.create_provider_run(run)

    for scheme_code in scheme_codes:
        try:
            latest_result = get_latest_nav(scheme_code)
            latest = latest_result.get("data") if latest_result.get("ok") else None
            if not latest:
                raise RuntimeError(latest_result.get("error") or "latest_nav_unavailable")

            existing = repo.get_mutual_fund_core_snapshot(scheme_code) or {}

            history_count = _nav_history_count(repo, scheme_code, min_history_rows + 1)
            start_date = _latest_nav_date(repo, scheme_code)
            if history_count < min_history_rows:
                # Force a full history pull when local history is too thin,
                # otherwise metrics stay null even though latest NAV exists.
                start_date = None
            history_result = get_nav_history(scheme_code, start_date=start_date)
            history_rows = history_result.get("data") if history_result.get("ok") else []
            if history_rows:
                repo.upsert_mutual_fund_nav_history_rows(history_rows)

            full_history = repo.get_mutual_fund_nav_history(scheme_code, limit=4000)
            metrics = compute_nav_metrics(full_history)
            selected_nav, selected_nav_date = _select_nav(existing, latest)

            snapshot_row = {
                "scheme_code": str(scheme_code),
                "scheme_name": latest.get("scheme_name"),
                "amc_name": latest.get("amc_name"),
                "category": latest.get("category") or existing.get("category"),
                "sub_category": existing.get("sub_category"),
                "plan_type": existing.get("plan_type"),
                "option_type": existing.get("option_type"),
                "fund_type": latest.get("fund_type") or existing.get("fund_type"),
                "nav": selected_nav,
                "nav_date": selected_nav_date,
                "return_1m": metrics.get("return_1m"),
                "return_3m": metrics.get("return_3m"),
                "return_6m": metrics.get("return_6m"),
                "return_1y": metrics.get("return_1y"),
                "return_3y": metrics.get("return_3y"),
                "return_5y": metrics.get("return_5y"),
                "volatility_1y": metrics.get("volatility_1y"),
                "max_drawdown_1y": metrics.get("max_drawdown_1y"),
                "expense_ratio": existing.get("expense_ratio"),
                "aum": existing.get("aum"),
                "benchmark": existing.get("benchmark"),
                "risk_level": existing.get("risk_level"),
                "fund_manager": existing.get("fund_manager"),
                "alpha": metrics.get("alpha"),
                "beta": metrics.get("beta"),
                "sharpe_ratio": metrics.get("sharpe_ratio"),
                "data_source": _merge_sources(existing.get("data_source"), "mfapi"),
                "provider_payload": _merge_provider_payload(existing.get("provider_payload"), latest.get("provider_payload")),
            }
            repo.upsert_mutual_fund_core_snapshot_rows([snapshot_row])
            _upsert_legacy_mutual_funds_row(repo, snapshot_row)
            run.symbols_succeeded += 1
        except Exception as exc:
            run.symbols_failed += 1
            logger.error("MF NAV sync failed for %s: %s", scheme_code, exc)
            repo.log_data_quality_issue(
                DataQualityIssue(
                    symbol=f"MF:{scheme_code}",
                    table_name="mutual_fund_core_snapshot",
                    issue_type="sync_error",
                    issue_message=str(exc),
                    source="mfapi",
                )
            )

    run.status = "success" if run.symbols_failed == 0 else "partial"
    run.finished_at = datetime.now(timezone.utc)
    run.metadata = {**(run.metadata or {}), "schemes_succeeded": run.symbols_succeeded}
    if run_id:
        repo.update_provider_run(run_id, run)

    logger.info(
        "MF sync summary: attempted=%s succeeded=%s failed=%s",
        run.symbols_attempted,
        run.symbols_succeeded,
        run.symbols_failed,
    )


if __name__ == "__main__":
    main()
