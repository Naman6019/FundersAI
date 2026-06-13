import os
import json
import logging
import asyncio
import sys
import time
import re
import hmac
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Literal
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import httpx
import yfinance as yf
import feedparser
from datetime import datetime, timedelta, timezone
import pytz

from app.services.fund_service import FundService
from app.models.fund_models import FundDetails, FundProfileResponse
import numpy as np
import pandas as pd

# Redirect yfinance cache to the writable /tmp directory
os.environ["YFINANCE_CACHE_DIR"] = "/tmp/yfinance_cache"
yf.set_tz_cache_location("/tmp/yfinance_tz_cache")

# Must run before any os.environ.get()
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase
from app.fetcher import run_eod_fetch
from app.nse_client import fetch_live_quote
from app.stock_universe import resolve_stock_symbol
from app.services.quant_service import (
    build_stock_compare,
    build_stock_profile,
    get_stock_financials,
    get_stock_price_history,
)
from app.services.comparison_reasoning import build_mf_why_better
from app.services import indianapi_service
from app.services.mfapi_service import get_latest_nav as mfapi_get_latest_nav, get_nav_history as mfapi_get_nav_history, search_schemes as mfapi_search_schemes
from app.services.indianapi_quota_guard import evaluate as evaluate_indianapi_quota
from app.services.provider_usage import build_usage_dashboard
from app.services import cache_policy
from app.services.rate_limit import (
    check_rate_limit,
    client_identifier_from_request,
    rate_limit_headers,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://marketmind.vercel.app",
        "https://fundersai.com",
        "https://www.fundersai.com",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _rate_limit_group_for_request(path: str, method: str) -> str | None:
    method = method.upper()
    if path == "/api/chat" and method == "POST":
        return "chat"
    if path.startswith("/api/quant/"):
        return "quant"
    if path.startswith("/api/provider/indianapi/"):
        return "quant"
    if path.startswith("/api/mf/"):
        return "mf-detail"
    if path.startswith("/api/funds/category"):
        return "category-funds"
    if path == "/api/data-health":
        return "data-health"
    if path == "/api/trigger-fetch":
        return "cron-sync-mf"
    if path.startswith("/api/admin/mf-documents/") and method == "POST":
        return "admin-mutation"
    return None


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    group = _rate_limit_group_for_request(request.url.path, request.method)
    if group:
        identity_override = request.headers.get("x-admin-key") if group == "admin-mutation" else None
        identity = client_identifier_from_request(request, identity_override)
        try:
            result = await check_rate_limit(group, identity)
        except Exception as exc:
            logger.warning("event=rate_limit_check_failed path=%s reason=%s", request.url.path, exc)
            if group == "data-health":
                return await call_next(request)
            return JSONResponse(
                {"error": "rate_limit_unavailable", "retry_after_seconds": 60},
                status_code=503,
                headers={"Retry-After": "60"},
            )
        if not result.allowed:
            if group == "data-health" and not result.configured:
                logger.warning("event=rate_limit_unconfigured_bypassed path=%s", request.url.path)
                return await call_next(request)
            status_code = 429 if result.configured else 503
            error = "rate_limited" if result.configured else "rate_limit_unconfigured"
            return JSONResponse(
                {"error": error, "retry_after_seconds": result.retry_after_seconds},
                status_code=status_code,
                headers=rate_limit_headers(result),
            )

    return await call_next(request)

from app.routes.quant import router as quant_router
app.include_router(quant_router)
from app.routes.indianapi import router as indianapi_router
app.include_router(indianapi_router)
from app.routes.mf_ingestion import router as mf_ingestion_router
app.include_router(mf_ingestion_router)

@app.get("/")
def read_root():
    return {"message": "FundersAI API is running. Use /health for health checks."}

@app.get("/health")
@app.head("/health")
def health():
    return {"status": "ok"}


def _to_utc_datetime(value: Any) -> datetime | None:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value).strip()
        if not raw:
            return None
        if len(raw) == 10 and raw[4] == "-" and raw[7] == "-":
            raw = f"{raw}T00:00:00+00:00"
        if raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _age_days(dt: datetime | None, now_utc: datetime) -> float | None:
    if not dt:
        return None
    return max((now_utc - dt).total_seconds() / 86400.0, 0.0)


def _fmt_age(age_days: float | None) -> str | None:
    if age_days is None:
        return None
    return f"{age_days:.1f}d"


def _count_mf_raw_documents(*, status: str | None = None) -> int:
    if not supabase:
        return 0
    query = supabase.table("mf_raw_documents").select("id", count="exact")
    if status:
        query = query.eq("parse_status", status)
    response = query.execute()
    return int(response.count or 0)


def _has_metric_value(value: Any) -> bool:
    return value not in (None, "")


SUPPORTED_MF_AMC_MARKERS = {
    "HDFC": ("hdfc",),
    "SBI": ("sbi",),
    "ICICI": ("icici",),
    "PPFAS": ("ppfas", "parag parikh"),
}


def _core_snapshot_enrichment_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    aum_rows = [row for row in rows if _has_metric_value(row.get("aum"))]
    ter_rows = [row for row in rows if _has_metric_value(row.get("expense_ratio"))]
    both_rows = [row for row in rows if _has_metric_value(row.get("aum")) and _has_metric_value(row.get("expense_ratio"))]
    enriched_rows = [row for row in rows if _has_metric_value(row.get("aum")) or _has_metric_value(row.get("expense_ratio"))]

    def covered_amcs(field: str) -> set[str]:
        covered: set[str] = set()
        for row in rows:
            if not _has_metric_value(row.get(field)):
                continue
            amc_name = str(row.get("amc_name") or "").lower()
            for label, markers in SUPPORTED_MF_AMC_MARKERS.items():
                if any(marker in amc_name for marker in markers):
                    covered.add(label)
        return covered

    latest_dt = max(
        [dt for dt in (_to_utc_datetime(row.get("last_updated")) for row in enriched_rows) if dt is not None],
        default=None,
    )
    return {
        "aum_count": len(aum_rows),
        "ter_count": len(ter_rows),
        "both_count": len(both_rows),
        "supported_total": len(SUPPORTED_MF_AMC_MARKERS),
        "supported_aum_count": len(covered_amcs("aum")),
        "supported_ter_count": len(covered_amcs("expense_ratio")),
        "latest_updated_at": latest_dt,
    }


def _latest_mf_doc_timestamp(*, status: str | None, field: str) -> datetime | None:
    if not supabase:
        return None
    query = supabase.table("mf_raw_documents").select(field).order(field, desc=True).limit(5)
    if status:
        query = query.eq("parse_status", status)
    rows = query.execute().data or []
    for row in rows:
        dt = _to_utc_datetime(row.get(field))
        if dt:
            return dt
    return None


def _require_admin_key(x_admin_key: str | None) -> None:
    expected_admin_key = os.getenv("MF_INTERNAL_ADMIN_KEY", "").strip()
    if not expected_admin_key or not x_admin_key or not hmac.compare_digest(x_admin_key, expected_admin_key):
        raise HTTPException(status_code=403, detail="admin_auth_required")


def _iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class AdminDocumentReviewAction(BaseModel):
    reviewer_notes: str | None = None


def _review_action_notes(payload: AdminDocumentReviewAction | None) -> str | None:
    if not payload or payload.reviewer_notes is None:
        return None
    notes = payload.reviewer_notes.strip()
    return notes or None


def _load_mf_review_document(document_id: str) -> dict[str, Any]:
    if not supabase:
        raise HTTPException(status_code=503, detail="supabase_unavailable")

    rows = (
        supabase.table("mf_raw_documents")
        .select("id,parse_status,validation_issues")
        .eq("id", document_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise HTTPException(status_code=404, detail="document_not_found")
    return rows[0]


def _mark_review_queue(document_id: str, status: str, reviewer_notes: str | None) -> None:
    if not supabase:
        return

    payload: dict[str, Any] = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if reviewer_notes:
        payload["reviewer_notes"] = reviewer_notes

    try:
        (
            supabase.table("mf_parse_review_queue")
            .update(payload)
            .eq("source_document_id", document_id)
            .eq("status", "pending_review")
            .execute()
        )
    except Exception as exc:
        logger.warning("event=review_queue_update_failed source_document_id=%s reason=%s", document_id, exc)


def _request_mf_document_reparse(document_id: str, reviewer_notes: str | None = None) -> dict[str, Any]:
    document = _load_mf_review_document(document_id)
    current_status = str(document.get("parse_status") or "").strip().lower()
    if current_status not in {"needs_review", "failed"}:
        raise HTTPException(status_code=409, detail="document_not_actionable")

    supabase.table("mf_raw_documents").update(
        {
            "parse_status": "needs_reparse",
            "validation_issues": [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", document_id).execute()
    _mark_review_queue(document_id, "reparse_requested", reviewer_notes)
    return {
        "status": "ok",
        "action": "reparse_requested",
        "source_document_id": document_id,
        "parse_status": "needs_reparse",
    }


def _resolve_mf_document_review(document_id: str, reviewer_notes: str | None = None) -> dict[str, Any]:
    document = _load_mf_review_document(document_id)
    current_status = str(document.get("parse_status") or "").strip().lower()
    if current_status != "needs_review":
        raise HTTPException(status_code=409, detail="document_not_in_needs_review")

    now = datetime.now(timezone.utc).isoformat()
    supabase.table("mf_raw_documents").update(
        {
            "parse_status": "parsed",
            "validation_issues": [],
            "parsed_at": now,
            "updated_at": now,
        }
    ).eq("id", document_id).execute()
    _mark_review_queue(document_id, "approved", reviewer_notes)
    return {
        "status": "ok",
        "action": "resolved",
        "source_document_id": document_id,
        "parse_status": "parsed",
    }


def _skip_mf_document_review(document_id: str, reviewer_notes: str | None = None) -> dict[str, Any]:
    document = _load_mf_review_document(document_id)
    current_status = str(document.get("parse_status") or "").strip().lower()
    if current_status not in {"needs_review", "failed", "needs_reparse"}:
        raise HTTPException(status_code=409, detail="document_not_actionable")

    issues = document.get("validation_issues") if isinstance(document.get("validation_issues"), list) else []
    cleaned_issues = [str(issue) for issue in issues if str(issue or "").strip()]
    if "skipped_irrelevant_document" not in cleaned_issues:
        cleaned_issues.append("skipped_irrelevant_document")

    now = datetime.now(timezone.utc).isoformat()
    supabase.table("mf_raw_documents").update(
        {
            "parse_status": "skipped_not_supported",
            "validation_issues": cleaned_issues,
            "parsed_at": now,
            "updated_at": now,
        }
    ).eq("id", document_id).execute()
    _mark_review_queue(document_id, "skipped", reviewer_notes)
    return {
        "status": "ok",
        "action": "skipped",
        "source_document_id": document_id,
        "parse_status": "skipped_not_supported",
    }


@app.get("/api/data-health")
def data_health():
    now_utc = datetime.now(timezone.utc)
    metrics = [
        {"label": "MF NAV", "status": "Missing", "note": "No NAV snapshot rows found.", "last_updated": None},
        {"label": "AUM / TER", "status": "Missing", "note": "No AUM+TER rows found.", "last_updated": None},
        {"label": "Risk metrics", "status": "Missing", "note": "No risk metric rows found.", "last_updated": None},
        {"label": "AMC docs", "status": "Missing", "note": "No parsed AMC factsheet/disclosure docs found.", "last_updated": None},
    ]

    if not supabase:
        return {
            "status": "degraded",
            "source": "supabase_unavailable",
            "checked_at": now_utc.isoformat(),
            "metrics": metrics,
        }

    try:
        core_rows = (
            supabase.table("mutual_fund_core_snapshot")
            .select("scheme_code,nav_date,last_updated,aum,expense_ratio,alpha,beta,sharpe_ratio,volatility_1y,max_drawdown_1y")
            .order("last_updated", desc=True)
            .limit(300)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("Data health core snapshot read failed: %s", exc)
        return {
            "status": "degraded",
            "source": "read_error",
            "checked_at": now_utc.isoformat(),
            "metrics": [
                {"label": "MF NAV", "status": "Error", "note": "Core snapshot read failed.", "last_updated": None},
                {"label": "AUM / TER", "status": "Error", "note": "Core snapshot read failed.", "last_updated": None},
                {"label": "Risk metrics", "status": "Error", "note": "Core snapshot read failed.", "last_updated": None},
                {"label": "AMC docs", "status": "Missing", "note": "Not checked due core snapshot read failure.", "last_updated": None},
            ],
        }

    try:
        enrichment_rows = (
            supabase.table("mutual_fund_core_snapshot")
            .select("scheme_code,amc_name,last_updated,aum,expense_ratio")
            .limit(10000)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("Data health enrichment coverage read failed: %s", exc)
        enrichment_rows = core_rows

    latest_nav_dt = max(
        [dt for dt in (_to_utc_datetime(row.get("nav_date")) for row in core_rows) if dt is not None],
        default=None,
    )
    nav_age_days = _age_days(latest_nav_dt, now_utc)
    if latest_nav_dt:
        nav_is_fresh = cache_policy.is_fresh(latest_nav_dt.isoformat(), "mutual_fund_nav", now=now_utc)
        if nav_is_fresh:
            metrics[0].update(status="Fresh", note=f"Latest NAV age {_fmt_age(nav_age_days)}.", last_updated=latest_nav_dt.isoformat())
        elif nav_age_days is not None and nav_age_days <= 7:
            metrics[0].update(status="Lagging", note=f"Latest NAV age {_fmt_age(nav_age_days)}.", last_updated=latest_nav_dt.isoformat())
        else:
            metrics[0].update(status="Stale", note=f"Latest NAV age {_fmt_age(nav_age_days)}.", last_updated=latest_nav_dt.isoformat())

    enrichment = _core_snapshot_enrichment_summary(enrichment_rows)
    latest_aum_ter_dt = enrichment["latest_updated_at"]
    aum_ter_age_days = _age_days(latest_aum_ter_dt, now_utc)
    aum_ter_note = (
        f"AUM rows={enrichment['aum_count']}, TER rows={enrichment['ter_count']}, "
        f"both={enrichment['both_count']}, supported_amcs_aum={enrichment['supported_aum_count']}/"
        f"{enrichment['supported_total']}, supported_amcs_ter={enrichment['supported_ter_count']}/"
        f"{enrichment['supported_total']}"
    )
    if latest_aum_ter_dt:
        enrich_is_fresh = cache_policy.is_fresh(latest_aum_ter_dt.isoformat(), "mutual_fund_enrichment", now=now_utc)
        if not enrichment["aum_count"] or not enrichment["ter_count"]:
            metrics[1].update(status="Partial", note=f"{aum_ter_note}. Latest enrichment age {_fmt_age(aum_ter_age_days)}.", last_updated=latest_aum_ter_dt.isoformat())
        elif enrich_is_fresh:
            metrics[1].update(status="Synced", note=f"{aum_ter_note}. Latest enrichment age {_fmt_age(aum_ter_age_days)}.", last_updated=latest_aum_ter_dt.isoformat())
        elif aum_ter_age_days is not None and aum_ter_age_days <= 60:
            metrics[1].update(status="Lagging", note=f"{aum_ter_note}. Latest enrichment age {_fmt_age(aum_ter_age_days)}.", last_updated=latest_aum_ter_dt.isoformat())
        else:
            metrics[1].update(status="Stale", note=f"{aum_ter_note}. Latest enrichment age {_fmt_age(aum_ter_age_days)}.", last_updated=latest_aum_ter_dt.isoformat())

    def _risk_row_ready(row: dict[str, Any]) -> bool:
        # Treat NAV-derived risk signals as valid coverage even when
        # alpha/beta are not persisted yet for every scheme.
        values = [
            row.get("volatility_1y"),
            row.get("max_drawdown_1y"),
            row.get("sharpe_ratio"),
            row.get("alpha"),
            row.get("beta"),
        ]
        present = sum(1 for value in values if value not in (None, ""))
        return present >= 2

    risk_rows = [row for row in core_rows if _risk_row_ready(row)]
    latest_risk_dt = max(
        [dt for dt in (_to_utc_datetime(row.get("last_updated")) for row in risk_rows) if dt is not None],
        default=None,
    )
    risk_age_days = _age_days(latest_risk_dt, now_utc)
    if latest_risk_dt:
        if latest_nav_dt and nav_age_days is not None and nav_age_days <= 7:
            metrics[2].update(status="Ready", note=f"Risk rows present. Latest age {_fmt_age(risk_age_days)}.", last_updated=latest_risk_dt.isoformat())
        elif risk_age_days is not None and risk_age_days <= 35:
            metrics[2].update(status="Partial", note=f"Risk rows present, NAV freshness lagging ({_fmt_age(nav_age_days)}).", last_updated=latest_risk_dt.isoformat())
        else:
            metrics[2].update(status="Stale", note=f"Risk rows stale ({_fmt_age(risk_age_days)}).", last_updated=latest_risk_dt.isoformat())

    pipeline = {
        "source_table": "mf_raw_documents",
        "total_documents": 0,
        "parsed_count": 0,
        "pending_count": 0,
        "failed_count": 0,
        "needs_review_count": 0,
        "skipped_count": 0,
        "last_downloaded_at": None,
        "last_parse_attempt_at": None,
        "last_success_at": None,
        "last_failure_at": None,
    }
    try:
        pending_count = (
            _count_mf_raw_documents(status="pending")
            + _count_mf_raw_documents(status="downloaded")
            + _count_mf_raw_documents(status="needs_reparse")
        )
        parsed_count = _count_mf_raw_documents(status="parsed")
        failed_count = _count_mf_raw_documents(status="failed")
        needs_review_count = _count_mf_raw_documents(status="needs_review")
        skipped_count = _count_mf_raw_documents(status="skipped_not_supported")
        total_documents = _count_mf_raw_documents()
        last_downloaded_dt = _latest_mf_doc_timestamp(status=None, field="downloaded_at")
        last_parse_attempt_dt = _latest_mf_doc_timestamp(status=None, field="parsed_at")
        last_success_dt = _latest_mf_doc_timestamp(status="parsed", field="parsed_at")
        last_failure_dt = _latest_mf_doc_timestamp(status="failed", field="parsed_at")

        pipeline.update(
            total_documents=total_documents,
            parsed_count=parsed_count,
            pending_count=pending_count,
            failed_count=failed_count,
            needs_review_count=needs_review_count,
            skipped_count=skipped_count,
            last_downloaded_at=last_downloaded_dt.isoformat() if last_downloaded_dt else None,
            last_parse_attempt_at=last_parse_attempt_dt.isoformat() if last_parse_attempt_dt else None,
            last_success_at=last_success_dt.isoformat() if last_success_dt else None,
            last_failure_at=last_failure_dt.isoformat() if last_failure_dt else None,
        )

        if total_documents == 0:
            metrics[3].update(
                status="Missing",
                note="No AMC docs ingested yet.",
                last_updated=None,
            )
        else:
            success_age_days = _age_days(last_success_dt, now_utc)
            success_age = _fmt_age(success_age_days) or "n/a"
            note = (
                f"parsed={parsed_count}, pending={pending_count}, failed={failed_count}, "
                f"review={needs_review_count}, skipped={skipped_count}, total={total_documents}"
            )

            if failed_count > 0 and not last_success_dt:
                metrics[3].update(
                    status="Error",
                    note=f"{note}. Failed parses exist and no successful parse yet.",
                    last_updated=last_failure_dt.isoformat() if last_failure_dt else None,
                )
            elif pending_count > 0:
                metrics[3].update(
                    status="Processing",
                    note=f"{note}. Last successful parse age {success_age}.",
                    last_updated=last_parse_attempt_dt.isoformat() if last_parse_attempt_dt else (last_success_dt.isoformat() if last_success_dt else None),
                )
            elif last_success_dt and success_age_days is not None and success_age_days <= 45:
                if failed_count > 0 or needs_review_count > 0:
                    metrics[3].update(
                        status="Partial",
                        note=f"{note}. Last successful parse age {success_age}.",
                        last_updated=last_success_dt.isoformat(),
                    )
                else:
                    metrics[3].update(
                        status="Indexed",
                        note=f"{note}. Last successful parse age {success_age}.",
                        last_updated=last_success_dt.isoformat(),
                    )
            elif last_success_dt:
                metrics[3].update(
                    status="Stale",
                    note=f"{note}. Last successful parse age {success_age}.",
                    last_updated=last_success_dt.isoformat(),
                )
            else:
                metrics[3].update(
                    status="Missing",
                    note=f"{note}. No successful parse found yet.",
                    last_updated=last_parse_attempt_dt.isoformat() if last_parse_attempt_dt else None,
                )
    except Exception as exc:
        logger.warning("Data health AMC docs read failed: %s", exc)
        metrics[3].update(status="Error", note="AMC docs pipeline tables not readable.", last_updated=None)

    bad_statuses = {"Stale", "Missing", "Error"}
    overall = "ok" if all(metric["status"] not in bad_statuses for metric in metrics) else "degraded"
    return {
        "status": overall,
        "source": "supabase_snapshot",
        "checked_at": now_utc.isoformat(),
        "metrics": metrics,
        "pipeline": pipeline,
    }


@app.get("/api/admin/ops-overview")
def admin_ops_overview(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    _require_admin_key(x_admin_key)
    now_utc = datetime.now(timezone.utc)
    if not supabase:
        raise HTTPException(status_code=503, detail="supabase_unavailable")

    workflow_runs: list[dict[str, Any]] = []
    workflow_source_table = "data_provider_runs"
    try:
        rows = (
            supabase.table("data_provider_runs")
            .select("provider,job_name,status,started_at,finished_at,symbols_attempted,symbols_succeeded,symbols_failed,error_summary,metadata")
            .order("started_at", desc=True)
            .limit(120)
            .execute()
            .data
            or []
        )
    except Exception:
        rows = []

    if not rows:
        workflow_source_table = "provider_runs"
        try:
            rows = (
                supabase.table("provider_runs")
                .select("provider,job_name,status,started_at,finished_at,symbols_attempted,symbols_succeeded,symbols_failed,error_summary,metadata")
                .order("started_at", desc=True)
                .limit(120)
                .execute()
                .data
                or []
            )
        except Exception:
            rows = []

    for row in rows:
        started_at = _to_utc_datetime(row.get("started_at"))
        finished_at = _to_utc_datetime(row.get("finished_at"))
        duration_seconds = None
        if started_at and finished_at:
            duration_seconds = max(int((finished_at - started_at).total_seconds()), 0)
        workflow_runs.append(
            {
                "provider": row.get("provider"),
                "job_name": row.get("job_name"),
                "status": row.get("status"),
                "started_at": _iso_or_none(started_at),
                "finished_at": _iso_or_none(finished_at),
                "duration_seconds": duration_seconds,
                "symbols_attempted": int(row.get("symbols_attempted") or 0),
                "symbols_succeeded": int(row.get("symbols_succeeded") or 0),
                "symbols_failed": int(row.get("symbols_failed") or 0),
                "error_summary": row.get("error_summary"),
                "metadata": row.get("metadata") if isinstance(row.get("metadata"), dict) else {},
            }
        )

    status_summary: dict[str, int] = {}
    failures_24h = 0
    successes_24h = 0
    window_24h = now_utc - timedelta(hours=24)
    for run in workflow_runs:
        status = str(run.get("status") or "unknown").strip().lower()
        status_summary[status] = status_summary.get(status, 0) + 1
        started_at = _to_utc_datetime(run.get("started_at"))
        if not started_at or started_at < window_24h:
            continue
        if status in {"success", "ok", "completed", "done"}:
            successes_24h += 1
        elif status in {"failed", "error", "partial_failed", "timeout"}:
            failures_24h += 1

    mf_pipeline_rows: list[dict[str, Any]] = []
    try:
        raw_rows = (
            supabase.table("mf_raw_documents")
            .select("amc_code,source_document_type,parse_status,downloaded_at,parsed_at,updated_at")
            .order("downloaded_at", desc=True)
            .limit(12000)
            .execute()
            .data
            or []
        )
    except Exception:
        raw_rows = []

    pipeline_map: dict[tuple[str, str], dict[str, Any]] = {}
    pending_statuses = {"pending", "downloaded", "needs_reparse"}
    for row in raw_rows:
        amc_code = str(row.get("amc_code") or "UNKNOWN").strip().upper() or "UNKNOWN"
        doc_type = str(row.get("source_document_type") or "unknown").strip().lower() or "unknown"
        parse_status = str(row.get("parse_status") or "").strip().lower()
        key = (amc_code, doc_type)
        bucket = pipeline_map.setdefault(
            key,
            {
                "amc_code": amc_code,
                "document_type": doc_type,
                "total_documents": 0,
                "parsed_count": 0,
                "pending_count": 0,
                "failed_count": 0,
                "needs_review_count": 0,
                "last_downloaded_at": None,
                "last_parse_attempt_at": None,
                "last_success_at": None,
                "last_failure_at": None,
            },
        )
        bucket["total_documents"] += 1
        if parse_status == "parsed":
            bucket["parsed_count"] += 1
        if parse_status in pending_statuses:
            bucket["pending_count"] += 1
        if parse_status == "failed":
            bucket["failed_count"] += 1
        if parse_status == "needs_review":
            bucket["needs_review_count"] += 1

        downloaded_at = _to_utc_datetime(row.get("downloaded_at"))
        parsed_at = _to_utc_datetime(row.get("parsed_at"))
        updated_at = _to_utc_datetime(row.get("updated_at"))

        last_downloaded_at = _to_utc_datetime(bucket.get("last_downloaded_at"))
        if downloaded_at and (not last_downloaded_at or downloaded_at > last_downloaded_at):
            bucket["last_downloaded_at"] = downloaded_at.isoformat()

        parse_attempt = parsed_at or updated_at
        last_parse_attempt_at = _to_utc_datetime(bucket.get("last_parse_attempt_at"))
        if parse_attempt and (not last_parse_attempt_at or parse_attempt > last_parse_attempt_at):
            bucket["last_parse_attempt_at"] = parse_attempt.isoformat()

        if parse_status == "parsed" and parse_attempt:
            last_success_at = _to_utc_datetime(bucket.get("last_success_at"))
            if not last_success_at or parse_attempt > last_success_at:
                bucket["last_success_at"] = parse_attempt.isoformat()

        if parse_status == "failed" and parse_attempt:
            last_failure_at = _to_utc_datetime(bucket.get("last_failure_at"))
            if not last_failure_at or parse_attempt > last_failure_at:
                bucket["last_failure_at"] = parse_attempt.isoformat()

    mf_pipeline_rows = sorted(
        pipeline_map.values(),
        key=lambda row: (str(row.get("amc_code") or ""), str(row.get("document_type") or "")),
    )

    try:
        dq_rows = (
            supabase.table("data_quality_issues")
            .select("id,symbol,table_name,field_name,issue_type,issue_message,source,detected_at")
            .order("detected_at", desc=True)
            .limit(120)
            .execute()
            .data
            or []
        )
    except Exception:
        dq_rows = []

    dq_last_24h = 0
    dq_last_7d = 0
    dq_24h_window = now_utc - timedelta(hours=24)
    dq_7d_window = now_utc - timedelta(days=7)
    for row in dq_rows:
        detected_at = _to_utc_datetime(row.get("detected_at"))
        if detected_at and detected_at >= dq_24h_window:
            dq_last_24h += 1
        if detected_at and detected_at >= dq_7d_window:
            dq_last_7d += 1

    try:
        mf_failed_docs = int(
            (
                supabase.table("mf_raw_documents")
                .select("id", count="exact")
                .eq("parse_status", "failed")
                .execute()
                .count
            )
            or 0
        )
    except Exception:
        mf_failed_docs = 0

    try:
        mf_review_queue = int(
            (
                supabase.table("mf_parse_review_queue")
                .select("id", count="exact")
                .eq("status", "pending_review")
                .execute()
                .count
            )
            or 0
        )
    except Exception:
        mf_review_queue = 0

    return {
        "status": "ok",
        "checked_at": now_utc.isoformat(),
        "workflow_source_table": workflow_source_table,
        "workflow_runs": workflow_runs,
        "workflow_summary": {
            "recent_run_count": len(workflow_runs),
            "status_counts": status_summary,
            "successes_24h": successes_24h,
            "failures_24h": failures_24h,
        },
        "mf_pipeline": mf_pipeline_rows,
        "data_quality": {
            "recent_issues": dq_rows,
            "issue_count_24h": dq_last_24h,
            "issue_count_7d": dq_last_7d,
            "mf_failed_documents": mf_failed_docs,
            "mf_pending_review": mf_review_queue,
        },
    }


@app.post("/api/admin/mf-documents/{document_id}/request-reparse")
def admin_request_mf_document_reparse(
    document_id: str,
    payload: AdminDocumentReviewAction | None = None,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    return _request_mf_document_reparse(document_id, _review_action_notes(payload))


@app.post("/api/admin/mf-documents/{document_id}/resolve")
def admin_resolve_mf_document_review(
    document_id: str,
    payload: AdminDocumentReviewAction | None = None,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    return _resolve_mf_document_review(document_id, _review_action_notes(payload))


@app.post("/api/admin/mf-documents/{document_id}/skip")
def admin_skip_mf_document_review(
    document_id: str,
    payload: AdminDocumentReviewAction | None = None,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    return _skip_mf_document_review(document_id, _review_action_notes(payload))


@app.get("/api/admin/mf-resolver-debug")
def admin_mf_resolver_debug(
    query: str = Query(..., min_length=2),
    horizon: str = Query("3Y", pattern="^(1Y|3Y|5Y)$"),
    limit: int = Query(20, ge=5, le=50),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    if not supabase:
        raise HTTPException(status_code=503, detail="supabase_unavailable")

    query_text = str(query or "").strip()
    normalized_query = _normalize_fund_text(query_text)
    if not normalized_query:
        return {
            "input_query": query_text,
            "normalized_query": normalized_query,
            "selected_candidate": None,
            "top_candidates": [],
            "scoring_breakdown": {
                "horizon": horizon,
                "min_history_points": _resolver_horizon_to_min_points(horizon),
            },
        }

    words = [word for word in normalized_query.split() if word]
    search_pattern = f"%{'%'.join(words)}%"

    rows = (
        supabase.table("mutual_fund_core_snapshot")
        .select("scheme_code,scheme_name,amc_name,category,sub_category,plan_type,option_type")
        .ilike("scheme_name", search_pattern)
        .limit(150)
        .execute()
        .data
        or []
    )

    min_history_points = _resolver_horizon_to_min_points(horizon)
    nav_history_cache: dict[str, dict[str, Any]] = {}
    scored = _score_fund_candidates(
        query_text,
        rows,
        nav_history_cache=nav_history_cache,
        min_history_points=min_history_points,
    )

    top_candidates: list[dict[str, Any]] = []
    for index, item in enumerate(scored[:limit]):
        row = item.get("row") or {}
        history_summary = item.get("history_summary") or {}
        top_candidates.append(
            {
                "rank": index + 1,
                "selected": index == 0,
                "scheme_code": str(row.get("scheme_code") or ""),
                "scheme_name": row.get("scheme_name"),
                "amc_name": row.get("amc_name"),
                "category": row.get("category"),
                "sub_category": row.get("sub_category"),
                "plan_type": row.get("plan_type"),
                "option_type": row.get("option_type"),
                "match_score": int(item.get("score") or 0),
                "nav_history_points": int(item.get("history_points") or 0),
                "first_nav_date": history_summary.get("first_nav_date"),
                "last_nav_date": history_summary.get("last_nav_date"),
                "supports": _supports_from_history_summary(history_summary),
                "penalty_notes": item.get("notes") or [],
            }
        )

    selected_candidate = top_candidates[0] if top_candidates else None
    if selected_candidate:
        selected_candidate = {
            **selected_candidate,
            "resolver_confidence": {
                "label": "high" if len(top_candidates) == 1 else ("high" if selected_candidate["match_score"] - top_candidates[1]["match_score"] >= 40 else "medium"),
                "score_gap_vs_next": 0 if len(top_candidates) == 1 else selected_candidate["match_score"] - top_candidates[1]["match_score"],
            },
            "resolver_notes": selected_candidate.get("penalty_notes", []),
        }

    return {
        "input_query": query_text,
        "normalized_query": normalized_query,
        "selected_candidate": selected_candidate,
        "top_candidates": top_candidates,
        "scoring_breakdown": {
            "horizon": horizon,
            "min_history_points": min_history_points,
            "candidate_count": len(scored),
        },
    }


@app.get("/api/v1/providers/usage")
def provider_usage_dashboard():
    enabled = os.getenv("ENABLE_PROVIDER_USAGE_ENDPOINT", "false").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        raise HTTPException(status_code=404, detail="Provider usage endpoint is disabled.")

    dashboard = build_usage_dashboard("indianapi")
    quota = evaluate_indianapi_quota(scheduled=True)
    return {
        "provider": "indianapi",
        "current_month_indianapi_usage": dashboard.get("month_request_cost"),
        "remaining_safe_indianapi_budget": quota.remaining_safe,
        "reserve_amount": quota.monthly_reserve,
        "daily_usage": dashboard.get("daily_request_cost"),
        "usage_by_endpoint": dashboard.get("usage_by_endpoint"),
        "cache_hit_ratio": dashboard.get("cache_hit_ratio"),
        "recent_provider_failures": dashboard.get("recent_failures"),
        "scheduled_sync_allowed": quota.allowed if quota.scheduled_sync_enabled else False,
        "scheduled_sync_reason": quota.reason,
        "month_window": dashboard.get("month_window"),
    }

class ChatHistoryMessage(BaseModel):
    role: Literal["user", "system"]
    content: str

class LastCompareContext(BaseModel):
    asset_type: Literal["stock", "mutual_fund"] = "mutual_fund"
    entities: list[str] = Field(default_factory=list)
    ids: list[str] = Field(default_factory=list)
    query: str | None = None
    last_focus: str | None = None
    available_topics: list[str] = Field(default_factory=list)

class LastPortfolioContext(BaseModel):
    query: str | None = None
    score: int | None = None
    label: str | None = None
    holdings: list[dict[str, Any]] = Field(default_factory=list)
    buckets: dict[str, float] = Field(default_factory=dict)
    overlap: dict[str, Any] = Field(default_factory=dict)
    insights: dict[str, Any] = Field(default_factory=dict)
    available_topics: list[str] = Field(default_factory=list)

class ConversationContext(BaseModel):
    last_compare: LastCompareContext | None = None
    last_portfolio: LastPortfolioContext | None = None


class ChatRequest(BaseModel):
    query: str
    asset_type: Literal["auto", "stock", "mutual_fund"] = "auto"
    research_depth: Literal["standard", "deep"] = "standard"
    explanation_mode: Literal["beginner", "advanced"] | None = None
    comparison_view_mode: Literal["canvas", "chat"] = "canvas"
    history: list[ChatHistoryMessage] = Field(default_factory=list)
    conversation_context: ConversationContext | None = None

class CategoryCompareRequest(BaseModel):
    category: str
    scheme_codes: list[str] = Field(default_factory=list)

CATEGORY_SEARCH_CONFIG = {
    "large_cap": {"label": "Large Cap", "match": "large cap", "scheme_match": "large cap"},
    "mid_cap": {"label": "Mid Cap", "match": "mid cap", "scheme_match": "mid cap"},
    "small_cap": {"label": "Small Cap", "match": "small cap", "scheme_match": "small cap"},
    "flexi_cap": {"label": "Flexi Cap", "match": "flexi cap", "scheme_match": "flexi cap"},
    "index": {"label": "Index", "match": "index", "scheme_match": "index"},
    "elss": {"label": "ELSS", "match": "elss", "scheme_match": "elss"},
}

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "OPENROUTER_API_KEY_PLACEHOLDER")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "nvidia/nemotron-3-ultra-550b-a55b:free")
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "http://localhost:3000")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "FundersAI")
CHAT_INTERNAL_PROXY_KEY = os.getenv("CHAT_INTERNAL_PROXY_KEY", "").strip()
CONTROLLED_WEB_CONTEXT_ENABLED = os.getenv("CONTROLLED_WEB_CONTEXT_ENABLED", "true").strip().lower() in {"1", "true", "yes", "on"}
APPROVED_WEB_SOURCE_NAMES = (
    "amfi",
    "sebi",
    "valueresearch",
    "value research",
    "moneycontrol",
    "mint",
    "economic times",
    "business standard",
    "morningstar",
    "personalfn",
    "upstox",
    "et mutual funds",
)
IST = pytz.timezone('Asia/Kolkata')
QUANT_CACHE: Dict[str, Any] = {}
QUANT_CACHE_TTL_SECONDS = int(os.getenv("QUANT_CACHE_TTL_SECONDS", "600"))
INDIANAPI_CHAT_STOCK_ENABLED = os.getenv("INDIANAPI_CHAT_STOCK_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
if "INDIANAPI_CHAT_STOCK_ENABLED" not in os.environ:
    INDIANAPI_CHAT_STOCK_ENABLED = os.getenv("INDIANAPI_ENABLE_LIVE_CALLS", "0").strip().lower() in {"1", "true", "yes", "on"}
DEBUG_MF_RESOLUTION = os.getenv("DEBUG_MF_RESOLUTION", "0").strip().lower() in {"1", "true", "yes", "on"}
MF_COMPARE_MIN_NAV_POINTS = max(int(os.getenv("MF_COMPARE_MIN_NAV_POINTS", "252")), 1)

def _trusted_chat_proxy(x_internal_proxy_key: str | None) -> bool:
    return bool(
        CHAT_INTERNAL_PROXY_KEY
        and x_internal_proxy_key
        and hmac.compare_digest(x_internal_proxy_key, CHAT_INTERNAL_PROXY_KEY)
    )


def _append_openrouter_usage(usage_collector: list[dict[str, Any]] | None, data: dict[str, Any]) -> None:
    if usage_collector is None:
        return
    usage = data.get("usage") if isinstance(data, dict) else None
    if not isinstance(usage, dict):
        return
    usage_collector.append(
        {
            "provider": "openrouter",
            "model": data.get("model") or OPENROUTER_MODEL,
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        }
    )


def _summarize_openrouter_usage(usage_collector: list[dict[str, Any]] | None) -> dict[str, Any]:
    rows = usage_collector or []
    return {
        "provider": "openrouter",
        "model": rows[-1].get("model") if rows else OPENROUTER_MODEL,
        "prompt_tokens": sum(int(row.get("prompt_tokens") or 0) for row in rows),
        "completion_tokens": sum(int(row.get("completion_tokens") or 0) for row in rows),
        "total_tokens": sum(int(row.get("total_tokens") or 0) for row in rows),
        "calls": len(rows),
    }


async def function_ollama_chat(messages, format="json", max_retries=2, usage_collector: list[dict[str, Any]] | None = None):
    openrouter_key = os.environ.get("OPENROUTER_API_KEY") or OPENROUTER_API_KEY
    if not openrouter_key or openrouter_key == "OPENROUTER_API_KEY_PLACEHOLDER":
        logger.error("Missing OPENROUTER_API_KEY in environment.")
        return None
        
    req_messages = [dict(m) for m in messages]
    payload = {
        "model": OPENROUTER_MODEL,
    }
    
    if format == "json":
        payload["response_format"] = {"type": "json_object"}
        if "json" not in req_messages[0]["content"].lower():
            req_messages[0]["content"] += "\nReturn output strictly in JSON format."
            
    payload["messages"] = req_messages
            
    headers = {
        "Authorization": f"Bearer {openrouter_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": OPENROUTER_SITE_URL,
        "X-Title": OPENROUTER_APP_NAME,
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(OPENROUTER_BASE_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            _append_openrouter_usage(usage_collector, data)
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenRouter API Error: {e}")
            return None

async def route_query(query: str, asset_type: str = "auto", usage_collector: list[dict[str, Any]] | None = None) -> dict:
    """Agent 1: Router"""
    def _has_downside_focus(text: str) -> bool:
        q = str(text or "").lower()
        triggers = [
            "market falls",
            "when market falls",
            "falling market",
            "bear market",
            "downside",
            "drawdown",
            "capital protection",
            "market crash",
            "during correction",
        ]
        return any(token in q for token in triggers)

    asset_instruction = ""
    if asset_type == "mutual_fund":
        asset_instruction = """
The user explicitly selected Mutual Funds mode. Treat ambiguous names as mutual fund scheme names, not stocks.
Preserve category words from the user query like Small Cap, Flexi Cap, Mid Cap, Large Cap, Index, Direct, Growth in compare_entities.
Do not classify mutual fund requests as stock screening requests.
"""
    elif asset_type == "stock":
        asset_instruction = """
The user explicitly selected Stocks mode. Treat ambiguous names as stocks or indices, not mutual fund schemes.
Do not classify stock requests as mutual fund requests.
"""

    system_prompt = """You are the Router Agent for FundersAI. Classify the user query intent.
If the query asks to filter, list, or screen stocks (e.g., "Find stocks with PE < 20", "Show me oversold stocks", "Mid cap stocks with RSI < 30"), set intent to 'screen' and populate 'screen_filters'.
If the query asks to compare two or more mutual funds or stocks, set intent to 'compare' and populate 'compare_entities' with a list of their names (e.g. ["HDFC Flexi Cap", "Parag Parikh Flexi Cap"]).
Otherwise, use 'quant', 'news', 'both', or 'general'.
Extract primary NSE/BSE ticker explicitly (e.g. RELIANCE.NS, ^NSEI for Nifty). 

Check for historical period mentions (e.g., '1m', '1y') and sentiment mentions.

Output strict JSON only format:
{
  "intent": "quant|news|both|general|screen|compare",
  "ticker": "TICKER.NS",
  "historical_period": "1mo|1y|5y|max", 
  "sentiment_flag": true/false,
  "downside_focus": true/false,
  "screen_filters": {
    "min_pe": 0,
    "max_pe": 100,
    "rsi_range": {"min": 0, "max": 100},
    "category": "Large Cap|Mid Cap|Small Cap"
  },
  "compare_entities": ["Asset 1 Name", "Asset 2 Name"]
}
If a filter is not mentioned, exclude it from screen_filters. Default historical_period to "1mo" if not mentioned. Default sentiment_flag to false unless news sentiment is requested.
Default downside_focus to false unless user explicitly asks downside/fall/crash/bear behavior.
    """ + asset_instruction
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]
    
    result = await function_ollama_chat(messages, format="json", usage_collector=usage_collector)
    if result:
        try:
            payload = json.loads(result)
            if not isinstance(payload, dict):
                payload = {"intent": "general", "ticker": None}
            payload["downside_focus"] = bool(payload.get("downside_focus")) or _has_downside_focus(query)
            return payload
        except Exception as e:
            logger.error(f"Router parsing error: {e}")
    return {"intent": "general", "ticker": None, "downside_focus": _has_downside_focus(query)}

def calculate_beta(stock_returns, nifty_returns):
    if len(stock_returns) < 10 or len(stock_returns) != len(nifty_returns):
        return 1.0
    try:
        # Use simple linear regression for beta (Slope of Stock Returns vs Market Returns)
        # Handle cases with constant returns or zero variance
        if np.var(nifty_returns) < 1e-9:
            return 1.0
        
        cov_matrix = np.cov(stock_returns, nifty_returns)
        if cov_matrix.shape == (2, 2):
            cov = cov_matrix[0][1]
            var = np.var(nifty_returns)
            beta = cov / var
            # Sanity check: Beta for a Flexi Cap equity fund should not be near zero
            # If it is, it might indicate bad data alignment
            if abs(beta) < 0.05:
                return 1.0
            return round(float(beta), 2)
        return 1.0
    except:
        return 1.0

def calculate_alpha_beta_v2(stock_hist, nifty_hist):
    if stock_hist.empty or nifty_hist.empty or len(stock_hist) < 20 or len(nifty_hist) < 20:
        return {"alpha": "N/A", "beta": "N/A"}

    stock_hist = _normalize_price_df_index(stock_hist)
    nifty_hist = _normalize_price_df_index(nifty_hist)
    
    # Pre-process: ensure we have numeric data and no NaNs in Close
    s_close = stock_hist['Close'].ffill().dropna()
    n_close = nifty_hist['Close'].ffill().dropna()
    
    stock_returns = s_close.pct_change().dropna()
    nifty_returns = n_close.pct_change().dropna()
    
    # Align returns on the same dates
    aligned = stock_returns.to_frame('stock').join(nifty_returns.to_frame('nifty'), how='inner')
    
    if len(aligned) < 10: return {"alpha": "N/A", "beta": "N/A"}
    
    beta = calculate_beta(aligned['stock'].tolist(), aligned['nifty'].tolist())
    
    # Annualized Returns for Alpha
    # Using the first and last valid prices to get total return
    stock_ret_total = (s_close.iloc[-1] - s_close.iloc[0]) / s_close.iloc[0]
    nifty_ret_total = (n_close.iloc[-1] - n_close.iloc[0]) / n_close.iloc[0]
    
    days = (s_close.index[-1] - s_close.index[0]).days
    if days <= 0: return {"alpha": "N/A", "beta": beta}
    
    # Annualize the returns
    years = days / 365.25
    stock_ann_ret = (1 + stock_ret_total) ** (1 / years) - 1
    nifty_ann_ret = (1 + nifty_ret_total) ** (1 / years) - 1
    
    # Risk-free rate (approx 6.5% for India)
    rf = 0.065
    
    # Alpha = R_p - [R_f + Beta * (R_m - R_f)]
    alpha = (stock_ann_ret - (rf + beta * (nifty_ann_ret - rf))) * 100
    
    return {"alpha": float(round(alpha, 2)), "beta": float(beta) if beta != "N/A" else "N/A", "period_years": float(round(years, 1))}

def _normalize_price_df_index(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    normalized = df.copy()
    normalized.index = pd.to_datetime(normalized.index, errors="coerce")
    normalized = normalized[normalized.index.notna()]
    if getattr(normalized.index, "tz", None) is not None:
        normalized.index = normalized.index.tz_convert(None)
    normalized.index = normalized.index.normalize()
    return normalized.sort_index()

def is_market_open() -> bool:
    now = datetime.now(IST)
    if now.weekday() >= 5:
        return False
    market_open = now.replace(hour=9, minute=15, second=0, microsecond=0)
    market_close = now.replace(hour=15, minute=30, second=0, microsecond=0)
    return market_open <= now <= market_close

def fetch_source_neutral_fundamentals(symbol: str) -> dict | None:
    if not symbol:
        return None
    clean_symbol = symbol.replace(".NS", "").replace(".BO", "").upper()
    try:
        from app.repositories.stock_repository import StockRepository
        from dataclasses import asdict
        repo = StockRepository()
        comp = repo.compare_stocks([clean_symbol])
        data = comp.get(clean_symbol)
        if not data or not data.get("profile"):
            return None
            
        profile = asdict(data["profile"]) if data["profile"] else {}
        ratios = asdict(data["ratios"]) if data["ratios"] else {}
        
        # Model must not be asked to invent missing financial values
        # Explicit nulls are passed where data is missing
        fundamentals = {
            "industry": profile.get("industry", None),
            "pe": ratios.get("pe", None),
            "pb": ratios.get("pb", None),
            "ev_ebitda": ratios.get("ev_ebitda", None),
            "roe": ratios.get("roe", None),
            "roce": ratios.get("roce", None),
            "debt_to_equity": ratios.get("debt_to_equity", None),
            "market_cap": ratios.get("market_cap", None),
            "dividend_yield": ratios.get("dividend_yield", None)
        }
        return fundamentals
    except Exception as e:
        logger.warning("Stock fundamentals lookup failed for %s: %s", clean_symbol, e)
        return None

def enrich_with_source_neutral_fundamentals(data: dict, symbol: str) -> dict:
    fundamentals = fetch_source_neutral_fundamentals(symbol)
    if not fundamentals:
        return data
    enriched = dict(data)
    enriched["fundamentals"] = fundamentals
    if enriched.get("pe_ratio") in [None, "N/A"]:
        enriched["pe_ratio"] = fundamentals.get("pe", "N/A")
    if enriched.get("market_cap") in [None, "N/A"]:
        enriched["market_cap"] = fundamentals.get("market_cap", "N/A")
    return enriched

async def resolve_mf_ticker(entity_name: str) -> str:
    """Helper to map a name to a yfinance-compatible ticker or ISIN."""
    fallback_map = {
        "hdfc flexi cap": "0P0000XW94.BO",
        "parag parikh flexi cap": "0P0000YWL2.BO",
        "quant small cap": "0P0000XW86.BO",
        "nippon india small cap": "0P0000XVUA.BO"
    }
    ent_lower = entity_name.lower()
    for key, ticker in fallback_map.items():
        if key in ent_lower:
            return ticker
    return None

def fetch_quant_data(ticker: str, period: str = "1mo") -> dict:
    """Agent 2: Quant Data"""
    if not ticker: return {"error": "No ticker identified"}
    
    clean_ticker = ticker.replace('.NS', '').replace('.BO', '').replace('^NSEI', 'NIFTY')

    cache_key = f"{clean_ticker}:{period}"
    cached_entry = QUANT_CACHE.get(cache_key)
    now_ts = time.time()
    if cached_entry and (now_ts - cached_entry["ts"]) < QUANT_CACHE_TTL_SECONDS:
        return cached_entry["data"]

    def cache_and_return(data: dict) -> dict:
        QUANT_CACHE[cache_key] = {"ts": time.time(), "data": data}
        return data

    def get_local_quant_snapshot(symbol: str) -> dict | None:
        if not supabase:
            return None
        try:
            snapshot_row = None
            snapshot_res = supabase.table('nifty_stocks').select('*').eq('symbol', symbol).limit(1).execute()
            if snapshot_res.data:
                snapshot_row = snapshot_res.data[0]

            history_res = supabase.table('stock_prices_daily').select('close, date').eq('symbol', symbol).order('date', desc=True).limit(2).execute()
            history_rows = history_res.data or []

            if not snapshot_row and not history_rows:
                return None

            latest_close = history_rows[0]["close"] if history_rows else None
            prev_close = history_rows[1]["close"] if len(history_rows) > 1 else None
            price = snapshot_row.get("current_price") if snapshot_row else latest_close
            if price in [None, "N/A"]:
                price = latest_close

            change_pct = snapshot_row.get("change_pct") if snapshot_row else None
            if (change_pct in [None, "N/A"]) and latest_close is not None and prev_close not in [None, 0]:
                change_pct = round(((latest_close - prev_close) / prev_close) * 100, 2)

            data = {
                "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST") + " (Supabase Local Snapshot)",
                "price": round(float(price), 2) if price not in [None, "N/A"] else "N/A",
                "change_pct": change_pct if change_pct not in [None, "N/A"] else "N/A",
                "pe_ratio": snapshot_row.get("pe_ratio", "N/A") if snapshot_row else "N/A",
                "market_cap": snapshot_row.get("market_cap", "N/A") if snapshot_row else "N/A",
                "beta": snapshot_row.get("beta", "N/A") if snapshot_row else "N/A",
                "alpha_vs_nifty": snapshot_row.get("alpha_vs_nifty", "N/A") if snapshot_row else "N/A",
                "historical_period": "1d (EOD local)",
                "rsi_14d": snapshot_row.get("rsi", "N/A") if snapshot_row else "N/A",
                "tv_recommendation": snapshot_row.get("recommendation", "N/A") if snapshot_row else "N/A"
            }

            if symbol == "NIFTY":
                data["beta"] = 1.0
                data["alpha_vs_nifty"] = 0.0

            return enrich_with_source_neutral_fundamentals(data, symbol)
        except Exception as e:
            logger.warning(f"Supabase local snapshot error for {symbol}: {e}")
            return None

    def get_indianapi_quant_snapshot(symbol: str) -> dict | None:
        if not INDIANAPI_CHAT_STOCK_ENABLED:
            return None
        if not symbol or symbol == "NIFTY":
            return None
        try:
            item = _stock_compare_item(symbol)
            if not isinstance(item, dict) or item.get("error"):
                return None

            source_summary = item.get("source_summary") or {}
            fundamentals = item.get("fundamentals") or {}
            local_data = get_local_quant_snapshot(symbol) or {}

            def _pick(primary: Any, fallback: Any) -> Any:
                return fallback if _is_missing(primary) and not _is_missing(fallback) else primary

            data = {
                "timestamp": item.get("timestamp") or datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
                "price": item.get("price"),
                "change_pct": item.get("change_pct"),
                "pe_ratio": _pick(item.get("pe_ratio"), local_data.get("pe_ratio")),
                "market_cap": _pick(item.get("market_cap"), local_data.get("market_cap")),
                "beta": _pick(item.get("beta"), local_data.get("beta")),
                "alpha_vs_nifty": _pick(item.get("alpha_vs_nifty"), local_data.get("alpha_vs_nifty")),
                "historical_period": item.get("historical_period") or local_data.get("historical_period") or "1y",
                "rsi_14d": _pick(item.get("rsi_14d"), local_data.get("rsi_14d")),
                "tv_recommendation": _pick(item.get("tv_recommendation"), local_data.get("tv_recommendation")),
                "fundamentals": fundamentals,
                "source_summary": source_summary,
                "source": (
                    "indianapi"
                    if source_summary.get("indianapi_fetched_at")
                    else source_summary.get("metadata")
                ),
                "fetchedAt": source_summary.get("indianapi_fetched_at"),
            }
            return data
        except Exception as e:
            logger.warning(f"IndianAPI-backed snapshot failed for {symbol}: {e}")
            return None

    def get_live_nifty_snapshot() -> dict | None:
        try:
            nifty = yf.Ticker("^NSEI")
            intraday = nifty.history(period="1d", interval="1m")
            if intraday.empty:
                return None

            last_price = float(intraday["Close"].dropna().iloc[-1])
            local_data = get_local_quant_snapshot("NIFTY") or {}
            prev_close = local_data.get("price")
            change_pct = local_data.get("change_pct", "N/A")

            if prev_close not in [None, "N/A", 0]:
                change_pct = round(((last_price - float(prev_close)) / float(prev_close)) * 100, 2)

            return {
                "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST") + " (Live NIFTY)",
                "price": round(last_price, 2),
                "change_pct": change_pct,
                "pe_ratio": "N/A",
                "market_cap": "N/A",
                "beta": 1.0,
                "alpha_vs_nifty": 0.0,
                "historical_period": "1d (live)",
                "rsi_14d": "N/A",
                "tv_recommendation": "N/A"
            }
        except Exception as e:
            logger.warning(f"Live NIFTY snapshot failed: {e}")
            return None

    if is_market_open():
        if clean_ticker == "NIFTY":
            local_nifty = get_local_quant_snapshot("NIFTY")
            if local_nifty:
                return cache_and_return(local_nifty)
            live_nifty = get_live_nifty_snapshot()
            if live_nifty:
                return cache_and_return(live_nifty)
        else:
            indianapi_data = get_indianapi_quant_snapshot(clean_ticker)
            if indianapi_data:
                return cache_and_return(indianapi_data)
            live_quote = fetch_live_quote(clean_ticker)
            if live_quote:
                local_data = get_local_quant_snapshot(clean_ticker) or {}
                live_data = {
                    "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST") + f" ({live_quote.get('source', 'Live Quote')})",
                    "price": round(float(live_quote["last_price"]), 2),
                    "change_pct": round(float(live_quote["pchange"]), 2) if live_quote.get("pchange") is not None else "N/A",
                    "pe_ratio": local_data.get("pe_ratio", "N/A"),
                    "market_cap": local_data.get("market_cap", "N/A"),
                    "beta": local_data.get("beta", "N/A"),
                    "alpha_vs_nifty": local_data.get("alpha_vs_nifty", "N/A"),
                    "historical_period": "1d (live)",
                    "rsi_14d": local_data.get("rsi_14d", "N/A"),
                    "tv_recommendation": local_data.get("tv_recommendation", "N/A")
                }
                return cache_and_return(enrich_with_source_neutral_fundamentals(live_data, clean_ticker))

    # Prefer local data for NIFTY off-market, and for off-market short-window queries.
    if clean_ticker == "NIFTY" or (period in ["1d", "1mo"] and not is_market_open()):
        local_data = get_local_quant_snapshot(clean_ticker)
        if local_data:
            return cache_and_return(local_data)
    elif not is_market_open():
        indianapi_data = get_indianapi_quant_snapshot(clean_ticker)
        if indianapi_data:
            return cache_and_return(indianapi_data)

    try:
        if period not in ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y", "10y", "ytd", "max"]:
            period = "1y"
            
        stock = yf.Ticker(ticker)
        nifty = yf.Ticker("^NSEI")
        try:
            info = stock.info
        except Exception as e:
            logger.warning(f"YFinance info lookup failed for {ticker}: {e}")
            info = {}
        
        hist = stock.history(period=period)
        # Use 3y for stable risk metrics calculation
        calc_period = "3y"
        hist_calc = stock.history(period=calc_period)
        nifty_hist = nifty.history(period=calc_period)
        
        if hist.empty:
            local_data = get_local_quant_snapshot(clean_ticker)
            if local_data:
                return cache_and_return(local_data)
            return {"error": "No recent data found"}
            
        current_price = info.get('currentPrice', hist['Close'].iloc[-1])
        prev_close = info.get('previousClose', hist['Close'].iloc[-2] if len(hist) > 1 else current_price)
        change_pct = ((current_price - prev_close) / prev_close) * 100
        
        risk_metrics = calculate_alpha_beta_v2(hist_calc, nifty_hist)
        
        data = {
            "timestamp": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
            "price": round(current_price, 2),
            "change_pct": round(change_pct, 2),
            "pe_ratio": info.get("trailingPE", "N/A"),
            "market_cap": info.get("marketCap", "N/A"),
            "beta": risk_metrics["beta"],
            "alpha_vs_nifty": risk_metrics["alpha"],
            "risk_period": f"{risk_metrics.get('period_years', 3)}Y",
            "historical_period": period,
            "rsi_14d": "N/A",
            "tv_recommendation": "N/A",
            "aum": info.get("totalAssets", "N/A")
        }
        return cache_and_return(enrich_with_source_neutral_fundamentals(data, clean_ticker))
    except Exception as e:
        logger.error(f"Quant Error: {e}")
        indianapi_data = get_indianapi_quant_snapshot(clean_ticker)
        if indianapi_data:
            return cache_and_return(indianapi_data)
        local_data = get_local_quant_snapshot(clean_ticker)
        if local_data:
            return cache_and_return(local_data)
        return {"error": str(e)}

async def analyze_news_sentiment(news_items: list, usage_collector: list[dict[str, Any]] | None = None) -> list:
    """Agent: Sentiment Analyzer"""
    if not news_items: return []
    
    system_prompt = """You are a financial sentiment analyzer. Given a list of news headlines, assign a sentiment of POSITIVE, NEGATIVE, or NEUTRAL to each. 
Return exactly in this JSON format:
{"evaluations": [{"title": "Headline", "sentiment": "POSITIVE"}]}"""
    
    titles = "\\n".join([n['title'] for n in news_items])
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": titles}
    ]
    
    result = await function_ollama_chat(messages, format="json", usage_collector=usage_collector)
    if result:
        try:
            evals = json.loads(result).get("evaluations", [])
            sentiment_map = {e["title"]: e["sentiment"] for e in evals}
            for n in news_items:
                n["sentiment"] = sentiment_map.get(n["title"], "NEUTRAL")
            return news_items
        except Exception as e:
            logger.error(f"Sentiment parsing error: {e}")
    
    for n in news_items: n["sentiment"] = "NEUTRAL"
    return news_items

def _is_approved_web_source(source: Any, url: Any = None) -> bool:
    source_text = str(source or "").lower()
    url_text = str(url or "").lower()
    return any(name in source_text or name in url_text for name in APPROVED_WEB_SOURCE_NAMES)

def fetch_news(query: str, ticker: str, sentiment_flag: bool = False) -> list:
    """Controlled web context: approved source headlines only."""
    if not CONTROLLED_WEB_CONTEXT_ENABLED:
        return []
    search_term = ticker.replace('.NS', '').replace('.BO', '') if ticker else query
    encoded_term = search_term.replace(' ', '+')
    rss_url = f"https://news.google.com/rss/search?q={encoded_term}+India+mutual+fund+stock+market&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        feed = feedparser.parse(rss_url)
        news_items = []
        for entry in feed.entries[:12]:
            source = entry.source.title if hasattr(entry, 'source') else "News Source"
            url = getattr(entry, "link", None)
            if not _is_approved_web_source(source, url):
                continue
            news_items.append({
                "title": entry.title,
                "source": source,
                "published": entry.published,
                "url": url,
                "context_type": "controlled_web_headline",
            })
            if len(news_items) >= 6:
                break
        return news_items
    except Exception as e:
        logger.error(f"News Error: {e}")
        return []

DISCLAIMER = "> ⚠️ **Disclaimer:** *FundersAI is an informational research tool only. Nothing presented here constitutes investment advice, a solicitation, or a recommendation to buy or sell any security. Always conduct your own research and consult a SEBI-registered Investment Advisor before making any financial decision.*"
DATA_UNAVAILABLE = "Data Unavailable"

ADVICE_REPLACEMENTS = {
    "attractive option for long-term investment": "candidate for further independent research",
    "attractive option": "candidate for further independent research",
    "investors should": "readers can",
    "investor should": "readers can",
    "buy or sell": "act on",
    "buy": "positive technical rating",
    "sell": "negative technical rating",
    "long-term investment": "longer-horizon research",
    "investment decision": "research decision",
    "invest": "research further",
}

def _is_missing(value: Any) -> bool:
    return value is None or value == "" or str(value).strip().upper() in {"N/A", "NA", "NONE", "NULL", "NAN"}

def _safe_value(value: Any) -> str:
    if _is_missing(value):
        return "N/A"
    if isinstance(value, float):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return str(value)

def _unwrap_nested_value(value: Any, preferred_keys: tuple[str, ...] = ()) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        for key in preferred_keys:
            if key in value:
                candidate = _unwrap_nested_value(value.get(key), preferred_keys)
                if not _is_missing(candidate):
                    return candidate
        for key in (
            "current",
            "value",
            "nav",
            "latest_nav",
            "date",
            "nav_date",
            "name",
            "scheme_name",
            "fund_house",
            "amc",
            "expense_ratio",
            "ratio",
            "aum",
            "asset_size",
        ):
            if key in value:
                candidate = _unwrap_nested_value(value.get(key), preferred_keys)
                if not _is_missing(candidate):
                    return candidate
        for nested in value.values():
            candidate = _unwrap_nested_value(nested, preferred_keys)
            if not _is_missing(candidate):
                return candidate
        return None
    if isinstance(value, list):
        for item in value:
            candidate = _unwrap_nested_value(item, preferred_keys)
            if not _is_missing(candidate):
                return candidate
        return None
    return value

def _format_percent(value: Any) -> str:
    if _is_missing(value):
        return "N/A"
    if isinstance(value, str) and value.strip().endswith("%"):
        return value
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return _safe_value(value)

def _format_ratio_percent(value: Any) -> str:
    if _is_missing(value):
        return "N/A"
    if isinstance(value, str) and value.strip().endswith("%"):
        return value
    try:
        amount = float(value)
        percent = amount * 100 if abs(amount) <= 1 else amount
        return f"{percent:.2f}%"
    except (TypeError, ValueError):
        return _safe_value(value)

def _format_price(value: Any) -> str:
    if _is_missing(value):
        return "N/A"
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return _safe_value(value)

def _format_inr_market_cap(value: Any) -> str:
    if _is_missing(value):
        return "N/A"
    try:
        amount = float(value)
    except (TypeError, ValueError):
        return _safe_value(value)

    if amount >= 1_00_00_00_00_000:
        return f"₹{amount / 1_00_00_00_00_000:.2f} lakh crore"
    if amount >= 1_00_00_000:
        return f"₹{amount / 1_00_00_000:.2f} crore"
    return f"₹{amount:,.0f}"

def _format_inr_amount(value: Any) -> str:
    if _is_missing(value):
        return "N/A"
    try:
        return f"INR {float(value):,.0f}"
    except (TypeError, ValueError):
        return _safe_value(value)

def _to_float_or_none(value: Any) -> float | None:
    if _is_missing(value):
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return None

def _money_token_to_float(value: str) -> float | None:
    raw = str(value or "").strip().lower().replace(",", "")
    match = re.match(r"^([0-9]+(?:\.[0-9]+)?)\s*(k|lakh|lac|cr|crore)?$", raw)
    if not match:
        return None
    amount = float(match.group(1))
    suffix = match.group(2)
    if suffix == "k":
        return amount * 1_000
    if suffix in {"lakh", "lac"}:
        return amount * 1_00_000
    if suffix in {"cr", "crore"}:
        return amount * 1_00_00_000
    return amount

def _parse_sip_inputs(query: str) -> dict[str, Any] | None:
    text = str(query or "").lower()
    if "sip" not in text and "systematic investment" not in text:
        return None

    amount = None
    amount_patterns = [
        r"(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?\s*(?:k|lakh|lac|cr|crore)?)\s*(?:per\s*month|/month|monthly|pm)",
        r"(?:sip|invest|investment|contribute)\D{0,25}(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?\s*(?:k|lakh|lac|cr|crore)?)",
    ]
    for pattern in amount_patterns:
        match = re.search(pattern, text)
        if match:
            amount = _money_token_to_float(match.group(1))
            if amount:
                break

    if amount is None:
        for match in re.finditer(r"([0-9][0-9,]*(?:\.[0-9]+)?\s*(?:k|lakh|lac|cr|crore)?)", text):
            end = match.end()
            nearby = text[end:end + 12]
            before = text[max(0, match.start() - 4):match.start()]
            if "%" in nearby or "percent" in nearby or "year" in nearby or "yr" in nearby or "%" in before:
                continue
            amount = _money_token_to_float(match.group(1))
            if amount:
                break

    years = None
    year_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:years?|yrs?)", text)
    if year_match:
        years = float(year_match.group(1))
    else:
        month_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:months?|mos?)", text)
        if month_match:
            years = float(month_match.group(1)) / 12

    rate = None
    rate_match = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*(?:%|percent)", text)
    if rate_match:
        rate = float(rate_match.group(1))
    else:
        at_rate_match = re.search(r"(?:at|return|returns|rate)\D{0,12}([0-9]+(?:\.[0-9]+)?)", text)
        if at_rate_match:
            candidate = float(at_rate_match.group(1))
            if candidate <= 100:
                rate = candidate

    if amount is None or years is None:
        return None

    return {
        "amount": amount,
        "years": years,
        "annual_rate": 12.0 if rate is None else rate,
        "rate_defaulted": rate is None,
    }

def _calculate_sip_projection(amount: float, years: float, annual_rate: float) -> dict[str, float]:
    months = int(round(years * 12))
    monthly_rate = (annual_rate / 100) / 12
    invested = amount * months
    if monthly_rate == 0:
        future_value = invested
    else:
        future_value = amount * ((((1 + monthly_rate) ** months - 1) / monthly_rate) * (1 + monthly_rate))
    return {
        "monthly_amount": amount,
        "years": years,
        "months": months,
        "annual_rate": annual_rate,
        "total_invested": invested,
        "estimated_value": future_value,
        "estimated_gain": future_value - invested,
    }

def _build_sip_calculator_response(query: str) -> dict[str, Any] | None:
    parsed = _parse_sip_inputs(query)
    if not parsed:
        return None

    projection = _calculate_sip_projection(
        parsed["amount"],
        parsed["years"],
        parsed["annual_rate"],
    )
    rows = [
        ["Monthly SIP", _format_inr_amount(projection["monthly_amount"])],
        ["Duration", f"{projection['months']} months ({projection['years']:.1f} years)"],
        ["Expected annual return", f"{projection['annual_rate']:.2f}%"],
        ["Total invested", _format_inr_amount(projection["total_invested"])],
        ["Estimated gain", _format_inr_amount(projection["estimated_gain"])],
        ["Estimated value", _format_inr_amount(projection["estimated_value"])],
    ]
    assumption = (
        "\n\nAssumption: expected annual return defaults to 12.00% because no rate was provided."
        if parsed["rate_defaulted"]
        else ""
    )
    answer = f"""### SIP Calculator
{_markdown_table(["Metric", "Value"], rows)}
{assumption}

This is a mathematical projection, not a guaranteed return or investment advice.

{DISCLAIMER}"""
    return {
        "answer": answer,
        "debug_intent": {"intent": "sip_calculator", **parsed},
        "quant_data": {"sip_projection": projection},
    }

def _risk_period(data: dict) -> str:
    period = str(data.get("risk_period") or data.get("historical_period") or "").strip()
    return period.split()[0].upper() if period else "period"

def _safe_recommendation(value: Any) -> str:
    if _is_missing(value):
        return "N/A"
    text = str(value).strip().lower()
    mapping = {
        "strong buy": "Strong positive technical rating",
        "buy": "Positive technical rating",
        "sell": "Negative technical rating",
        "strong sell": "Strong negative technical rating",
    }
    return mapping.get(text, str(value))

def _is_unavailable_entity(data: Any) -> bool:
    return not isinstance(data, dict) or bool(data.get("error"))

def _markdown_table(headers: list[str], rows: list[list[str]]) -> str:
    header = "| " + " | ".join(headers) + " |"
    divider = "| " + " | ".join(["---"] * len(headers)) + " |"
    body = ["| " + " | ".join(row) + " |" for row in rows]
    return "\n".join([header, divider, *body])

def _dashboard_category_key(query: str) -> str | None:
    text = " ".join(str(query or "").lower().replace("-", " ").split())
    if "fund" not in text and "elss" not in text:
        return None
    for key, config in CATEGORY_SEARCH_CONFIG.items():
        if config["match"] in text:
            return key
    if "nifty 50" in text and "index" in text:
        return "index"
    return None

def _dashboard_tool_intent(query: str, asset_type: str = "auto") -> dict[str, Any] | None:
    sip_inputs = _parse_sip_inputs(query)
    if sip_inputs:
        return {"intent": "sip_calculator", **sip_inputs}

    category_key = _dashboard_category_key(query)
    if category_key and asset_type != "stock":
        return {
            "intent": "category_search",
            "category_key": category_key,
            "category_label": CATEGORY_SEARCH_CONFIG[category_key]["label"],
        }
    return None

def _normalize_compare_entity_name(entity: str) -> str:
    text = " ".join(str(entity or "").replace("-", " ").replace(",", " ").split())
    text = re.sub(r"\b(?:and\s+)?(?:why|how|what|which|explain|show|tell)\b.*$", "", text, flags=re.IGNORECASE).strip()
    low = text.lower()
    if "parag" in low or "ppfas" in low:
        if "flexi" in low or "flexi cap" in low:
            return "Parag Parikh Flexi Cap"
    if "hdfc" in low and "flexi" in low:
        return "HDFC Flexi Cap"
    if "icici" in low and "multi" in low:
        return "ICICI Multi Asset"
    if "sbi" in low and "blue" in low:
        return "SBI Bluechip"
    if "flexi" in low and "cap" not in low:
        return f"{text} Cap"
    return text

def _extract_compare_followup_question(query: str) -> str | None:
    text = " ".join(str(query or "").strip().split())
    if not text:
        return None
    match = re.search(r"\b(?:and|,)\s+((?:why|how|what|which|explain|show|tell)\b.+)$", text, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip(" ?") + "?"
    if re.match(r"^(why|how|what|which|explain|show|tell)\b", text, flags=re.IGNORECASE):
        return text
    return None

def _deterministic_compare_intent(query: str, asset_type: str = "auto") -> dict[str, Any] | None:
    if asset_type == "stock":
        return None

    text = " ".join(str(query or "").strip().split())
    low = text.lower()
    if "compare" not in low:
        return None
    if not any(token in low for token in ("fund", "flexi", "cap", "ppfas", "parag", "hdfc", "icici", "sbi")):
        return None

    cleaned = re.sub(r"^compare\s+", "", text, flags=re.IGNORECASE)
    cleaned = re.sub(r"\b(for|over)\s+(the\s+)?(long\s*term|short\s*term|medium\s*term).*$", "", cleaned, flags=re.IGNORECASE).strip()
    parts = re.split(r"\s+(?:and|vs\.?|versus)\s+", cleaned, maxsplit=1, flags=re.IGNORECASE)
    if len(parts) < 2:
        return None

    entities = [_normalize_compare_entity_name(part) for part in parts[:2]]
    entities = [entity for entity in entities if entity]
    if len(entities) < 2:
        return None

    intent = {
        "intent": "compare",
        "ticker": None,
        "historical_period": "5y" if "long" in low else "1mo",
        "sentiment_flag": False,
        "downside_focus": any(token in low for token in ("downside", "drawdown", "fall", "crash")),
        "compare_entities": entities,
        "asset_type": "mutual_fund",
        "deterministic_router": True,
    }
    followup_question = _extract_compare_followup_question(query)
    if followup_question:
        intent["followup_question"] = followup_question
    return intent

def _is_compare_followup_query(query: str) -> bool:
    low = str(query or "").lower()
    if "compare" in low:
        return False
    has_reference = any(token in low for token in ("both", "these", "them", "those", "their", "the two"))
    has_metric = any(token in low for token in (
        "return", "returns", "differ", "difference", "risk", "expense", "aum",
        "drawdown", "volatility", "sharpe", "alpha", "beta", "nav", "performance",
        "safer", "steadier", "winner", "better", "portfolio", "holdings",
    ))
    asks_question = bool(re.match(r"^\s*(why|how|what|which|explain|show|tell)\b", low))
    return has_metric and (has_reference or asks_question)

def _detect_followup_topic(query: str) -> str | None:
    low = str(query or "").lower()
    if any(token in low for token in ("holding", "holdings", "overlap", "same stocks", "common stocks")):
        return "holdings"
    if any(token in low for token in ("sector", "allocation", "portfolio mix")):
        return "sectors"
    if any(token in low for token in ("risk", "safer", "drawdown", "volatility", "sharpe", "steadier")):
        return "risk"
    if any(token in low for token in ("expense", "cost", "aum", "size")):
        return "cost"
    if any(token in low for token in ("return", "returns", "performance", "differ", "difference")):
        return "returns"
    if any(token in low for token in ("fresh", "missing", "available", "data quality", "nav date")):
        return "data_quality"
    return None

def _last_compare_intent_from_history(history: list[Any], asset_type: str = "auto") -> dict[str, Any] | None:
    for message in reversed(_history_payload(history)):
        if message.get("role") != "user":
            continue
        intent = _deterministic_compare_intent(message.get("content", ""), asset_type)
        if intent and len(intent.get("compare_entities") or []) >= 2:
            return intent
    return None

def _last_compare_intent_from_context(context: Any) -> dict[str, Any] | None:
    last_compare = getattr(context, "last_compare", None) if context is not None else None
    if isinstance(context, dict):
        last_compare = context.get("last_compare")
    if not last_compare:
        return None

    if isinstance(last_compare, dict):
        entities = last_compare.get("entities") or []
        ids = last_compare.get("ids") or []
        context_asset_type = last_compare.get("asset_type") or "mutual_fund"
        source_query = last_compare.get("query")
        last_focus = last_compare.get("last_focus")
    else:
        entities = getattr(last_compare, "entities", []) or []
        ids = getattr(last_compare, "ids", []) or []
        context_asset_type = getattr(last_compare, "asset_type", "mutual_fund")
        source_query = getattr(last_compare, "query", None)
        last_focus = getattr(last_compare, "last_focus", None)

    clean_entities = [str(entity).strip() for entity in entities if str(entity or "").strip()]
    if len(clean_entities) < 2:
        return None

    return {
        "intent": "compare",
        "ticker": None,
        "historical_period": "1mo",
        "sentiment_flag": False,
        "downside_focus": False,
        "compare_entities": clean_entities[:2],
        "compare_ids": [str(item).strip() for item in ids if str(item or "").strip()][:2],
        "asset_type": context_asset_type,
        "source_query": source_query,
        "last_focus": last_focus,
        "context_router": True,
    }

def _followup_compare_intent(
    query: str,
    history: list[Any],
    asset_type: str = "auto",
    conversation_context: Any = None,
) -> dict[str, Any] | None:
    if not _is_compare_followup_query(query):
        return None
    previous = _last_compare_intent_from_context(conversation_context) or _last_compare_intent_from_history(history, asset_type)
    if not previous:
        return None
    if asset_type == "stock" and previous.get("asset_type") != "stock":
        return None
    intent = dict(previous)
    if "long" in str(query or "").lower():
        intent["historical_period"] = "5y"
    intent["followup_question"] = _extract_compare_followup_question(query) or str(query).strip()
    intent["followup_topic"] = _detect_followup_topic(query) or intent.get("last_focus")
    intent["followup_from_context"] = bool(previous.get("context_router"))
    intent["followup_from_history"] = not bool(previous.get("context_router"))
    return intent

RISK_QUIZ_QUESTIONS = [
    {
        "question": "1. If your portfolio fell 15% in a month, what would you most likely do?",
        "options": [
            ("A", "Reduce risk quickly"),
            ("B", "Wait and review calmly"),
            ("C", "Consider adding more after research"),
        ],
    },
    {
        "question": "2. When do you expect to use this money?",
        "options": [
            ("A", "Within 3 years"),
            ("B", "In 3-5 years"),
            ("C", "After 5 years"),
        ],
    },
    {
        "question": "3. What matters most to you?",
        "options": [
            ("A", "Capital stability"),
            ("B", "Balanced growth with controlled swings"),
            ("C", "Higher long-term growth even with sharper swings"),
        ],
    },
]

def _history_payload(history: list[Any]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []
    for item in history[-20:]:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")
        else:
            role = getattr(item, "role", None)
            content = getattr(item, "content", None)
        if role in {"user", "system"} and str(content or "").strip():
            messages.append({"role": str(role), "content": str(content).strip()})
    return messages

def _is_risk_quiz_start(query: str) -> bool:
    text = str(query or "").lower()
    return "risk profile" in text or "risk quiz" in text

def _is_portfolio_review_start(query: str) -> bool:
    text = str(query or "").lower()
    return "portfolio review" in text or "review my portfolio" in text or "portfolio health" in text

def _system_history_contains(history: list[dict[str, str]], text: str) -> bool:
    needle = text.lower()
    return any(message["role"] == "system" and needle in message["content"].lower() for message in history)

def _risk_quiz_started(history: list[dict[str, str]]) -> bool:
    # Only trap if the user explicitly started it, not just because the bot said "Risk Quiz"
    return any(message["role"] == "user" and _is_risk_quiz_start(message["content"]) for message in history)

def _risk_quiz_completed(history: list[dict[str, str]]) -> bool:
    return _system_history_contains(history, "risk profile result")

def _risk_answer_score(text: str, question_index: int) -> int | None:
    cleaned = str(text or "").strip().lower()
    match = re.search(r"\b([abc])\b", cleaned)
    if match:
        return {"a": 0, "b": 1, "c": 2}.get(match.group(1))
    if question_index == 0:
        if any(token in cleaned for token in ("reduce", "sell", "exit", "switch")):
            return 0
        if any(token in cleaned for token in ("wait", "hold", "review", "calm")):
            return 1
        if any(token in cleaned for token in ("add", "more", "accumulate")):
            return 2
    if question_index == 1:
        if any(token in cleaned for token in ("short", "within 3", "1 year", "2 year", "3 year")):
            return 0
        if any(token in cleaned for token in ("3-5", "3 to 5", "medium")):
            return 1
        if any(token in cleaned for token in ("long", "5 year", "after 5", "10 year")):
            return 2
    if question_index == 2:
        if any(token in cleaned for token in ("stability", "capital", "safe")):
            return 0
        if any(token in cleaned for token in ("balanced", "controlled")):
            return 1
        if any(token in cleaned for token in ("growth", "higher", "aggressive")):
            return 2
    return None

def _risk_quiz_answers(history: list[dict[str, str]], current_query: str) -> list[int]:
    sequence = [*history, {"role": "user", "content": current_query}]
    start_index = None
    for index, message in enumerate(sequence):
        if message["role"] == "user" and _is_risk_quiz_start(message["content"]):
            start_index = index
    if start_index is None:
        return []

    answers: list[int] = []
    for message in sequence[start_index + 1:]:
        if message["role"] != "user":
            continue
        score = _risk_answer_score(message["content"], len(answers))
        if score is not None:
            answers.append(score)
        else:
            # If the user responds with something completely unrelated, abort the quiz
            if len(message["content"]) > 15:
                return []
        if len(answers) == len(RISK_QUIZ_QUESTIONS):
            break
    return answers

def _risk_question_markdown(question_index: int) -> str:
    item = RISK_QUIZ_QUESTIONS[question_index]
    options = "\n".join([f"- {letter}. {label}" for letter, label in item["options"]])
    return f"""### Risk Quiz
{item["question"]}

{options}

Reply with A, B, or C."""

def _build_risk_quiz_response(query: str, history: list[dict[str, str]]) -> dict[str, Any] | None:
    if not _is_risk_quiz_start(query) and (not _risk_quiz_started(history) or _risk_quiz_completed(history)):
        return None

    answers = _risk_quiz_answers(history, query)
    if len(answers) < len(RISK_QUIZ_QUESTIONS):
        answer = _risk_question_markdown(len(answers))
        return {
            "answer": answer,
            "debug_intent": {"intent": "risk_quiz", "step": len(answers) + 1, "answers": answers},
            "quant_data": {"risk_quiz": {"step": len(answers) + 1, "answers": answers}},
        }

    score = sum(answers)
    if score <= 2:
        profile = "Conservative"
        fit = "lower volatility research buckets such as debt-oriented, conservative hybrid, and large-cap categories"
    elif score <= 4:
        profile = "Moderate"
        fit = "balanced research buckets such as large cap, flexi cap, balanced advantage, and index categories"
    else:
        profile = "Aggressive"
        fit = "higher volatility research buckets such as mid cap, small cap, flexi cap, and sector-review categories"

    answer = f"""### Risk Profile Result
| Metric | Result |
| --- | --- |
| Score | {score}/6 |
| Profile | {profile} |
| Research fit | {fit} |

Use this as a starting point for research only. It is not a suitability assessment or investment advice.

{DISCLAIMER}"""
    return {
        "answer": answer,
        "debug_intent": {"intent": "risk_quiz", "step": "complete", "score": score, "profile": profile},
        "quant_data": {"risk_quiz": {"score": score, "profile": profile, "answers": answers}},
    }

def _fund_search_pattern(search_term: str) -> str:
    cleaned = (
        search_term.lower()
        .replace("felxi", "flexi")
        .replace("bluechip", "blue chip")
        .replace(" fund", "")
        .replace(" growth", "")
        .replace(".", " ")
        .replace(",", " ")
        .strip()
    )
    words = [word for word in cleaned.split() if word]
    return f"%{'%'.join(words)}%" if words else "%"

def _normalize_portfolio_fund_name(name: str) -> str:
    text = " ".join(str(name or "").replace("-", " ").split())
    low = text.lower()
    if ("parag" in low or "ppfas" in low) and "flexi" in low:
        return "Parag Parikh Flexi Cap"
    if "hdfc" in low and "mid" in low and "cap" in low:
        return "HDFC Mid Cap Opportunities"
    if "hdfc" in low and "flexi" in low:
        return "HDFC Flexi Cap"
    if "hdfc" in low and "large" in low and "cap" in low:
        return "HDFC Large Cap"
    if "sbi" in low and ("blue" in low or "bluechip" in low):
        return "SBI Blue Chip"
    if "sbi" in low and "large" in low and "cap" in low:
        return "SBI Large Cap"
    if "sbi" in low and "flexi" in low:
        return "SBI Flexicap"
    if "icici" in low and "large" in low and "cap" in low:
        return "ICICI Prudential Large Cap"
    if "icici" in low and "multi" in low:
        return "ICICI Prudential Multi Asset"
    if "icici" in low and "flexi" in low:
        return "ICICI Prudential Flexicap"
    return text

def _portfolio_amc_terms(name: str) -> list[str]:
    low = str(name or "").lower()
    if "hdfc" in low:
        return ["hdfc"]
    if "sbi" in low:
        return ["sbi"]
    if "icici" in low:
        return ["icici", "prudential"]
    if "parag" in low or "ppfas" in low:
        return ["parag", "ppfas"]
    return []

def _portfolio_bucket_hint(name: str) -> str | None:
    text = _normalize_fund_text(str(name or ""))
    if "small cap" in text or "smallcap" in text:
        return "Small Cap"
    if "mid cap" in text or "midcap" in text:
        return "Mid Cap"
    if "large cap" in text or "largecap" in text or "blue chip" in text or "bluechip" in text:
        return "Large Cap"
    if "flexi" in text or "multi cap" in text:
        return "Flexi/Multi Cap"
    if "index" in text:
        return "Index"
    if "elss" in text:
        return "ELSS"
    return None

def _row_matches_portfolio_bucket(row: dict[str, Any], bucket: str) -> bool:
    if _portfolio_bucket(row.get("category")) == bucket:
        return True
    text = _normalize_fund_text(" ".join(str(row.get(field) or "") for field in ("scheme_name", "category")))
    if bucket == "Small Cap":
        return "small cap" in text
    if bucket == "Mid Cap":
        return "mid cap" in text
    if bucket == "Large Cap":
        return "large cap" in text or "blue chip" in text or "bluechip" in text
    if bucket == "Flexi/Multi Cap":
        return "flexi" in text or "multi cap" in text
    if bucket == "Index":
        return "index" in text
    if bucket == "ELSS":
        return "elss" in text
    return False

def _portfolio_bucket_candidates(name: str, fields: str) -> list[dict[str, Any]]:
    if not supabase:
        return []
    search_name = _normalize_portfolio_fund_name(name)
    bucket = _portfolio_bucket_hint(search_name) or _portfolio_bucket_hint(name)
    amc_terms = _portfolio_amc_terms(search_name) or _portfolio_amc_terms(name)
    if not bucket or not amc_terms:
        return []

    rows: list[dict[str, Any]] = []
    seen_codes: set[str] = set()

    def add_rows(next_rows: list[dict[str, Any]]) -> None:
        for row in next_rows:
            code = str(row.get("scheme_code") or row.get("scheme_name") or "")
            if code in seen_codes:
                continue
            seen_codes.add(code)
            rows.append(row)

    for term in amc_terms:
        try:
            add_rows(
                supabase.table("mutual_fund_core_snapshot")
                .select(fields)
                .ilike("scheme_name", f"%{term}%")
                .limit(100)
                .execute()
                .data
                or []
            )
        except Exception:
            pass
        try:
            add_rows(
                supabase.table("mutual_fund_core_snapshot")
                .select(fields)
                .ilike("amc_name", f"%{term}%")
                .limit(100)
                .execute()
                .data
                or []
            )
        except Exception:
            pass

    supported_rows = [row for row in rows if _is_supported_mf_row(row)]
    bucket_rows = [row for row in (supported_rows or rows) if _row_matches_portfolio_bucket(row, bucket)]
    return bucket_rows

def _portfolio_review_started(history: list[dict[str, str]]) -> bool:
    return any(message["role"] == "user" and _is_portfolio_review_start(message["content"]) for message in history) or _system_history_contains(history, "paste your mutual fund holdings")

def _parse_portfolio_holdings(query: str) -> list[dict[str, Any]]:
    text = str(query or "").strip()
    holdings: list[dict[str, Any]] = []
    amount_pattern = r"(?:rs\.?|inr|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?\s*(?:k|lakh|lac|cr|crore)?)"

    def _clean_holding_name(value: str) -> str:
        return re.sub(r"\s+", " ", value).strip(" .:-")

    for match in re.finditer(rf"{amount_pattern}\s+(?:in|into|for)\s+([^,\n;]+)", text, flags=re.IGNORECASE):
        amount = _money_token_to_float(match.group(1))
        name = _clean_holding_name(match.group(2))
        if amount and len(name) >= 3:
            holdings.append({"input_name": name, "amount": amount})
    if holdings:
        return holdings

    normalized_text = re.sub(
        r"((?:rs\.?|inr|₹)?\s*[0-9][0-9,]*(?:\.[0-9]+)?\s*(?:k|lakh|lac|cr|crore)?)\s+(?:and|&)\s+",
        r"\1, ",
        text,
        flags=re.IGNORECASE,
    )

    for part in re.split(r"[,;\n]+", normalized_text):
        match = re.search(rf"(.+?)\s*[:=-]\s*{amount_pattern}", part, flags=re.IGNORECASE)
        if not match:
            match = re.search(rf"(.+?)\s+{amount_pattern}\s*$", part.strip(), flags=re.IGNORECASE)
        if not match:
            continue
        name = _clean_holding_name(match.group(1))
        amount = _money_token_to_float(match.group(2))
        if amount and len(name) >= 3:
            holdings.append({"input_name": name, "amount": amount})
    return holdings

def _resolve_portfolio_fund(name: str) -> dict[str, Any] | None:
    if not supabase:
        return None
    search_name = _normalize_portfolio_fund_name(name)
    try:
        fields = "scheme_code,scheme_name,amc_name,category,return_3y,aum,expense_ratio,nav_date"
        rows = (
            supabase.table("mutual_fund_core_snapshot")
            .select(fields)
            .ilike("scheme_name", _fund_search_pattern(search_name))
            .limit(25)
            .execute()
            .data
            or []
        )
        if not rows and search_name != name:
            rows = (
                supabase.table("mutual_fund_core_snapshot")
                .select(fields)
                .ilike("scheme_name", _fund_search_pattern(name))
                .limit(25)
                .execute()
                .data
                or []
            )
        supported_rows = [row for row in rows if _is_supported_mf_row(row)]
        candidates = supported_rows or rows
        
        best_match = None
        if candidates:
            best_match = FundService.pick_best_fund_match(search_name, candidates, nav_history_cache={}, min_history_points=0)

        if not best_match:
            bucket_candidates = _portfolio_bucket_candidates(name, fields)
            if bucket_candidates:
                best_match = FundService.pick_best_fund_match(search_name, bucket_candidates, nav_history_cache={}, min_history_points=0)

        # Fallback for missing AUM and Expense Ratio for the selected best_match
        if best_match:
            if not best_match.get("aum") or not best_match.get("expense_ratio"):
                code = best_match.get("scheme_code")
                if code:
                    legacy_res = supabase.table("mutual_funds").select("aum,expense_ratio").eq("scheme_code", code).limit(1).execute()
                    if legacy_res.data:
                        legacy_row = legacy_res.data[0]
                        if not best_match.get("aum"):
                            best_match["aum"] = legacy_row.get("aum")
                        if not best_match.get("expense_ratio"):
                            best_match["expense_ratio"] = legacy_row.get("expense_ratio")
        return best_match
    except Exception as exc:
        logger.error("Portfolio fund match failed for %s: %s", name, exc)
        return None

def _portfolio_bucket(category: Any) -> str:
    text = str(category or "").lower()
    if "small" in text:
        return "Small Cap"
    if "mid" in text:
        return "Mid Cap"
    if "large" in text:
        return "Large Cap"
    if "flexi" in text or "multi cap" in text:
        return "Flexi/Multi Cap"
    if "index" in text:
        return "Index"
    if "debt" in text or "liquid" in text or "income" in text:
        return "Debt"
    if "hybrid" in text or "balanced" in text:
        return "Hybrid"
    if "elss" in text:
        return "ELSS"
    return "Unclassified"

def _load_latest_fund_holdings(scheme_code_value: Any) -> tuple[list[dict[str, Any]], str | None]:
    if not supabase or scheme_code_value in (None, ""):
        return [], None
    scheme_code = str(scheme_code_value)
    try:
        rows = (
            supabase.table("mutual_fund_holdings")
            .select("as_of_date,security_name,isin,sector,weight_pct,source,provider_payload")
            .eq("scheme_code", int(scheme_code) if scheme_code.isdigit() else scheme_code)
            .order("as_of_date", desc=True)
            .order("weight_pct", desc=True)
            .limit(500)
            .execute()
            .data
            or []
        )
    except Exception:
        return [], None

    latest_as_of = None
    holdings: list[dict[str, Any]] = []
    for row in rows:
        as_of = row.get("as_of_date")
        if latest_as_of is None:
            latest_as_of = as_of
        if as_of != latest_as_of:
            continue
        holdings.append(
            {
                "security_name": row.get("security_name"),
                "isin": row.get("isin"),
                "sector": row.get("sector"),
                "weight_pct": row.get("weight_pct"),
                "as_of_date": as_of,
                "source": row.get("source"),
                "provider_payload": row.get("provider_payload"),
            }
        )
    holdings.sort(key=lambda item: _holding_weight(item), reverse=True)
    return holdings, latest_as_of

def _build_portfolio_overlap(resolved: list[dict[str, Any]]) -> dict[str, Any]:
    matched = [item for item in resolved if item.get("matched")]
    if len(matched) < 2:
        return {"coverage_status": "unavailable", "reason": "Need at least two matched funds for portfolio overlap."}

    exposure_by_key: dict[str, dict[str, Any]] = {}
    sector_exposure: dict[str, dict[str, float]] = {}
    loaded_funds = 0
    as_of_dates: list[str] = []

    for item in matched:
        fund = item.get("matched") or {}
        fund_name = _safe_value(fund.get("scheme_name"))
        scheme_code = fund.get("scheme_code")
        holdings, as_of = _load_latest_fund_holdings(scheme_code)
        if not holdings:
            continue
        loaded_funds += 1
        if as_of:
            as_of_dates.append(str(as_of))
        fund_weight = float(item.get("weight") or 0.0)
        for row in holdings:
            if not isinstance(row, dict):
                continue
            key = _holding_key(row)
            holding_weight = _holding_weight(row)
            if not key or holding_weight <= 0:
                continue
            exposure = fund_weight * holding_weight
            existing = exposure_by_key.setdefault(
                key,
                {
                    "name": row.get("security_name") or "N/A",
                    "isin": row.get("isin"),
                    "sector": row.get("sector"),
                    "fund_exposures": [],
                },
            )
            existing["fund_exposures"].append({"fund": fund_name, "exposure": round(exposure, 4)})
            sector = str(row.get("sector") or "Unclassified").strip() or "Unclassified"
            sector_exposure.setdefault(sector, {})[fund_name] = sector_exposure.setdefault(sector, {}).get(fund_name, 0.0) + exposure

    if loaded_funds < 2:
        return {
            "coverage_status": "unavailable",
            "reason": "Holdings data is unavailable for enough matched funds.",
            "matched_fund_count": len(matched),
            "funds_with_holdings": loaded_funds,
        }

    common_holdings = []
    for row in exposure_by_key.values():
        exposures = row["fund_exposures"]
        if len(exposures) < 2:
            continue
        total_exposure = sum(float(item["exposure"]) for item in exposures)
        largest_single = max(float(item["exposure"]) for item in exposures)
        common_holdings.append(
            {
                "name": row.get("name"),
                "isin": row.get("isin"),
                "sector": row.get("sector"),
                "fund_count": len(exposures),
                "funds": [item["fund"] for item in exposures],
                "portfolio_exposure": round(total_exposure, 4),
                "overlap_exposure": round(total_exposure - largest_single, 4),
            }
        )
    common_holdings.sort(key=lambda row: row["overlap_exposure"], reverse=True)

    sector_overlap = []
    for sector, exposures in sector_exposure.items():
        if len(exposures) < 2:
            continue
        total_exposure = sum(exposures.values())
        largest_single = max(exposures.values())
        sector_overlap.append(
            {
                "sector": sector,
                "fund_count": len(exposures),
                "portfolio_exposure": round(total_exposure, 4),
                "overlap_exposure": round(total_exposure - largest_single, 4),
            }
        )
    sector_overlap.sort(key=lambda row: row["overlap_exposure"], reverse=True)

    return {
        "coverage_status": "available",
        "matched_fund_count": len(matched),
        "funds_with_holdings": loaded_funds,
        "as_of_date": " / ".join(sorted(set(as_of_dates))) if as_of_dates else None,
        "common_holding_count": len(common_holdings),
        "total_overlap_exposure": round(sum(row["overlap_exposure"] for row in common_holdings), 4),
        "top_common_holdings": common_holdings[:10],
        "sector_overlap": sector_overlap[:10],
    }

def _build_portfolio_review_insights(
    resolved: list[dict[str, Any]],
    bucket_totals: dict[str, float],
    overlap: dict[str, Any],
    score: int,
    label: str,
    total_amount: float,
) -> dict[str, Any]:
    matched = [item for item in resolved if item.get("matched")]
    unmatched = [item for item in resolved if not item.get("matched")]
    top_fund = max(resolved, key=lambda item: float(item.get("weight") or 0), default=None)
    bucket_rows = sorted(bucket_totals.items(), key=lambda pair: pair[1], reverse=True)
    largest_bucket, largest_bucket_amount = bucket_rows[0] if bucket_rows else ("N/A", 0.0)
    largest_bucket_pct = (largest_bucket_amount / total_amount * 100) if total_amount else 0.0
    overlap_value = _to_float_or_none(overlap.get("total_overlap_exposure")) or 0.0
    common_count = int(overlap.get("common_holding_count") or 0)

    if overlap.get("coverage_status") != "available":
        overlap_level = "Unknown"
        headline = "The review can read allocation, but holdings-level overlap is limited by missing holdings data."
    elif overlap_value >= 15:
        overlap_level = "High"
        headline = "The portfolio has meaningful duplicated stock exposure, so fund count may overstate diversification."
    elif overlap_value >= 7:
        overlap_level = "Moderate"
        headline = "The portfolio is diversified by category, but a few underlying stocks and sectors repeat across funds."
    elif common_count > 0:
        overlap_level = "Low"
        headline = "The portfolio has some shared holdings, but duplicated stock exposure is not dominant."
    else:
        overlap_level = "Low"
        headline = "The matched funds do not show meaningful common stock overlap in the latest holdings data."

    review_points = [
        f"Overall label is {label} with a score of {score}/100, based on match coverage, category spread, largest holding weight, and overlap data.",
        f"Largest allocation bucket is {largest_bucket} at {_format_percent(largest_bucket_pct)} of the pasted amount.",
    ]
    if top_fund:
        review_points.append(
            f"Largest fund weight is {_format_percent(float(top_fund.get('weight') or 0) * 100)} in {_safe_value(top_fund.get('input_name'))}; this matters more than the number of funds held."
        )
    if overlap.get("coverage_status") == "available":
        review_points.append(
            f"Duplicated stock exposure is {_format_percent(overlap_value)} across {common_count} common holdings."
        )

    overlap_read: list[str] = []
    if overlap.get("coverage_status") == "available":
        top_common = overlap.get("top_common_holdings") if isinstance(overlap.get("top_common_holdings"), list) else []
        top_sectors = overlap.get("sector_overlap") if isinstance(overlap.get("sector_overlap"), list) else []
        if top_common:
            names = ", ".join(_safe_value(item.get("name")) for item in top_common[:3])
            overlap_read.append(f"Main repeated holdings: {names}. These stocks can drive similar short-term movement across multiple funds.")
        if top_sectors:
            sector = top_sectors[0]
            overlap_read.append(
                f"Biggest repeated sector exposure is {_safe_value(sector.get('sector'))} at {_format_percent(sector.get('overlap_exposure'))} duplicated exposure."
            )
        if overlap_value >= 7:
            overlap_read.append("This overlap is not automatically bad, but it reduces the benefit of holding multiple funds if the repeated stocks or sectors move together.")
        elif common_count > 0:
            overlap_read.append("The overlap exists, but it is small enough that allocation and fund mandate differences still matter more.")
    else:
        overlap_read.append(f"Holdings overlap could not be reviewed fully: {_safe_value(overlap.get('reason'))}.")

    watchpoints: list[str] = []
    if unmatched:
        watchpoints.append(f"{len(unmatched)} submitted holding(s) were unmatched, so the review may understate concentration or overlap.")
    if largest_bucket_pct >= 50:
        watchpoints.append(f"{largest_bucket} is at {_format_percent(largest_bucket_pct)}, so this bucket dominates the submitted portfolio.")
    if top_fund and float(top_fund.get("weight") or 0) >= 0.35:
        watchpoints.append(f"{_safe_value(top_fund.get('input_name'))} is above 35% of the pasted portfolio, making it the main driver of outcomes.")
    if overlap_value >= 7:
        watchpoints.append("Repeated exposure is worth checking against your reason for holding each fund; two funds may still behave similarly if they own the same banks, IT names, or market leaders.")
    if not watchpoints:
        watchpoints.append("No single deterministic red flag appears from the submitted allocation and latest holdings overlap.")

    next_questions = [
        "Ask: Which common holding contributes most to duplicated exposure?",
        "Ask: Is the sector overlap concentrated in banks, IT, or another sector?",
        "Ask: Which fund is driving most of the portfolio risk?",
    ]

    return {
        "headline": headline,
        "overlap_level": overlap_level,
        "review_points": review_points,
        "overlap_read": overlap_read,
        "watchpoints": watchpoints,
        "next_questions": next_questions,
    }

def _portfolio_review_insights_markdown(insights: dict[str, Any]) -> str:
    if not insights:
        return ""
    lines = ["### Review Interpretation"]
    if insights.get("headline"):
        lines.append(_safe_value(insights.get("headline")))
    lines.append("")
    lines.append("| Review Area | Read |")
    lines.append("| --- | --- |")
    lines.append(f"| Overlap level | {_safe_value(insights.get('overlap_level'))} |")
    for item in (insights.get("review_points") or [])[:4]:
        lines.append(f"| Portfolio read | {_safe_value(item)} |")
    for item in (insights.get("overlap_read") or [])[:3]:
        lines.append(f"| Overlap read | {_safe_value(item)} |")
    for item in (insights.get("watchpoints") or [])[:4]:
        lines.append(f"| Watchpoint | {_safe_value(item)} |")
    next_questions = insights.get("next_questions") if isinstance(insights.get("next_questions"), list) else []
    if next_questions:
        lines.append("")
        lines.append("### Follow-up Questions")
        lines.extend(f"- {question}" for question in next_questions[:3])
    return "\n".join(lines)

def _portfolio_context_payload(query: str, review: dict[str, Any]) -> dict[str, Any]:
    payload = (review.get("quant_data") or {}).get("portfolio_review") if isinstance(review, dict) else {}
    if not isinstance(payload, dict) or not payload.get("holdings"):
        return {}
    holdings = []
    for item in (payload.get("holdings") or [])[:12]:
        if not isinstance(item, dict):
            continue
        matched = item.get("matched") if isinstance(item.get("matched"), dict) else {}
        holdings.append(
            {
                "input_name": item.get("input_name"),
                "amount": item.get("amount"),
                "weight": item.get("weight"),
                "matched_fund": matched.get("scheme_name") if matched else None,
                "bucket": item.get("bucket"),
            }
        )
    return {
        "last_portfolio": {
            "query": query,
            "score": payload.get("score"),
            "label": payload.get("label"),
            "holdings": holdings,
            "buckets": payload.get("buckets") or {},
            "overlap": payload.get("overlap") or {},
            "insights": payload.get("insights") or {},
            "available_topics": ["allocation", "holdings_overlap", "sector_overlap", "concentration", "unmatched", "review_points"],
        }
    }

def _last_portfolio_from_context(context: Any) -> dict[str, Any] | None:
    if context is None:
        return None
    portfolio = context.get("last_portfolio") if isinstance(context, dict) else getattr(context, "last_portfolio", None)
    if portfolio is None:
        return None
    if isinstance(portfolio, dict):
        return portfolio
    return {
        "query": getattr(portfolio, "query", None),
        "score": getattr(portfolio, "score", None),
        "label": getattr(portfolio, "label", None),
        "holdings": getattr(portfolio, "holdings", []) or [],
        "buckets": getattr(portfolio, "buckets", {}) or {},
        "overlap": getattr(portfolio, "overlap", {}) or {},
        "insights": getattr(portfolio, "insights", {}) or {},
        "available_topics": getattr(portfolio, "available_topics", []) or [],
    }

def _build_portfolio_followup_response(query: str, conversation_context: Any) -> dict[str, Any] | None:
    portfolio = _last_portfolio_from_context(conversation_context)
    if not portfolio:
        return None
    low = query.lower()
    wants_risk = any(term in low for term in ("risk", "risky", "volatile", "volatility", "aggressive", "most risk"))
    wants_balance = any(term in low for term in ("balance", "rebalance", "balanced", "change", "changes", "adjust", "improve", "reduce", "increase"))
    followup_terms = (
        "overlap", "common", "same stock", "same holding", "holding", "sector",
        "allocation", "concentration", "divers", "risk", "unmatched", "bucket",
        "review", "interpret", "summary", "good", "bad", "points", "which fund", "what about", "why",
        "risky", "volatile", "volatility", "aggressive", "balance", "rebalance", "balanced",
        "change", "changes", "adjust", "improve", "reduce", "increase",
    )
    if not any(term in low for term in followup_terms):
        return None

    overlap = portfolio.get("overlap") if isinstance(portfolio.get("overlap"), dict) else {}
    holdings = portfolio.get("holdings") if isinstance(portfolio.get("holdings"), list) else []
    buckets = portfolio.get("buckets") if isinstance(portfolio.get("buckets"), dict) else {}
    insights = portfolio.get("insights") if isinstance(portfolio.get("insights"), dict) else {}
    lines = ["### Portfolio Follow-up"]
    top_fund = max(holdings, key=lambda item: float(item.get("weight") or 0), default=None)
    bucket_rows = sorted(buckets.items(), key=lambda pair: float(pair[1] or 0), reverse=True) if buckets else []
    bucket_total = sum(float(value or 0) for value in buckets.values()) if buckets else 0
    largest_bucket, largest_bucket_amount = bucket_rows[0] if bucket_rows else (None, 0)
    largest_bucket_pct = float(largest_bucket_amount or 0) / bucket_total * 100 if bucket_total else 0

    if wants_risk:
        if top_fund:
            lines.append(
                f"- Main fund-level risk driver by submitted weight: {_safe_value(top_fund.get('input_name'))} at {_format_percent(float(top_fund.get('weight') or 0) * 100)}."
            )
        if largest_bucket:
            lines.append(f"- Main category concentration: {_safe_value(largest_bucket)} at {_format_percent(largest_bucket_pct)} of pasted amount.")
        if overlap.get("coverage_status") == "available":
            lines.append(
                f"- Holdings overlap risk: duplicated stock exposure is {_format_percent(overlap.get('total_overlap_exposure'))} across {overlap.get('common_holding_count', 0)} common holdings."
            )
            top_common = overlap.get("top_common_holdings") if isinstance(overlap.get("top_common_holdings"), list) else []
            if top_common:
                item = top_common[0]
                lines.append(f"- Largest repeated holding: {_safe_value(item.get('name'))} at {_format_percent(item.get('portfolio_exposure'))} total portfolio exposure.")
        elif overlap:
            lines.append(f"- Holdings overlap risk is unavailable: {_safe_value(overlap.get('reason'))}.")

    if wants_balance:
        lines.append("- Balance levers to test:")
        if top_fund:
            lines.append(f"  - Scenario-check reducing dependence on {_safe_value(top_fund.get('input_name'))}; it has the largest effect because it is the biggest fund weight.")
        if largest_bucket:
            lines.append(f"  - Scenario-check lowering {_safe_value(largest_bucket)} concentration if the intent is broader category spread.")
        existing_buckets = {str(bucket).lower() for bucket, _amount in bucket_rows}
        if not any("large" in bucket for bucket in existing_buckets):
            lines.append("  - Large Cap exposure is not visible in the saved bucket mix; compare whether adding it improves stability metrics.")
        if not any("debt" in bucket for bucket in existing_buckets):
            lines.append("  - Debt/liquid exposure is not visible in the saved bucket mix; compare separately if lower volatility is the goal.")
        lines.append("  - Use the fund comparison view to check returns, volatility, expense ratio, and holdings overlap before making any real change.")

    if any(term in low for term in ("review", "interpret", "summary", "good", "bad", "powerup", "points")) and insights:
        if insights.get("headline"):
            lines.append(f"- {_safe_value(insights.get('headline'))}")
        for item in (insights.get("review_points") or [])[:3]:
            lines.append(f"- {_safe_value(item)}")
        for item in (insights.get("watchpoints") or [])[:3]:
            lines.append(f"- Watchpoint: {_safe_value(item)}")

    if any(term in low for term in ("overlap", "common", "same stock", "same holding", "holding")):
        if overlap.get("coverage_status") == "available":
            lines.append(f"- Duplicated stock exposure is {_format_percent(overlap.get('total_overlap_exposure'))} across {overlap.get('common_holding_count', 0)} common holdings.")
            for item in (overlap.get("top_common_holdings") or [])[:5]:
                lines.append(
                    f"- {_safe_value(item.get('name'))}: {_format_percent(item.get('portfolio_exposure'))} total portfolio exposure, {_format_percent(item.get('overlap_exposure'))} duplicated exposure across {item.get('fund_count', 0)} funds."
                )
        else:
            lines.append(f"- Holdings overlap is unavailable: {_safe_value(overlap.get('reason'))}.")

    if "sector" in low:
        sectors = overlap.get("sector_overlap") if isinstance(overlap.get("sector_overlap"), list) else []
        if sectors:
            lines.append("- Sector overlap:")
            for item in sectors[:5]:
                lines.append(f"  - {_safe_value(item.get('sector'))}: {_format_percent(item.get('overlap_exposure'))} duplicated sector exposure.")
        else:
            lines.append("- Sector overlap needs holdings-level sector data across at least two matched funds.")

    if any(term in low for term in ("allocation", "bucket", "divers", "concentration", "risk")):
        if buckets and bucket_total:
            lines.append("- Category allocation:")
            for bucket, amount in bucket_rows:
                lines.append(f"  - {bucket}: {_format_percent(float(amount or 0) / bucket_total * 100)} of pasted amount.")
        if top_fund:
            lines.append(f"- Largest fund weight is {_format_percent(float(top_fund.get('weight') or 0) * 100)} in {_safe_value(top_fund.get('input_name'))}.")

    if "unmatched" in low:
        unmatched = [item for item in holdings if str(item.get("bucket") or "").lower() == "unmatched"]
        if unmatched:
            lines.append("- Unmatched entries: " + ", ".join(_safe_value(item.get("input_name")) for item in unmatched) + ".")
        else:
            lines.append("- All submitted holdings were matched in the last portfolio review.")

    lines.append("")
    lines.append("This is based on the submitted portfolio review in this chat, not a new suitability recommendation.")
    return {
        "answer": "\n".join(lines),
        "debug_intent": {"intent": "portfolio_followup", "source": "conversation_context"},
        "quant_data": {"portfolio_review": portfolio},
        "conversation_context": {"last_portfolio": portfolio},
        "system_action": {"type": "PORTFOLIO_REVIEW"},
    }

def _build_portfolio_review_response(query: str, history: list[dict[str, str]]) -> dict[str, Any] | None:
    holdings = _parse_portfolio_holdings(query)
    if not holdings:
        if _is_portfolio_review_start(query) or _portfolio_review_started(history):
            answer = """### Portfolio Review
Paste your mutual fund holdings with amounts.

Example: `50k in Parag Parikh Flexi Cap, 20k in HDFC Mid-Cap, 30k in SBI Bluechip`"""
            return {
                "answer": answer,
                "debug_intent": {"intent": "portfolio_review", "step": "awaiting_holdings"},
                "quant_data": {"portfolio_review": {"holdings": []}},
            }
        return None

    resolved: list[dict[str, Any]] = []
    total_amount = sum(float(item["amount"]) for item in holdings)
    for item in holdings:
        match = _resolve_portfolio_fund(item["input_name"])
        amount = float(item["amount"])
        category = match.get("category") if match else None
        db_bucket = _portfolio_bucket(category) if match else "Unmatched"
        input_bucket = _portfolio_bucket_hint(item["input_name"])
        bucket = input_bucket if match and db_bucket in {"Unclassified", "Unmatched"} and input_bucket else db_bucket
        resolved.append({
            **item,
            "weight": amount / total_amount if total_amount else 0,
            "matched": match,
            "bucket": bucket,
        })

    bucket_totals: dict[str, float] = {}
    for item in resolved:
        bucket_totals[item["bucket"]] = bucket_totals.get(item["bucket"], 0.0) + float(item["amount"])

    matched_amount = sum(float(item["amount"]) for item in resolved if item["matched"])
    matched_pct = (matched_amount / total_amount * 100) if total_amount else 0
    top_weight = max((item["weight"] for item in resolved), default=0) * 100
    bucket_count = len([bucket for bucket in bucket_totals if bucket != "Unmatched"])
    score = 100 - max(top_weight - 35, 0) - (100 - matched_pct) * 0.5 + min(bucket_count, 4) * 3
    score = max(0, min(100, round(score)))
    label = "Good" if score >= 75 else "Fair" if score >= 55 else "Needs review"

    holding_rows = [
        [
            _safe_value(item["input_name"]),
            _format_inr_amount(item["amount"]),
            f"{item['weight'] * 100:.1f}%",
            _safe_value((item["matched"] or {}).get("scheme_name")),
            item["bucket"],
        ]
        for item in resolved
    ]
    bucket_rows = [
        [bucket, _format_inr_amount(amount), f"{(amount / total_amount * 100 if total_amount else 0):.1f}%"]
        for bucket, amount in sorted(bucket_totals.items(), key=lambda pair: pair[1], reverse=True)
    ]
    unmatched = [item["input_name"] for item in resolved if not item["matched"]]
    notes = [
        f"Matched coverage: {matched_pct:.1f}% of pasted amount.",
        f"Largest single holding weight: {top_weight:.1f}%.",
        f"Detected category buckets: {bucket_count}.",
    ]
    if unmatched:
        notes.append(f"Unmatched entries: {', '.join(unmatched)}.")

    overlap = _build_portfolio_overlap(resolved)
    insights = _build_portfolio_review_insights(resolved, bucket_totals, overlap, score, label, total_amount)
    insights_section = _portfolio_review_insights_markdown(insights)
    if overlap.get("coverage_status") == "available":
        overlap_rows = [
            [
                _safe_value(item.get("name")),
                _safe_value(item.get("sector")),
                str(item.get("fund_count") or 0),
                _format_percent(item.get("portfolio_exposure")),
                _format_percent(item.get("overlap_exposure")),
            ]
            for item in (overlap.get("top_common_holdings") or [])[:5]
        ]
        overlap_section = f"""### Portfolio Overlap
| Metric | Result |
| --- | --- |
| Funds with holdings data | {overlap.get("funds_with_holdings")}/{overlap.get("matched_fund_count")} |
| Common holdings | {overlap.get("common_holding_count")} |
| Duplicated stock exposure | {_format_percent(overlap.get("total_overlap_exposure"))} |

{_markdown_table(["Common Holding", "Sector", "Funds", "Portfolio Exposure", "Duplicated Exposure"], overlap_rows) if overlap_rows else "No common stock holdings were found across the matched funds."}"""
    else:
        overlap_section = f"""### Portfolio Overlap
Holdings overlap unavailable: {_safe_value(overlap.get("reason"))}"""

    answer = f"""### Portfolio Health Check
| Metric | Result |
| --- | --- |
| Health score | {score}/100 |
| Label | {label} |
| Total pasted amount | {_format_inr_amount(total_amount)} |

### Holdings
{_markdown_table(["Input", "Amount", "Weight", "Matched Fund", "Bucket"], holding_rows)}

### Category Allocation
{_markdown_table(["Bucket", "Amount", "Weight"], bucket_rows)}

{insights_section}

{overlap_section}

### Research Notes
{chr(10).join(f"- {note}" for note in notes)}

This is a diversification snapshot from pasted text, not a complete suitability review or investment advice.

{DISCLAIMER}"""
    response = {
        "answer": answer,
        "debug_intent": {"intent": "portfolio_review", "step": "complete", "score": score, "label": label},
        "quant_data": {"portfolio_review": {"score": score, "label": label, "holdings": resolved, "buckets": bucket_totals, "overlap": overlap, "insights": insights}},
    }
    response["conversation_context"] = _portfolio_context_payload(query, response)
    response["system_action"] = {"type": "PORTFOLIO_REVIEW"}
    return response

def _build_deferred_dashboard_response(query: str, history: list[Any], conversation_context: Any = None) -> dict[str, Any] | None:
    history_messages = _history_payload(history)
    portfolio_followup = _build_portfolio_followup_response(query, conversation_context)
    if portfolio_followup:
        return portfolio_followup
    risk_response = _build_risk_quiz_response(query, history_messages)
    if risk_response:
        return risk_response
    return _build_portfolio_review_response(query, history_messages)

def _is_supported_mf_row(row: dict[str, Any]) -> bool:
    text = " ".join(
        str(row.get(field) or "").lower()
        for field in ("scheme_name", "amc_name", "fund_house")
    )
    return any(marker in text for markers in SUPPORTED_MF_AMC_MARKERS.values() for marker in markers)

def _category_key_from_value(value: str) -> str | None:
    normalized = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "large": "large_cap",
        "largecap": "large_cap",
        "large_cap": "large_cap",
        "mid": "mid_cap",
        "midcap": "mid_cap",
        "mid_cap": "mid_cap",
        "small": "small_cap",
        "smallcap": "small_cap",
        "small_cap": "small_cap",
        "flexi": "flexi_cap",
        "flexicap": "flexi_cap",
        "flexi_cap": "flexi_cap",
        "index": "index",
        "index_funds": "index",
        "elss": "elss",
    }
    return aliases.get(normalized) or (normalized if normalized in CATEGORY_SEARCH_CONFIG else None)

def _category_row_matches(row: dict[str, Any], category_key: str) -> bool:
    config = CATEGORY_SEARCH_CONFIG[category_key]
    category_text = _normalize_fund_text(str(row.get("category") or ""))
    scheme_text = _normalize_fund_text(str(row.get("scheme_name") or ""))
    match_text = _normalize_fund_text(str(config["match"]))
    scheme_match = _normalize_fund_text(str(config.get("scheme_match") or config["match"]))
    if match_text and match_text in category_text:
        return True
    if scheme_match and scheme_match in scheme_text:
        return True
    if category_key == "index" and "index" in scheme_text:
        return True
    return False

def _decorate_category_row(row: dict[str, Any]) -> dict[str, Any]:
    is_supported = _is_supported_mf_row(row)
    return {
        **row,
        "is_supported": is_supported,
        "disabled_reason": None if is_supported else "Coming Soon",
    }

def _category_sort_key(row: dict[str, Any]) -> tuple[int, int, float]:
    has_return = _to_float_or_none(row.get("return_3y")) is not None
    ranking_value = _to_float_or_none(row.get("return_3y")) if has_return else _to_float_or_none(row.get("aum"))
    return (0 if row.get("is_supported") else 1, 0 if has_return else 1, -(ranking_value or 0.0))

def _category_snapshot_fields() -> str:
    return (
        "scheme_code,scheme_name,amc_name,category,return_1y,return_3y,return_5y,aum,"
        "expense_ratio,risk_level,nav_date,last_updated,alpha,beta,sharpe_ratio,volatility_1y,max_drawdown_1y"
    )

def _read_category_rows(category_key: str, include_unsupported: bool = False, limit: int = 100) -> list[dict[str, Any]]:
    if not supabase:
        logger.error("Supabase client not initialized")
        return []

    config = CATEGORY_SEARCH_CONFIG[category_key]
    fields = _category_snapshot_fields()
    rows: list[dict[str, Any]] = []
    try:
        res = (
            supabase.table("mutual_fund_core_snapshot")
            .select(fields)
            .ilike("category", f"%{config['match']}%")
            .limit(500)
            .execute()
        )
        rows = res.data or []
        if config.get("scheme_match"):
            res = (
                supabase.table("mutual_fund_core_snapshot")
                .select(fields)
                .ilike("scheme_name", f"%{config['scheme_match']}%")
                .limit(500)
                .execute()
            )
            seen = {str(row.get("scheme_code") or row.get("scheme_name")) for row in rows}
            for row in res.data or []:
                key = str(row.get("scheme_code") or row.get("scheme_name"))
                if key not in seen:
                    seen.add(key)
                    rows.append(row)
    except Exception as exc:
        logger.error("Category search DB error: %s", exc)
        return []

    matched_rows = [_decorate_category_row(row) for row in rows if _category_row_matches(row, category_key)]
    if not matched_rows:
        matched_rows = [_decorate_category_row(row) for row in rows]
    
    # Filter out funds where AUM is missing so we only show the variants that actually have parsed data
    matched_rows = [row for row in matched_rows if row.get("aum") is not None]
    
    return sorted(matched_rows, key=_category_sort_key)[:limit]

def _build_category_search_response(intent_info: dict[str, Any]) -> dict[str, Any]:
    category_key = intent_info["category_key"]
    label = intent_info["category_label"]
    rows = _read_category_rows(category_key)
    if not rows:
        answer = f"""### {label} Funds
No matching {label} fund data is available in FundersAI's supported AMC snapshot yet.

This category view is limited to available FundersAI data and is not investment advice.

{DISCLAIMER}"""
        return {
            "answer": answer,
            "debug_intent": intent_info,
            "quant_data": {"category_search": {"category": label, "rows": []}},
        }

    has_returns = any(_to_float_or_none(row.get("return_3y")) is not None for row in rows)
    if has_returns:
        sorted_rows = sorted(
            rows,
            key=lambda row: (_to_float_or_none(row.get("return_3y")) is None, -(_to_float_or_none(row.get("return_3y")) or -1e18)),
        )
        ranking_label = "Top by 3Y return"
    else:
        sorted_rows = sorted(rows, key=lambda row: _to_float_or_none(row.get("aum")) or 0, reverse=True)
        ranking_label = "Largest by AUM"

    table_rows = [
        [
            _safe_value(row.get("scheme_name")),
            _safe_value(row.get("category")),
            _format_percent(row.get("return_3y")),
            _format_inr_market_cap(row.get("aum")),
            _format_percent(row.get("expense_ratio")),
            _safe_value(row.get("risk_level") or "Risk label unavailable"),
            _safe_value(row.get("nav_date")),
        ]
        for row in sorted_rows[:5]
    ]
    answer = f"""### {label} Funds - {ranking_label}
{_markdown_table(["Fund", "Category", "3Y Return", "AUM", "Expense Ratio", "Risk Label", "NAV Date"], table_rows)}

This is a category snapshot based on available FundersAI data, not a recommendation.

{DISCLAIMER}"""
    return {
        "answer": answer,
        "debug_intent": intent_info,
        "quant_data": {
            "category_search": {
                "category": label,
                "ranking": ranking_label,
                "rows": sorted_rows[:5],
            }
        },
    }

def _category_list_payload(category_key: str) -> dict[str, Any]:
    rows = _read_category_rows(category_key, include_unsupported=True, limit=100)
    has_returns = any(_to_float_or_none(row.get("return_3y")) is not None for row in rows)
    ranking_label = "Top by 3Y return" if has_returns else "Largest by AUM"
    return {
        "category_key": category_key,
        "category": CATEGORY_SEARCH_CONFIG[category_key]["label"],
        "ranking": ranking_label,
        "rows": rows,
    }

def _read_snapshot_rows_by_scheme_codes(scheme_codes: list[str]) -> list[dict[str, Any]]:
    if not supabase:
        return []
    fields = _category_snapshot_fields()
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for code in scheme_codes:
        code_str = str(code or "").strip()
        if not code_str or code_str in seen:
            continue
        seen.add(code_str)
        try:
            res = (
                supabase.table("mutual_fund_core_snapshot")
                .select(fields)
                .eq("scheme_code", int(code_str) if code_str.isdigit() else code_str)
                .limit(1)
                .execute()
            )
            if res.data:
                rows.append(_decorate_category_row(res.data[0]))
        except Exception as exc:
            logger.error("Category compare row lookup failed for %s: %s", code_str, exc)
    return rows

def _category_fund_metrics(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "scheme_code": row.get("scheme_code"),
        "scheme_name": row.get("scheme_name"),
        "amc_name": row.get("amc_name"),
        "category": row.get("category"),
        "return_1y": row.get("return_1y"),
        "return_3y": row.get("return_3y"),
        "return_5y": row.get("return_5y"),
        "aum": row.get("aum"),
        "expense_ratio": row.get("expense_ratio"),
        "risk_level": row.get("risk_level"),
        "alpha": row.get("alpha"),
        "beta": row.get("beta"),
        "sharpe_ratio": row.get("sharpe_ratio"),
        "volatility_1y": row.get("volatility_1y"),
        "max_drawdown_1y": row.get("max_drawdown_1y"),
        "nav_date": row.get("nav_date"),
        "last_updated": row.get("last_updated"),
    }

def _sector_exposure_from_holdings(holdings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    sectors: dict[str, float] = {}
    for row in holdings:
        sector = str(row.get("sector") or "Unclassified").strip() or "Unclassified"
        sectors[sector] = sectors.get(sector, 0.0) + _holding_weight(row)
    return [
        {"sector": sector, "weight_pct": round(weight, 4)}
        for sector, weight in sorted(sectors.items(), key=lambda pair: pair[1], reverse=True)
    ][:10]

def _build_category_compare_payload(category_key: str, scheme_codes: list[str]) -> dict[str, Any]:
    category_key = _category_key_from_value(category_key) or category_key
    if category_key not in CATEGORY_SEARCH_CONFIG:
        raise HTTPException(status_code=400, detail="Unsupported category.")

    clean_codes = [str(code or "").strip() for code in scheme_codes if str(code or "").strip()]
    clean_codes = list(dict.fromkeys(clean_codes))
    if len(clean_codes) < 2 or len(clean_codes) > 3:
        raise HTTPException(status_code=400, detail="Select 2 to 3 supported funds.")

    rows = _read_snapshot_rows_by_scheme_codes(clean_codes)
    rows_by_code = {str(row.get("scheme_code")): row for row in rows}
    missing = [code for code in clean_codes if code not in rows_by_code]
    if missing:
        raise HTTPException(status_code=404, detail=f"Fund data not found for: {', '.join(missing)}")

    equal_amount = 100.0 / len(rows)
    resolved: list[dict[str, Any]] = []
    selected_funds: list[dict[str, Any]] = []
    holdings_by_code: dict[str, list[dict[str, Any]]] = {}
    sectors_by_code: dict[str, list[dict[str, Any]]] = {}

    for row in rows:
        code = str(row.get("scheme_code"))
        holdings, holdings_as_of = _load_latest_fund_holdings(row.get("scheme_code"))
        holdings_by_code[code] = holdings[:25]
        sectors_by_code[code] = _sector_exposure_from_holdings(holdings)
        bucket = _portfolio_bucket(row.get("category"))
        resolved.append(
            {
                "input_name": row.get("scheme_name"),
                "amount": equal_amount,
                "weight": 1 / len(rows),
                "matched": row,
                "bucket": bucket if bucket != "Unclassified" else (_portfolio_bucket_hint(row.get("scheme_name")) or bucket),
            }
        )
        selected_funds.append(
            {
                **_category_fund_metrics(row),
                "bucket": resolved[-1]["bucket"],
                "holdings_as_of_date": holdings_as_of,
                "top_holdings": holdings[:10],
                "sector_allocation": sectors_by_code[code],
            }
        )

    bucket_totals: dict[str, float] = {}
    for item in resolved:
        bucket_totals[item["bucket"]] = bucket_totals.get(item["bucket"], 0.0) + float(item["amount"])

    overlap = _build_portfolio_overlap(resolved)
    score = 100 - max((max(item["weight"] for item in resolved) * 100) - 35, 0) + min(len(bucket_totals), 4) * 3
    score = max(0, min(100, round(score)))
    label = "Good" if score >= 75 else "Fair" if score >= 55 else "Needs review"
    insights = _build_portfolio_review_insights(resolved, bucket_totals, overlap, score, label, 100.0)

    return {
        "category_key": category_key,
        "category": CATEGORY_SEARCH_CONFIG[category_key]["label"],
        "selected_funds": selected_funds,
        "metric_groups": {
            "returns": ["return_1y", "return_3y", "return_5y"],
            "risk": ["risk_level", "volatility_1y", "max_drawdown_1y", "sharpe_ratio", "alpha", "beta"],
            "cost_scale": ["expense_ratio", "aum", "nav_date"],
        },
        "holdings": holdings_by_code,
        "sectors": sectors_by_code,
        "overlap": overlap,
        "insights": insights,
        "score": score,
        "label": label,
        "research_note": "Category comparison uses an equal-weighted selected set for overlap math. This is research only, not investment advice.",
    }

@app.get("/api/funds/category")
def category_funds_endpoint(category: str):
    category_key = _category_key_from_value(category)
    if not category_key:
        raise HTTPException(status_code=400, detail="Unsupported category.")
    return _category_list_payload(category_key)

@app.post("/api/funds/category/compare")
def category_funds_compare_endpoint(req: CategoryCompareRequest):
    return _build_category_compare_payload(req.category, req.scheme_codes)

def _stock_metric_rows(data: dict) -> list[tuple[str, str]]:
    period = _risk_period(data)
    source_summary = data.get("source_summary") or {}
    rows = [
        ("Timestamp", _safe_value(data.get("timestamp"))),
        ("Price", _format_price(data.get("price"))),
        ("Change", _format_percent(data.get("change_pct"))),
        ("P/E Ratio", _safe_value(data.get("pe_ratio"))),
        ("Market Cap", _format_inr_market_cap(data.get("market_cap"))),
        (f"Beta ({period})", _safe_value(data.get("beta"))),
        (f"Alpha vs Nifty ({period})", _format_percent(data.get("alpha_vs_nifty"))),
        ("RSI (14D)", _safe_value(data.get("rsi_14d"))),
        ("Technical Rating", _safe_recommendation(data.get("tv_recommendation"))),
        ("Source", _safe_value(data.get("source") or source_summary.get("metadata") or "source unavailable")),
        ("Fetched At", _safe_value(data.get("fetchedAt") or source_summary.get("indianapi_fetched_at") or data.get("timestamp"))),
    ]
    fundamentals = data.get("fundamentals") or {}
    if fundamentals:
        rows.extend([
            ("Industry", _safe_value(fundamentals.get("industry"))),
            ("PB Ratio", _safe_value(fundamentals.get("pb"))),
            ("Dividend Yield", _format_ratio_percent(fundamentals.get("dividend_yield"))),
            ("Latest Quarterly Net Profit", _format_inr_market_cap(fundamentals.get("net_profit_qtr"))),
            ("Latest Quarterly Revenue", _format_inr_market_cap(fundamentals.get("revenue_qtr"))),
            ("ROCE", _format_ratio_percent(fundamentals.get("roce"))),
            ("ROE", _format_ratio_percent(fundamentals.get("roe"))),
            ("EPS TTM", _format_price(fundamentals.get("eps_ttm"))),
            ("EV / EBITDA", _safe_value(fundamentals.get("ev_ebitda"))),
            ("Sales Growth (3Y)", _format_ratio_percent(fundamentals.get("sales_growth_3y"))),
            ("Profit Growth (3Y)", _format_ratio_percent(fundamentals.get("profit_growth_3y"))),
            ("EPS Growth (3Y)", _format_ratio_percent(fundamentals.get("eps_growth_3y"))),
            ("Debt to Equity", _safe_value(fundamentals.get("debt_to_equity"))),
            ("Promoter Holding", _format_ratio_percent(fundamentals.get("promoter_holding"))),
            ("FII Holding", _format_ratio_percent(fundamentals.get("fii_holding"))),
            ("DII Holding", _format_ratio_percent(fundamentals.get("dii_holding"))),
            ("Data Source", _safe_value(fundamentals.get("source") or "source unavailable")),
        ])
    return rows

def _fund_metric_rows(data: dict) -> list[tuple[str, str]]:
    period = _risk_period(data)
    nav = _unwrap_nested_value(data.get("nav", data.get("price")), ("nav", "latest_nav", "current", "value"))
    nav_date = _unwrap_nested_value(data.get("nav_date", data.get("date")), ("nav_date", "date"))
    fund_house = _unwrap_nested_value(data.get("fund_house"), ("name", "fund_house", "amc"))
    category = _unwrap_nested_value(data.get("category"), ("category", "schemeType", "name"))
    expense_ratio = _unwrap_nested_value(data.get("expense_ratio"), ("current", "expense_ratio", "expenseRatio", "ratio", "value"))
    aum = _unwrap_nested_value(data.get("aum"), ("aum", "asset_size", "value", "current"))
    risk_level = str(data.get("risk_level") or "").strip()
    return [
        ("Matched Name", _safe_value(data.get("name"))),
        ("NAV", _format_price(nav)),
        ("NAV Date", _safe_value(nav_date)),
        ("Fund House", _safe_value(fund_house)),
        ("Category", _safe_value(category)),
        ("Risk Label", risk_level or "Risk label unavailable"),
        ("Risk Label Source", "Official AMC factsheet" if risk_level else "Unavailable"),
        ("Return (3Y)", _format_percent(data.get("return_3y"))),
        ("Volatility (1Y)", _format_percent(data.get("volatility_1y"))),
        ("Max Drawdown (1Y)", _format_percent(data.get("max_drawdown_1y"))),
        ("Sharpe Ratio", _safe_value(data.get("sharpe_ratio"))),
        ("Expense Ratio", _safe_value(expense_ratio)),
        ("AUM", _format_inr_market_cap(aum)),
        (f"Beta ({period})", _safe_value(data.get("beta"))),
        (f"Alpha vs Nifty ({period})", _format_percent(data.get("alpha_vs_nifty"))),
        ("Source", _safe_value(data.get("source") or "source unavailable")),
        ("Fetched At", _safe_value(data.get("fetchedAt") or nav_date)),
    ]

def _looks_like_fund(data: dict) -> bool:
    return any(key in data for key in ["nav", "nav_date", "fund_house", "expense_ratio"]) and "timestamp" not in data

def _stock_compare_item(symbol: str, risk_metrics: dict | None = None) -> dict:
    stock_response = build_stock_compare([symbol])
    comparison = stock_response.get("comparison") or {}
    item = comparison.get(symbol) or next(iter(comparison.values()), None)
    if not item:
        return {"error": "Data not found for this entity"}
    if risk_metrics and not item.get("error"):
        item.update(risk_metrics)
    return item

def _walk_dicts(data: Any):
    if isinstance(data, dict):
        yield data
        for value in data.values():
            yield from _walk_dicts(value)
    elif isinstance(data, list):
        for item in data:
            yield from _walk_dicts(item)

def _comparison_rows(comparison: dict) -> tuple[list[str], list[list[str]], list[str]]:
    entities = list(comparison.keys())
    valid_entities = {name: data for name, data in comparison.items() if not _is_unavailable_entity(data)}
    notes = [
        f"{name} could not be matched in FundersAI data."
        for name, data in comparison.items()
        if _is_unavailable_entity(data)
    ]
    for name, data in valid_entities.items():
        quality = data.get("data_quality") or {}
        message = quality.get("message")
        if message and message not in notes and quality.get("missing_fields"):
            notes.append(f"{name}: {message}")

    uses_fund_metrics = any(_looks_like_fund(data) for data in valid_entities.values())
    metric_rows = _fund_metric_rows if uses_fund_metrics else _stock_metric_rows
    metric_names: list[str] = []
    values_by_entity: dict[str, dict[str, str]] = {}

    for entity in entities:
        data = comparison.get(entity, {})
        values_by_entity[entity] = {}
        if _is_unavailable_entity(data):
            continue
        for metric, value in metric_rows(data):
            if metric not in metric_names:
                metric_names.append(metric)
            values_by_entity[entity][metric] = value

    if not metric_names:
        metric_names = ["Status"]

    rows = []
    for metric in metric_names:
        row = [metric]
        for entity in entities:
            row.append(values_by_entity.get(entity, {}).get(metric, DATA_UNAVAILABLE))
        rows.append(row)

    rows.append(["Data Status", *[
        DATA_UNAVAILABLE if _is_unavailable_entity(comparison.get(entity)) else "Available"
        for entity in entities
    ]])

    return ["Metric", *entities], rows, notes

def _data_table_markdown(intent: str, quant_data: Any, screening_results: list | None = None) -> tuple[str, list[str]]:
    notes: list[str] = []
    if intent == "screen":
        rows = []
        for item in screening_results or []:
            rows.append([
                _safe_value(item.get("symbol")),
                _safe_value(item.get("name")),
                _format_price(item.get("price")),
                _safe_value(item.get("pe_ratio")),
                _safe_value(item.get("rsi")),
            ])
        return _markdown_table(["Symbol", "Name", "Price", "P/E", "RSI"], rows or [["N/A", "N/A", "N/A", "N/A", "N/A"]]), notes

    if isinstance(quant_data, dict) and "comparison" in quant_data:
        headers, rows, notes = _comparison_rows(quant_data.get("comparison") or {})
        return _markdown_table(headers, rows), notes

    if isinstance(quant_data, dict) and quant_data.get("error"):
        return _markdown_table(["Metric", "Value"], [["Status", DATA_UNAVAILABLE], ["Reason", _safe_value(quant_data.get("error"))]]), notes

    if isinstance(quant_data, dict) and quant_data:
        rows = _fund_metric_rows(quant_data) if _looks_like_fund(quant_data) else _stock_metric_rows(quant_data)
        return _markdown_table(["Metric", "Value"], [[metric, value] for metric, value in rows]), notes

    return _markdown_table(["Metric", "Value"], [["Status", DATA_UNAVAILABLE]]), notes

def _news_markdown(news_data: list) -> str:
    if not news_data:
        return "- No recent news found from configured sources."

    def _safe_http_url(value: Any) -> str | None:
        if _is_missing(value):
            return None
        text = str(value).strip()
        if text.lower().startswith("http://") or text.lower().startswith("https://"):
            return text
        return None

    def _headline_takeaway(title: str) -> str:
        headline = (title or "").lower()
        if any(token in headline for token in ["inflow", "aum", "corpus", "assets"]):
            return "Takeaway: This reflects fund size and recent money movement, not guaranteed future return."
        if any(token in headline for token in ["vs", "compare", "really the same", "same?"]):
            return "Takeaway: Use this to compare portfolio style and risk profile before judging returns."
        if any(token in headline for token in ["stocks held", "holdings", "portfolio"]):
            return "Takeaway: Common holdings can increase overlap risk; diversify if both funds own similar top positions."
        if any(token in headline for token in ["best mutual funds", "top", "rank"]):
            return "Takeaway: Rankings are opinion-led; validate with 3Y/5Y returns, drawdown, expense ratio, and AUM trend."
        return "Takeaway: Treat this as context only and cross-check with current NAV trend and risk metrics."

    rows = []
    for item in news_data[:6]:
        sentiment = f"**[{item.get('sentiment')}]** " if item.get("sentiment") else ""
        published = _safe_value(item.get("published"))
        source = _safe_value(item.get("source"))
        title = _safe_value(item.get("title"))
        takeaway = _headline_takeaway(title)
        url = _safe_http_url(item.get("url"))
        source_label = source if source != "N/A" else "Source"
        quoted = f"Quoted headline: \"{title}\"."
        source_line = f"([{source_label}]({url}))" if url else f"(Source: {source_label})"
        rows.append(f"- {sentiment}{published} {takeaway} {quoted} {source_line}")
    return "\n".join(rows) if rows else "- No recent news found from configured sources."

def _sanitize_research_text(text: str) -> str:
    sanitized = text or ""
    for bad, replacement in ADVICE_REPLACEMENTS.items():
        pattern = rf"\b{re.escape(bad)}\b"
        sanitized = re.sub(pattern, replacement, sanitized, flags=re.IGNORECASE)
    return sanitized

def _summary_subject(query: str, intent_info: dict, quant_data: Any) -> str:
    if isinstance(quant_data, dict) and "comparison" in quant_data:
        return " vs ".join(quant_data["comparison"].keys())
    ticker = intent_info.get("ticker")
    return ticker or query

def _snapshot_line(intent: str, quant_data: Any) -> str:
    if isinstance(quant_data, dict) and "comparison" in quant_data:
        available = sum(1 for item in quant_data["comparison"].values() if not _is_unavailable_entity(item))
        total = len(quant_data["comparison"])
        return f"{available} of {total} requested entities have structured FundersAI data."
    if isinstance(quant_data, dict) and quant_data.get("price"):
        return f"Latest structured price is {_format_price(quant_data.get('price'))} with {_format_percent(quant_data.get('change_pct'))} change."
    if isinstance(quant_data, dict) and quant_data.get("nav"):
        return f"Latest structured NAV is {_format_price(quant_data.get('nav'))}."
    return "Structured data is limited for this query."


def _compare_direct_answer_markdown(quant_data: Any) -> str:
    if not isinstance(quant_data, dict):
        return ""
    comparison = quant_data.get("comparison")
    if not isinstance(comparison, dict) or len(comparison) < 2:
        return ""

    why_better = quant_data.get("why_better") if isinstance(quant_data.get("why_better"), dict) else {}
    winner = why_better.get("winner") if isinstance(why_better.get("winner"), dict) else {}
    confidence = why_better.get("confidence") if isinstance(why_better.get("confidence"), dict) else {}
    winner_name = winner.get("entity_name")
    winner_status = winner.get("status")

    if winner_status == "winner" and winner_name:
        overall = f"{winner_name} ranks higher on the selected deterministic factors."
    elif winner_status == "tie":
        overall = "No clear overall edge based on currently available factors."
    else:
        overall = "Insufficient local data for a reliable overall winner."

    confidence_label = _safe_value(confidence.get("label"))
    confidence_score = confidence.get("score")
    if isinstance(confidence_score, (int, float)):
        confidence_text = f"{confidence_label} ({float(confidence_score):.2f})"
    else:
        confidence_text = confidence_label

    lines = [
        f"- Overall: {overall}",
        f"- Confidence: {confidence_text}",
    ]

    for factor in why_better.get("factor_results") or []:
        if not isinstance(factor, dict):
            continue
        factor_name = _safe_value(factor.get("factor"))
        factor_winner = _safe_value(factor.get("winner")) if factor.get("winner") else "No clear edge"
        coverage_raw = factor.get("coverage")
        coverage_pct = None
        if isinstance(coverage_raw, (int, float)):
            coverage_pct = round(float(coverage_raw) * 100)
        coverage_text = f"{coverage_pct}%" if coverage_pct is not None else "N/A"
        lines.append(f"- {factor_name}: {factor_winner} (coverage: {coverage_text})")

    limitations = why_better.get("data_limitations") if isinstance(why_better.get("data_limitations"), list) else []
    if limitations:
        lines.append(f"- Data limitations: {'; '.join(str(item) for item in limitations[:3])}")

    return "\n".join(lines)

def _comparison_valid_items(comparison: Any) -> list[tuple[str, dict[str, Any]]]:
    if not isinstance(comparison, dict):
        return []
    return [
        (name, data)
        for name, data in comparison.items()
        if isinstance(data, dict) and not _is_unavailable_entity(data)
    ]

def _metric_label_winner(valid: list[tuple[str, dict[str, Any]]], key: str, lower_is_better: bool = False) -> tuple[str, str] | None:
    if len(valid) < 2:
        return None
    values = []
    for name, data in valid[:2]:
        value = _to_float_or_none(data.get(key))
        if value is not None:
            values.append((name, value))
    if len(values) < 2 or values[0][1] == values[1][1]:
        return None
    winner = min(values, key=lambda item: item[1]) if lower_is_better else max(values, key=lambda item: item[1])
    loser = values[1] if winner == values[0] else values[0]
    diff = abs(winner[1] - loser[1])
    return winner[0], f"{winner[0]} leads by {diff:.2f} pts ({_format_percent(winner[1])} vs {_format_percent(loser[1])})."

def _build_comparison_summary(quant_data: Any) -> dict[str, Any]:
    comparison = quant_data.get("comparison") if isinstance(quant_data, dict) else None
    valid = _comparison_valid_items(comparison)
    if len(valid) < 2:
        return {
            "headline": "Structured comparison is limited because one or more funds could not be matched.",
            "verdict_cards": [],
            "key_differences": ["Data coverage is insufficient for a decisive research snapshot."],
            "missing_data": [],
        }

    (name_a, data_a), (name_b, data_b) = valid[:2]
    return_winner = _metric_label_winner(valid, "return_3y")
    risk_winner = _metric_label_winner(valid, "volatility_1y", lower_is_better=True)
    cost_winner = _metric_label_winner(valid, "expense_ratio", lower_is_better=True)
    drawdown_winner = _metric_label_winner(valid, "max_drawdown_1y")

    if return_winner:
        headline = f"{return_winner[0]} has the stronger available 3Y return, but risk, cost, and data coverage should be read alongside it."
    else:
        headline = "No clear return leader is available from the current structured data."

    def _card(label: str, winner: tuple[str, str] | None, fallback: str) -> dict[str, str]:
        return {
            "label": label,
            "value": winner[0] if winner else "No clear edge",
            "note": winner[1] if winner else fallback,
        }

    missing_data = []
    for name, data in valid[:2]:
        missing = [
            label
            for label, key in (
                ("1Y return", "return_1y"),
                ("3Y return", "return_3y"),
                ("5Y return", "return_5y"),
                ("expense ratio", "expense_ratio"),
                ("AUM", "aum"),
                ("volatility", "volatility_1y"),
                ("drawdown", "max_drawdown_1y"),
                ("Sharpe", "sharpe_ratio"),
            )
            if _is_missing(data.get(key))
        ]
        if missing:
            missing_data.append({"entity": name, "fields": missing})

    key_differences = []
    for item in (return_winner, risk_winner, cost_winner, drawdown_winner):
        if item:
            key_differences.append(item[1])
    if not key_differences:
        key_differences.append("Current structured metrics do not show a strong deterministic edge.")

    return {
        "headline": headline,
        "verdict_cards": [
            _card("Return profile", return_winner, "3Y return is missing or too close to call."),
            _card("Risk profile", risk_winner, "Volatility is missing or too close to call."),
            _card("Cost profile", cost_winner, "Expense ratio is missing or too close to call."),
            {
                "label": "Data quality",
                "value": "Complete" if not missing_data else "Partial",
                "note": "Core comparison fields are available." if not missing_data else "Some fields are missing; use the data notes before reading the verdict.",
            },
        ],
        "key_differences": key_differences[:5],
        "missing_data": missing_data,
    }

def _holding_key(row: dict[str, Any]) -> str | None:
    isin = str(row.get("isin") or "").strip().upper()
    if isin and isin not in {"N/A", "NA", "NONE", "NULL"}:
        return f"isin:{isin}"
    name = re.sub(r"[^a-z0-9]+", " ", str(row.get("security_name") or "").lower()).strip()
    return f"name:{name}" if name else None

def _holding_weight(row: dict[str, Any]) -> float:
    return _to_float_or_none(row.get("weight_pct")) or 0.0

def _build_holdings_overlap(comparison: Any) -> dict[str, Any]:
    valid = _comparison_valid_items(comparison)
    if len(valid) < 2:
        return {"coverage_status": "unavailable", "reason": "Need two matched funds for holdings overlap."}

    (name_a, data_a), (name_b, data_b) = valid[:2]
    holdings_a = data_a.get("holdings") if isinstance(data_a.get("holdings"), list) else []
    holdings_b = data_b.get("holdings") if isinstance(data_b.get("holdings"), list) else []
    if not holdings_a or not holdings_b:
        return {
            "coverage_status": "unavailable",
            "reason": "Holdings data is unavailable for one or both funds.",
            "entities": [name_a, name_b],
            "common_holdings": [],
            "top_common_holdings": [],
            "total_overlap_weight": 0,
        }

    map_a = {_holding_key(row): row for row in holdings_a if isinstance(row, dict) and _holding_key(row)}
    map_b = {_holding_key(row): row for row in holdings_b if isinstance(row, dict) and _holding_key(row)}
    common = []
    for key in sorted(set(map_a).intersection(map_b)):
        row_a = map_a[key]
        row_b = map_b[key]
        weight_a = _holding_weight(row_a)
        weight_b = _holding_weight(row_b)
        common.append({
            "name": row_a.get("security_name") or row_b.get("security_name") or "N/A",
            "isin": row_a.get("isin") or row_b.get("isin"),
            "sector": row_a.get("sector") or row_b.get("sector"),
            "weight_a": round(weight_a, 4),
            "weight_b": round(weight_b, 4),
            "overlap_weight": round(min(weight_a, weight_b), 4),
        })
    common.sort(key=lambda row: row["overlap_weight"], reverse=True)

    def _top_concentration(rows: list[dict[str, Any]], limit: int = 10) -> float:
        weights = sorted((_holding_weight(row) for row in rows if isinstance(row, dict)), reverse=True)
        return round(sum(weights[:limit]), 4)

    def _sector_map(rows: list[dict[str, Any]]) -> dict[str, float]:
        sectors: dict[str, float] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            sector = str(row.get("sector") or "Unclassified").strip() or "Unclassified"
            sectors[sector] = sectors.get(sector, 0.0) + _holding_weight(row)
        return sectors

    sectors_a = _sector_map(holdings_a)
    sectors_b = _sector_map(holdings_b)
    sector_overlap = [
        {
            "sector": sector,
            "weight_a": round(sectors_a.get(sector, 0.0), 4),
            "weight_b": round(sectors_b.get(sector, 0.0), 4),
            "overlap_weight": round(min(sectors_a.get(sector, 0.0), sectors_b.get(sector, 0.0)), 4),
        }
        for sector in sorted(set(sectors_a).intersection(sectors_b))
    ]
    sector_overlap.sort(key=lambda row: row["overlap_weight"], reverse=True)

    dates = [
        row.get("as_of_date")
        for row in [*(holdings_a[:1] or []), *(holdings_b[:1] or [])]
        if isinstance(row, dict) and row.get("as_of_date")
    ]

    return {
        "coverage_status": "available",
        "entities": [name_a, name_b],
        "as_of_date": " / ".join(str(date) for date in dates) if dates else None,
        "common_holding_count": len(common),
        "total_overlap_weight": round(sum(row["overlap_weight"] for row in common), 4),
        "fund_a_top_concentration": _top_concentration(holdings_a),
        "fund_b_top_concentration": _top_concentration(holdings_b),
        "common_holdings": common,
        "top_common_holdings": common[:10],
        "sector_overlap": sector_overlap[:10],
    }

def _comparison_summary_markdown(summary: Any) -> str:
    if not isinstance(summary, dict):
        return ""
    lines = []
    headline = summary.get("headline")
    if headline:
        lines.append(str(headline))
    cards = summary.get("verdict_cards")
    if isinstance(cards, list) and cards:
        lines.append("")
        for card in cards[:4]:
            if not isinstance(card, dict):
                continue
            lines.append(f"- **{_safe_value(card.get('label'))}:** {_safe_value(card.get('value'))} — {_safe_value(card.get('note'))}")
    differences = summary.get("key_differences")
    if isinstance(differences, list) and differences:
        lines.append("")
        lines.extend([f"- {item}" for item in differences[:5]])
    return "\n".join(lines).strip()

def _comparison_followup_answer_markdown(quant_data: Any, question: str | None) -> str:
    if not question or not isinstance(quant_data, dict):
        return ""
    comparison = quant_data.get("comparison")
    if not isinstance(comparison, dict) or len(comparison) < 2:
        return ""

    valid = [(name, data) for name, data in comparison.items() if isinstance(data, dict) and not _is_unavailable_entity(data)]
    if len(valid) < 2:
        return ""

    (name_a, data_a), (name_b, data_b) = valid[:2]
    low = question.lower()
    lines: list[str] = []

    def _metric_pair(label: str, key: str, formatter=_safe_value) -> str | None:
        a_val = data_a.get(key)
        b_val = data_b.get(key)
        if _is_missing(a_val) and _is_missing(b_val):
            return None
        return f"{label}: {name_a} {formatter(a_val)} vs {name_b} {formatter(b_val)}"

    if any(token in low for token in ("return", "returns", "differ", "difference", "performance")):
        for label, key in (("1Y return", "return_1y"), ("3Y return", "return_3y"), ("5Y return", "return_5y")):
            line = _metric_pair(label, key, _format_percent)
            if line:
                lines.append(f"- {line}.")
        lines.append(
            "- Return gaps usually come from different portfolio composition, category exposure, cash levels, stock selection, and how much volatility each fund took during the same period."
        )

    if any(token in low for token in ("risk", "safer", "steadier", "drawdown", "volatility", "sharpe")):
        for label, key, formatter in (
            ("Volatility", "volatility_1y", _format_percent),
            ("Max drawdown", "max_drawdown_1y", _format_percent),
            ("Sharpe ratio", "sharpe_ratio", _safe_value),
        ):
            line = _metric_pair(label, key, formatter)
            if line:
                lines.append(f"- {line}.")

    if any(token in low for token in ("expense", "cost", "aum", "size")):
        for label, key, formatter in (
            ("Expense ratio", "expense_ratio", _safe_value),
            ("AUM", "aum", _format_inr_market_cap),
        ):
            line = _metric_pair(label, key, formatter)
            if line:
                lines.append(f"- {line}.")

    overlap = quant_data.get("holdings_overlap") if isinstance(quant_data.get("holdings_overlap"), dict) else {}
    if any(token in low for token in ("holding", "holdings", "overlap", "same stocks", "common stocks")):
        if overlap.get("coverage_status") == "available":
            lines.append(f"- Holdings overlap weight is {_format_percent(overlap.get('total_overlap_weight'))} across {overlap.get('common_holding_count', 0)} common holdings.")
            for item in (overlap.get("top_common_holdings") or [])[:3]:
                if isinstance(item, dict):
                    lines.append(f"- Common holding: {_safe_value(item.get('name'))} with overlap {_format_percent(item.get('overlap_weight'))}.")
        else:
            lines.append(f"- Holdings overlap is unavailable: {_safe_value(overlap.get('reason'))}.")

    if any(token in low for token in ("sector", "allocation", "portfolio mix")):
        if overlap.get("coverage_status") == "available" and overlap.get("sector_overlap"):
            for item in (overlap.get("sector_overlap") or [])[:3]:
                if isinstance(item, dict):
                    lines.append(f"- Sector overlap: {_safe_value(item.get('sector'))} at {_format_percent(item.get('overlap_weight'))}.")
        else:
            lines.append("- Sector overlap needs holdings-level sector data for both funds.")

    if not lines:
        lines.append(
            "- The useful comparison points are returns, volatility, drawdown, Sharpe ratio, expense ratio, AUM, and portfolio/sector exposure where available."
        )

    return "\n".join(lines[:7])

async def run_stock_screen(filters: dict) -> list:
    """Stock screening against the local stock universe."""
    if not supabase:
        logger.error("Supabase client not initialized")
        return []

    try:
        query = supabase.table('nifty_stocks').select('*')
        
        min_pe = filters.get("min_pe")
        max_pe = filters.get("max_pe")
        if min_pe is not None: query = query.gte('pe_ratio', min_pe)
        if max_pe is not None: query = query.lte('pe_ratio', max_pe)
            
        rsi_range = filters.get("rsi_range", {})
        rsi_min = rsi_range.get("min")
        rsi_max = rsi_range.get("max")
        if rsi_min is not None: query = query.gte('rsi', rsi_min)
        if rsi_max is not None: query = query.lte('rsi', rsi_max)
            
        category = filters.get("category")
        if category: query = query.eq('category', category)
            
        res = query.execute()
        raw_results = res.data
        
        formatted_results = []
        for r in raw_results:
            formatted_results.append({
                "Symbol": r["symbol"],
                "Category": r.get("category", "N/A"),
                "RSI": round(r["rsi"], 2) if r.get("rsi") is not None else "N/A",
                "P/E": round(r["pe_ratio"], 2) if r.get("pe_ratio") is not None else "N/A",
                "Recommendation": r.get("recommendation", "N/A")
            })
        return formatted_results
    except Exception as e:
        logger.error(f"Stock screening DB error: {e}")
        return []

async def synthesis_response(
    query: str,
    intent_info: dict,
    quant_data: Any,
    news_data: list,
    screening_results: list = None,
    research_depth: str = "standard",
    explanation_mode: str | None = None,
    comparison_view_mode: str = "canvas",
    usage_collector: list[dict[str, Any]] | None = None,
) -> str:
    """Synthesis Core"""
    
    intent = intent_info.get("intent")
    deep_research = explanation_mode == "advanced" or research_depth == "deep"
    beginner_mode = explanation_mode == "beginner" or (explanation_mode is None and not deep_research)
    
    if intent == "general":
        system_prompt_gen = """You are FundersAI, an expert AI stock market research assistant and financial educator.
If the user asks basic educational questions (e.g., 'What is PE ratio?', 'Explain the metrics used here'), provide a clear, comprehensive, and beginner-friendly explanation. 
Break down metrics like P/E Ratio (valuation), RSI (momentum/overbought/oversold), and moving averages carefully. Use bullet points and analogies if helpful. 
Do NOT be overly brief when explaining concepts. Provide deep value to the user.
NEVER give direct financial advice to buy or sell a specific stock."""
        if beginner_mode:
            system_prompt_gen = """You are FundersAI, a research-only Indian market explainer.
Use plain English and define financial terms briefly.
Keep the same facts, avoid jargon, and never give buy/sell/invest advice.
Include a short "Terms in plain English" section when financial terms appear."""
        if deep_research:
            system_prompt_gen = """You are FundersAI, an expert AI stock market research assistant and financial educator.
Answer as a deep research explainer with this structure:
1) Concept Breakdown
2) Why It Matters in Indian markets
3) How to Read It with other metrics
4) Red Flags and Common Mistakes
5) Research Checklist
Use clear language, practical examples, and no buy/sell advice."""
        messages = [
            {"role": "system", "content": system_prompt_gen},
            {"role": "user", "content": query}
        ]
        return await function_ollama_chat(messages, format="text", usage_collector=usage_collector)

    table_markdown, data_notes = _data_table_markdown(intent, quant_data, screening_results)
    news_markdown = _news_markdown(news_data)
    subject = _summary_subject(query, intent_info, quant_data)
    snapshot = _snapshot_line(intent, quant_data)
    compare_direct_answer = _compare_direct_answer_markdown(quant_data) if intent == "compare" else ""
    followup_answer = _comparison_followup_answer_markdown(quant_data, intent_info.get("followup_question")) if intent == "compare" else ""
    comparison_summary = _comparison_summary_markdown(quant_data.get("comparison_summary")) if intent == "compare" and isinstance(quant_data, dict) else ""

    system_prompt = """You are FundersAI, a research-only Indian market analyst.
Write only the Trend Observation paragraph.
Use the provided structured facts only. Do not add new numbers.
Use neutral research language. Do not use advice words or phrases like buy, sell, invest, avoid, investors should, attractive option, or long-term investment.
If data is unavailable for an entity, mention that the comparison is limited by missing data.
Keep it to 3-5 concise sentences."""
    if beginner_mode:
        system_prompt = """You are FundersAI, a research-only Indian market explainer.
Use only the provided structured facts. Do not add new numbers.
Use plain English, short sentences, and define any financial term in one line.
Do not use advice words or phrases like buy, sell, invest, avoid, investors should, attractive option, or long-term investment.
Keep it concise and mention missing or stale data when relevant."""
    if deep_research:
        system_prompt = """You are FundersAI, a research-only Indian market analyst.
Create a deep research note using only the provided facts, with exactly these markdown sections:
### Executive Summary
### What the Data Shows
### Bull vs Bear Case
### Risks and Missing Data
### Research Checklist
Rules:
- No buy/sell/invest advice.
- Do not invent numbers.
- If data is missing, state it clearly.
- Keep each section concise and factual."""
    
    notes_context = "\n".join([f"- {note}" for note in data_notes]) if data_notes else "- None"
    context = f"""
User Query: {query}
Identified Intent: {intent}
Identified Ticker: {intent_info.get('ticker')}

Structured Data Table:
{table_markdown}

Data Notes:
{notes_context}

Controlled Web Context:
{news_markdown}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context}
    ]
    
    trend = await function_ollama_chat(messages, format="text", usage_collector=usage_collector)
    if not trend:
        if deep_research:
            trend = """### Executive Summary
- Structured metrics and recent news are available but should be treated as research context, not advice.

### What the Data Shows
- The table highlights current valuation, profitability, momentum, and recent performance where available.

### Bull vs Bear Case
- Bull case depends on consistency in reported growth and price strength.
- Bear case depends on weak/partial data, stale inputs, or negative news flow.

### Risks and Missing Data
- Missing values, stale records, and provider limits reduce confidence.

### Research Checklist
- Validate latest filings and earnings commentary.
- Check trend durability across longer periods."""
        else:
            trend = "The structured data above should be read as market context, not as a recommendation. Metrics can be useful for comparison, but missing values and source freshness limit the strength of any conclusion. Use the available figures as a starting point for independent research."
    trend = _sanitize_research_text(trend.strip())

    notes_markdown = ""
    if data_notes:
        notes_markdown = "\n\n### Data Notes\n" + "\n".join([f"- {note}" for note in data_notes])
    glossary_markdown = ""
    if beginner_mode:
        glossary_markdown = "\n\n### Terms in Plain English\n- Sharpe ratio: return earned for each unit of risk.\n- Drawdown: how far the value fell from a recent high.\n- Beta: how much the asset tends to move compared with the market.\n- Expense ratio: the yearly fund cost charged as a percentage.\n- Debt/equity: how much debt a company carries compared with shareholder capital."

    title = "Deep Research Snapshot" if deep_research else "Snapshot"
    analysis_heading = "Deep Research Analysis" if deep_research else "Trend Observation"

    if intent == "compare" and comparison_view_mode == "canvas":
        long_term_read = compare_direct_answer or (
            "Use the canvas metrics to compare long-term returns, volatility, drawdown, Sharpe ratio, expense ratio, AUM, and data freshness side by side. A stronger long-term fit should show consistent returns with controlled downside and reasonable costs, not only a higher point-to-point return."
        )
        return f"""### {subject} — {title}
> Detailed comparison metrics are visible in the canvas panel.

### Long-Term Read
{long_term_read}
{chr(10) + chr(10) + "### Comparison Snapshot" + chr(10) + comparison_summary if comparison_summary else ""}
{chr(10) + chr(10) + "### Follow-up Answer" + chr(10) + followup_answer if followup_answer else ""}

### News & Announcements *(last 48-72 hrs)*
{news_markdown}

### {analysis_heading}

{trend}
{glossary_markdown}

### Follow-up Questions
- Compare downside protection and max drawdown.
- Show expense ratio and AUM differences.
- Explain which fund looks steadier over 3Y and 5Y.

{DISCLAIMER}"""

    return f"""### {subject} — {title}
> {snapshot}
{chr(10) + chr(10) + "### How They Differ" + chr(10) + compare_direct_answer if compare_direct_answer else ""}

### Data Table
{table_markdown}{notes_markdown}

### News & Announcements *(last 48-72 hrs)*
{news_markdown}

### {analysis_heading}

{trend}
{glossary_markdown}

{DISCLAIMER}"""

@app.get("/api/trigger-fetch")
async def trigger_eod_fetch(background_tasks: BackgroundTasks):
    """Trigger background EOD fetching process via cron tool"""
    background_tasks.add_task(run_eod_fetch)
    return {"message": "Background fetch process triggered successfully."}

async def get_mf_history_df(scheme_code: int, days: int = 1100):
    """Fetch MF history from Supabase (or fallback) and return as a DataFrame compatible with risk functions."""
    from app.services.fund_service import FundService
    import asyncio
    return await asyncio.to_thread(FundService.get_mf_history_df, scheme_code, days)

async def get_nifty_history_df(days: int = 1100):
    """Fetch NIFTY history from normalized stock price history."""
    if not supabase:
        return pd.DataFrame()
    import asyncio
    try:
        def _fetch_nifty():
            return supabase.table('stock_prices_daily').select('close, date').eq('symbol', 'NIFTY').order('date', desc=True).limit(days).execute()
        res = await asyncio.to_thread(_fetch_nifty)
        if res.data:
            df = pd.DataFrame(res.data)
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            df.rename(columns={'close': 'Close'}, inplace=True)
            df.set_index('date', inplace=True)
            return _normalize_price_df_index(df)
    except Exception as e:
        logger.error(f"Failed to fetch local NIFTY history: {e}")
    return pd.DataFrame()

def _normalize_fund_text(text: str) -> str:
    return " ".join(
        text.lower()
        .replace("smallcap", "small cap")
        .replace("midcap", "mid cap")
        .replace("largecap", "large cap")
        .replace("bluechip", "blue chip")
        .replace("-", " ")
        .split()
    )

def _coerce_scheme_code_filter(scheme_code_value: Any):
    if scheme_code_value in (None, ""):
        return None
    scheme_code_str = str(scheme_code_value).strip()
    if not scheme_code_str:
        return None
    return int(scheme_code_str) if scheme_code_str.isdigit() else scheme_code_str

def _nav_history_summary_for_scheme(scheme_code_value: Any, cache: dict[str, dict[str, Any]] | None = None) -> dict[str, Any]:
    key = str(scheme_code_value or "").strip()
    default_summary = {
        "count": 0,
        "first_nav_date": None,
        "last_nav_date": None,
    }
    if not key:
        return default_summary
    if cache is not None and key in cache:
        return cache[key]

    code_filter = _coerce_scheme_code_filter(scheme_code_value)
    if code_filter is None or not supabase:
        if cache is not None:
            cache[key] = default_summary
        return default_summary

    summary = dict(default_summary)
    try:
        count_res = (
            supabase.table("mutual_fund_nav_history")
            .select("nav_date", count="exact")
            .eq("scheme_code", code_filter)
            .execute()
        )
        summary["count"] = int(count_res.count or 0)

        first_res = (
            supabase.table("mutual_fund_nav_history")
            .select("nav_date")
            .eq("scheme_code", code_filter)
            .order("nav_date", desc=False)
            .limit(1)
            .execute()
        )
        last_res = (
            supabase.table("mutual_fund_nav_history")
            .select("nav_date")
            .eq("scheme_code", code_filter)
            .order("nav_date", desc=True)
            .limit(1)
            .execute()
        )
        first_row = (first_res.data or [None])[0]
        last_row = (last_res.data or [None])[0]
        summary["first_nav_date"] = first_row.get("nav_date") if isinstance(first_row, dict) else None
        summary["last_nav_date"] = last_row.get("nav_date") if isinstance(last_row, dict) else None
    except Exception as exc:
        if DEBUG_MF_RESOLUTION:
            logger.warning("MF nav history summary lookup failed for %s: %s", key, exc)

    if cache is not None:
        cache[key] = summary
    return summary

def _history_coverage_from_df(df: pd.DataFrame) -> dict[str, Any]:
    if df.empty:
        return {
            "history_points": 0,
            "first_nav_date": None,
            "last_nav_date": None,
            "supports": {"1Y": False, "3Y": False, "5Y": False},
        }
    ordered = df.sort_index()
    first_dt = ordered.index[0]
    last_dt = ordered.index[-1]
    span_days = max(int((last_dt - first_dt).days), 0)
    return {
        "history_points": int(len(ordered)),
        "first_nav_date": first_dt.strftime("%Y-%m-%d"),
        "last_nav_date": last_dt.strftime("%Y-%m-%d"),
        "supports": {
            "1Y": span_days >= 365,
            "3Y": span_days >= 365 * 3,
            "5Y": span_days >= 365 * 5,
        },
    }

def _pick_best_fund_match(
    entity: str,
    rows: list[dict],
    nav_history_cache: dict[str, dict[str, Any]] | None = None,
    min_history_points: int = 0,
) -> dict | None:
    scored_rows = _score_fund_candidates(
        entity,
        rows,
        nav_history_cache=nav_history_cache,
        min_history_points=min_history_points,
    )
    return scored_rows[0]["row"] if scored_rows else None


def _score_fund_candidates(
    entity: str,
    rows: list[dict],
    nav_history_cache: dict[str, dict[str, Any]] | None = None,
    min_history_points: int = 0,
) -> list[dict[str, Any]]:
    if not rows:
        return []

    entity_norm = _normalize_fund_text(entity.replace(" fund", "").replace(" growth", ""))
    entity_words = [w for w in entity_norm.split() if len(w) > 2]
    wants_passive = "passive" in entity_norm
    wants_fof = "fund of funds" in entity_norm or "fof" in entity_norm
    wants_multi_asset = "multi asset" in entity_norm
    wants_direct = "direct" in entity_norm
    wants_regular = "regular" in entity_norm

    scored_rows: list[dict[str, Any]] = []
    for row in rows:
        notes: list[str] = []
        name_norm = _normalize_fund_text(row.get("scheme_name", ""))
        value = 0
        if entity_norm and entity_norm in name_norm:
            value += 100
            notes.append("name_contains_full_query:+100")
        overlap_hits = sum(1 for word in entity_words if word in name_norm)
        if overlap_hits:
            value += overlap_hits * 100
            notes.append(f"token_overlap:+{overlap_hits * 100}")
        # Always prefer Direct Growth siblings for AMC-derived fields.
        if "direct" in name_norm:
            value += 30
            notes.append("direct_bonus:+30")
        else:
            value -= 20
            notes.append("direct_missing_penalty:-20")
        if "growth" in name_norm:
            value += 20
            notes.append("growth_bonus:+20")
        if "regular" in name_norm:
            value -= 35
            notes.append("regular_penalty:-35")
        if "idcw" in name_norm or "dividend" in name_norm:
            value -= 25
            notes.append("idcw_dividend_penalty:-25")
        if "index" in name_norm and "index" not in entity_norm:
            value -= 35
            notes.append("index_mismatch_penalty:-35")
        if "etf" in name_norm and "etf" not in entity_norm:
            value -= 35
            notes.append("etf_mismatch_penalty:-35")
        if "institutional" in name_norm and "institutional" not in entity_norm:
            value -= 20
            notes.append("institutional_penalty:-20")
        if "passive" in name_norm and not wants_passive:
            value -= 80
            notes.append("passive_mismatch_penalty:-80")
        if "fund of funds" in name_norm and not wants_fof:
            value -= 70
            notes.append("fof_mismatch_penalty:-70")
        if "multi asset" in name_norm and not wants_multi_asset:
            value -= 80
            notes.append("multi_asset_mismatch_penalty:-80")
        if wants_direct and "regular" in name_norm:
            value -= 60
            notes.append("direct_requested_regular_penalty:-60")
        if wants_regular and "direct" in name_norm:
            value -= 60
            notes.append("regular_requested_direct_penalty:-60")
        if wants_multi_asset and "multi asset" in name_norm:
            value += 20
            notes.append("multi_asset_match_bonus:+20")
        if wants_multi_asset and "fund of funds" in name_norm and not wants_fof:
            value -= 30
            notes.append("multi_asset_fof_penalty:-30")

        history = _nav_history_summary_for_scheme(row.get("scheme_code"), nav_history_cache)
        history_points = int(history.get("count") or 0)
        if history_points == 0:
            value -= 30
            notes.append("no_nav_history_penalty:-30")
        else:
            history_bonus = min(history_points // 200, 30)
            value += history_bonus
            notes.append(f"history_bonus:+{history_bonus}")
        if min_history_points > 0 and history_points < min_history_points:
            value -= 120
            notes.append(f"min_history_penalty:-120(required={min_history_points})")

        scored_rows.append(
            {
                "score": value,
                "history_points": history_points,
                "row": row,
                "notes": notes,
                "history_summary": history,
            }
        )

    scored_rows.sort(key=lambda item: item["score"], reverse=True)
    if DEBUG_MF_RESOLUTION:
        logger.info(
            "MF resolver entity='%s' min_history=%s top_candidates=%s",
            entity,
            min_history_points,
            [
                {
                    "scheme_code": str(item["row"].get("scheme_code")),
                    "scheme_name": item["row"].get("scheme_name"),
                    "score": item["score"],
                    "history_points": item["history_points"],
                }
                for item in scored_rows[:5]
            ],
        )
    return scored_rows


def _supports_from_history_summary(summary: dict[str, Any]) -> dict[str, bool]:
    first_nav = _to_utc_datetime(summary.get("first_nav_date"))
    last_nav = _to_utc_datetime(summary.get("last_nav_date"))
    if not first_nav or not last_nav:
        return {"1Y": False, "3Y": False, "5Y": False}
    span_days = max(int((last_nav - first_nav).days), 0)
    return {
        "1Y": span_days >= 365,
        "3Y": span_days >= 365 * 3,
        "5Y": span_days >= 365 * 5,
    }


def _resolver_horizon_to_min_points(horizon: str) -> int:
    lookup = {
        "1Y": 252,
        "3Y": 252 * 3,
        "5Y": 252 * 5,
    }
    return lookup.get(str(horizon or "").upper(), MF_COMPARE_MIN_NAV_POINTS)

def _compute_cagr_from_close(close_series: pd.Series, years: int) -> float | None:
    if close_series.empty:
        return None
    current_date = close_series.index[-1]
    target_date = current_date - pd.DateOffset(years=years)
    historical = close_series[close_series.index <= target_date]
    if historical.empty:
        return None
    current_val = float(close_series.iloc[-1])
    past_val = float(historical.iloc[-1])
    if past_val <= 0:
        return None
    cagr = (current_val / past_val) ** (1 / years) - 1
    return round(cagr * 100, 2)

def _compute_nav_risk_metrics(close_series: pd.Series, risk_free_rate: float = 0.06):
    close_series = close_series.astype(float).dropna()
    if len(close_series) < 2:
        return None

    returns = close_series.pct_change().dropna()
    if returns.empty:
        return None

    mean_daily = float(returns.mean())
    std_daily = float(returns.std(ddof=0))
    ann_std = std_daily * np.sqrt(252)
    ann_return = mean_daily * 252

    sharpe = None if ann_std == 0 else (ann_return - risk_free_rate) / ann_std
    downside = returns[returns < 0]
    downside_std = float(np.sqrt(np.mean(np.square(downside)))) * np.sqrt(252) if len(downside) > 0 else 0.0
    sortino = None if downside_std == 0 else (ann_return - risk_free_rate) / downside_std

    running_max = close_series.cummax()
    drawdown = (running_max - close_series) / running_max.replace(0, np.nan)
    max_drawdown = float(drawdown.max()) if not drawdown.empty else 0.0

    return {
        "stdDev": round(ann_std, 4),
        "sharpeRatio": round(sharpe, 2) if sharpe is not None else None,
        "sortinoRatio": round(sortino, 2) if sortino is not None else None,
        "maxDrawdown": round(max_drawdown, 4)
    }

@app.get("/api/quant/stocks/compare")
async def compare_stocks_quant(symbols: str = Query(..., min_length=1)):
    try:
        return build_stock_compare(symbols)
    except Exception as e:
        logger.error("Stock quant compare failed: %s", e)
        raise HTTPException(status_code=500, detail="Stock quant comparison failed")


@app.get("/api/quant/stocks/{symbol}/profile")
async def stock_quant_profile(symbol: str):
    try:
        return build_stock_profile(symbol)
    except Exception as e:
        logger.error("Stock profile failed for %s: %s", symbol, e)
        raise HTTPException(status_code=500, detail="Stock profile failed")


@app.get("/api/quant/stocks/{symbol}/financials")
async def stock_quant_financials(symbol: str):
    try:
        return get_stock_financials(symbol)
    except Exception as e:
        logger.error("Stock financials failed for %s: %s", symbol, e)
        raise HTTPException(status_code=500, detail="Stock financials failed")


@app.get("/api/quant/stocks/{symbol}/price-history")
async def stock_quant_price_history(symbol: str, days: int = Query(365, ge=1, le=5000)):
    try:
        return {"symbol": symbol.upper(), "price_history": get_stock_price_history(symbol, days=days)}
    except Exception as e:
        logger.error("Stock price history failed for %s: %s", symbol, e)
        raise HTTPException(status_code=500, detail="Stock price history failed")


@app.get("/api/mf/{scheme_code}")
async def get_mutual_fund_details(scheme_code: int):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")

    try:
        profile = FundService.get_mutual_fund_profile(scheme_code)
        if not profile:
            raise HTTPException(status_code=404, detail="Mutual fund not found")

        # Nifty fallback for alpha/beta
        nifty_hist = await get_nifty_history_df(days=2200)
        hist_df = FundService.get_mf_history_df(scheme_code, days=2200)

        risk_metrics = profile.risk_metrics.model_dump()
        if not hist_df.empty and not nifty_hist.empty:
            alpha_beta = calculate_alpha_beta_v2(hist_df, nifty_hist)
            if risk_metrics.get("beta") is None:
                risk_metrics["beta"] = alpha_beta.get("beta")
            if risk_metrics.get("alpha_vs_nifty") is None:
                risk_metrics["alpha_vs_nifty"] = alpha_beta.get("alpha")
            risk_metrics["risk_period"] = f"{alpha_beta.get('period_years', 3)}Y"

        history_coverage = _history_coverage_from_df(hist_df)
        details_dump = profile.details.model_dump()
        nav_ref = details_dump.get("launch_date") # Or whatever is available
        stale = profile.data_quality.is_stale
        
        return {
            "scheme_code": scheme_code,
            "details": details_dump,
            "returns": profile.returns.model_dump(by_alias=True),
            "riskMetrics": risk_metrics,
            "chartData": [pt.model_dump() for pt in profile.nav_history],
            "fullData": [pt.model_dump() for pt in profile.nav_history],
            "historyCoverage": history_coverage,
            "data_quality": profile.data_quality.model_dump(),
            "freshness": {
                "stale": stale,
                "warning": profile.data_quality.warning,
                "nav_date": profile.data_quality.last_nav_date,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to fetch MF details for {scheme_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_endpoint(
    req: ChatRequest,
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_tier: str | None = Header(default=None, alias="X-User-Tier"),
    x_internal_proxy_key: str | None = Header(default=None, alias="X-Internal-Proxy-Key"),
):
    trusted_proxy = _trusted_chat_proxy(x_internal_proxy_key)
    usage_collector: list[dict[str, Any]] | None = [] if trusted_proxy else None
    asset_type = req.asset_type
    deferred_response = _build_deferred_dashboard_response(req.query, req.history, req.conversation_context)
    if deferred_response:
        if trusted_proxy:
            deferred_response["_usage"] = _summarize_openrouter_usage(usage_collector)
        return deferred_response

    deterministic_compare = _deterministic_compare_intent(req.query, asset_type)
    followup_compare = None if deterministic_compare else _followup_compare_intent(
        req.query,
        req.history,
        asset_type,
        req.conversation_context,
    )

    dashboard_intent = _dashboard_tool_intent(req.query, asset_type)
    if dashboard_intent and not followup_compare:
        if dashboard_intent["intent"] == "sip_calculator":
            sip_response = _build_sip_calculator_response(req.query)
            if sip_response:
                if trusted_proxy:
                    sip_response["_usage"] = _summarize_openrouter_usage(usage_collector)
                return sip_response
        if dashboard_intent["intent"] == "category_search":
            category_response = _build_category_search_response(dashboard_intent)
            if trusted_proxy:
                category_response["_usage"] = _summarize_openrouter_usage(usage_collector)
            return category_response

    intent_info = deterministic_compare or followup_compare or await route_query(req.query, asset_type, usage_collector=usage_collector)
    intent = intent_info.get("intent", "general")
    ticker = intent_info.get("ticker")
    period = intent_info.get("historical_period", "1mo")
    sentiment = intent_info.get("sentiment_flag", False)
    
    # Restrict mutual fund queries to AMCs with active ingestion pipelines
    is_unsupported_mf = False
    query_lower = req.query.lower()
    supported_mf_keywords = ["parag", "ppfas", "icici", "hdfc", "sbi"]
    
    is_mf_context = (asset_type == "mutual_fund" or 
                     any(k in query_lower for k in ["fund", "mutual fund", "flexi cap", "small cap", "mid cap", "large cap", "elss", "nav", "amc", "sip", "portfolio"]))
    
    if is_mf_context and intent in ["compare", "quant", "both"]:
        unsupported_amc_keywords = [
            "quant", "nippon", "axis", "kotak", "mirae", "uti", "dsp", "tata", "motilal", 
            "canara", "groww", "zerodha", "bandhan", "idfc", "franklin", "edelweiss", "sundaram", "lic", 
            "pgim", "invesco", "hsbc", "union", "baroda", "bnp", "mahindra", "shriram", "whiteoak", 
            "samco", "helios", "navi", "quantum", "taurus", "360 one", "iifl", "jm financial"
        ]
        
        # Check if the query explicitly mentions an unsupported AMC
        if any(amc in query_lower for amc in unsupported_amc_keywords):
            is_unsupported_mf = True
            
        # Check if comparison entities contain unsupported AMCs or don't match the supported ones
        if intent == "compare":
            entities = intent_info.get("compare_entities", [])
            if entities:
                for ent in entities:
                    ent_lower = str(ent).lower()
                    if not any(k in ent_lower for k in supported_mf_keywords):
                        is_unsupported_mf = True
                        break
            else:
                is_unsupported_mf = True
        elif intent in ["quant", "both"]:
            search_term = (ticker or req.query).lower()
            if not any(k in search_term for k in supported_mf_keywords):
                is_unsupported_mf = True

    if is_unsupported_mf:
        advisory_message = """### ⚠️ FundersAI Premium Advisor Notice

FundersAI currently only has active data pipelines set up for **PPFAS (Parag Parikh)** and **ICICI Prudential** mutual funds. 

Live ingestion, portfolio holdings tracking, and historical return pipelines are currently active for **PPFAS**, **ICICI Prudential**, **HDFC**, and **SBI**.
Other AMCs (such as **Nippon India**, **Quant**, **Axis**, etc.) are still being configured.

To experience FundersAI's advanced research capabilities, please try:
- Comparing **Parag Parikh**, **ICICI**, **HDFC**, or **SBI** funds
- Inspecting sector allocations, risk metrics, or portfolio holdings for these supported funds
- Asking about NAV trends, expense ratios, or Sharpe/Alpha comparisons across these supported AMCs."""
        
        response = {
            "answer": advisory_message,
            "debug_intent": intent_info,
            "quant_data": {}
        }
        if trusted_proxy:
            response["_usage"] = _summarize_openrouter_usage(usage_collector)
        return response
    
    quant_data = {}
    news_data = []
    screening_results = None

    def _entity_search_term(entity: str) -> str:
        # Keep entity matching independent in compare mode.
        # Do not inject category words from the full query into each entity,
        # otherwise queries like "A large cap vs B flexi cap" cross-contaminate.
        return str(entity).strip()

    def _fund_search_pattern(search_term: str) -> str:
        cleaned = (
            search_term.lower()
            .replace('felxi', 'flexi')
            .replace(' fund', '')
            .replace(' growth', '')
            .replace('.', ' ')
            .replace(',', ' ')
            .strip()
        )
        words = [word for word in cleaned.split() if word]
        return f"%{'%'.join(words)}%" if words else "%"

    def _fund_from_mfapi(search_term: str) -> dict | None:
        return None
    
    if intent == "screen":
        filters = intent_info.get("screen_filters", {})
        screening_results = await run_stock_screen(filters)
        
    elif intent == "compare":
        entities = intent_info.get("compare_entities", [])
        
        # If user only provided one entity, treat as a single quant lookup
        if len(entities) == 1:
            intent = "quant"
            ticker = entities[0]
        else:
            if asset_type == "stock":
                stock_payload = build_stock_compare(entities)
                quant_data = {
                    "comparison": stock_payload.get("comparison", {}),
                    "why_better": stock_payload.get("why_better"),
                    "verdict_context": stock_payload.get("verdict_context"),
                    "source_freshness": stock_payload.get("source_freshness"),
                    "data_quality": stock_payload.get("data_quality"),
                    "risk_analysis": stock_payload.get("risk_analysis"),
                    "asset_type": "stock",
                }
                intent_info["compare_entities"] = entities
            else:
                comparison_results = {}
                nav_history_cache: dict[str, dict[str, Any]] = {}
                # Pre-fetch Nifty history once for all comparisons
                n_hist_local = await get_nifty_history_df()
                downside_focus = bool(intent_info.get("downside_focus"))

                def _load_amc_holdings_and_sectors(scheme_code_value: Any) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
                    if not supabase or scheme_code_value in (None, ""):
                        return [], [], None
                    scheme_code_str = str(scheme_code_value)
                    try:
                        holdings_res = (
                            supabase.table("mutual_fund_holdings")
                            .select("as_of_date,security_name,isin,sector,weight_pct,source,provider_payload")
                            .eq("scheme_code", int(scheme_code_str) if scheme_code_str.isdigit() else scheme_code_str)
                            .order("as_of_date", desc=True)
                            .order("weight_pct", desc=True)
                            .limit(500)
                            .execute()
                        )
                        holding_rows = holdings_res.data or []
                    except Exception:
                        holding_rows = []

                    latest_as_of = None
                    holdings: list[dict[str, Any]] = []
                    for row in holding_rows:
                        as_of = row.get("as_of_date")
                        if latest_as_of is None:
                            latest_as_of = as_of
                        if as_of != latest_as_of:
                            continue
                        holdings.append(
                            {
                                "security_name": row.get("security_name"),
                                "isin": row.get("isin"),
                                "sector": row.get("sector"),
                                "weight_pct": row.get("weight_pct"),
                                "as_of_date": as_of,
                                "source": row.get("source"),
                                "provider_payload": row.get("provider_payload"),
                            }
                        )
                    def _weight_or_default(value: Any) -> float:
                        try:
                            if value in (None, ""):
                                return -1.0
                            return float(value)
                        except (TypeError, ValueError):
                            return -1.0

                    holdings.sort(key=lambda item: _weight_or_default(item.get("weight_pct")), reverse=True)

                    try:
                        sectors_res = (
                            supabase.table("mutual_fund_sectors")
                            .select("sector,weight_pct,stock_count,source,provider_payload,updated_at")
                            .eq("scheme_code", scheme_code_str)
                            .order("weight_pct", desc=True)
                            .limit(50)
                            .execute()
                        )
                        sectors = sectors_res.data or []
                    except Exception:
                        sectors = []

                    return holdings, sectors, latest_as_of
                
                for entity in entities:
                    db_data = None
                    scheme_code = None
                    best_match_row = None
                    if supabase and asset_type != "stock":
                        try:
                            search_term = _entity_search_term(entity)
                            search_pattern = _fund_search_pattern(search_term)
                            res = supabase.table('mutual_fund_core_snapshot').select('*').ilike('scheme_name', search_pattern).limit(25).execute()
                            if not res.data:
                                res = supabase.table('mutual_funds').select('*').ilike('scheme_name', search_pattern).limit(25).execute()
                            if res.data:
                                best_match = _pick_best_fund_match(
                                    search_term,
                                    res.data,
                                    nav_history_cache=nav_history_cache,
                                    min_history_points=MF_COMPARE_MIN_NAV_POINTS,
                                )
                                best_match_row = best_match
                                scheme_code = best_match['scheme_code']
                                nav_history_summary = _nav_history_summary_for_scheme(scheme_code, nav_history_cache)
                                provider_payload = best_match.get("provider_payload") if isinstance(best_match.get("provider_payload"), dict) else {}
                                amc_trace = provider_payload.get("amc_trace") if isinstance(provider_payload.get("amc_trace"), dict) else {}

                                def _trace_value(field_name: str):
                                    item = amc_trace.get(field_name)
                                    if isinstance(item, dict):
                                        return item.get("value")
                                    return None

                                legacy_row = None
                                if scheme_code not in (None, ""):
                                    try:
                                        code_filter = int(scheme_code) if str(scheme_code).isdigit() else scheme_code
                                        legacy_res = (
                                            supabase.table("mutual_funds")
                                            .select("category,benchmark,aum,expense_ratio,fund_house")
                                            .eq("scheme_code", code_filter)
                                            .limit(1)
                                            .execute()
                                        )
                                        legacy_row = (legacy_res.data or [None])[0]
                                    except Exception:
                                        legacy_row = None
                                db_data = {
                                    "scheme_code": str(scheme_code) if scheme_code is not None else None,
                                    "name": best_match['scheme_name'],
                                    "resolved_scheme_name": best_match['scheme_name'],
                                    "history_points": nav_history_summary.get("count"),
                                    "first_nav_date": nav_history_summary.get("first_nav_date"),
                                    "last_nav_date": nav_history_summary.get("last_nav_date"),
                                    "nav": best_match['nav'],
                                    "nav_date": best_match['nav_date'],
                                    "category": best_match.get('category') or ((legacy_row or {}).get("category") if isinstance(legacy_row, dict) else None),
                                    "benchmark": best_match.get("benchmark") or ((legacy_row or {}).get("benchmark") if isinstance(legacy_row, dict) else None),
                                    "fund_manager": best_match.get("fund_manager") or _trace_value("fund_manager"),
                                    "risk_level": best_match.get("risk_level") or _trace_value("risk_level"),
                                    "fund_house": best_match.get('amc_name') or best_match.get('fund_house') or ((legacy_row or {}).get("fund_house") if isinstance(legacy_row, dict) else None),
                                    "expense_ratio": best_match.get('expense_ratio') if best_match.get('expense_ratio') not in (None, "") else ((legacy_row or {}).get("expense_ratio") if isinstance(legacy_row, dict) else "N/A"),
                                    "aum": best_match.get('aum') if best_match.get('aum') not in (None, "") else ((legacy_row or {}).get("aum") if isinstance(legacy_row, dict) else "N/A"),
                                    "return_1y": best_match.get("return_1y"),
                                    "return_3y": best_match.get("return_3y"),
                                    "return_5y": best_match.get("return_5y"),
                                    "volatility_1y": best_match.get("volatility_1y"),
                                    "max_drawdown_1y": best_match.get("max_drawdown_1y"),
                                    "sharpe_ratio": best_match.get("sharpe_ratio"),
                                    "alpha": best_match.get("alpha"),
                                    "beta": best_match.get("beta"),
                                    "source": "FundersAI DB"
                                }
                                if DEBUG_MF_RESOLUTION:
                                    logger.info(
                                        "MF compare resolved entity='%s' -> scheme_code=%s history_points=%s",
                                        entity,
                                        str(scheme_code),
                                        nav_history_summary.get("count"),
                                    )
                        except Exception as e:
                            logger.error(f"Supabase compare error: {e}")

                    if not db_data and asset_type != "stock":
                        db_data = _fund_from_mfapi(entity)

                    risk_metrics = {}
                    yf_ticker = None
                    stock_symbol = None
                    
                    try:
                        hist = pd.DataFrame()
                        nifty_hist = pd.DataFrame()

                        # Prefer local MF history for compare mode. It is faster, more stable,
                        # and avoids third-party ticker mismatches for Indian mutual funds.
                        if scheme_code:
                            hist = await get_mf_history_df(scheme_code)
                            nifty_hist = n_hist_local

                        if not hist.empty and not nifty_hist.empty:
                            metrics = calculate_alpha_beta_v2(hist, nifty_hist)
                            risk_metrics = {
                                "beta": metrics["beta"],
                                "alpha_vs_nifty": metrics["alpha"],
                                "risk_period": f"{metrics.get('period_years', 3)}Y"
                            }
                    except:
                        pass

                    if db_data:
                        holdings_rows, sector_rows, holdings_as_of = await asyncio.to_thread(_load_amc_holdings_and_sectors, scheme_code)
                        missing_fields = [
                            field
                            for field in ("nav", "nav_date", "expense_ratio", "aum")
                            if _is_missing(db_data.get(field))
                        ]
                        source_summary = {
                            "metadata": db_data.get("source"),
                            "stale": not cache_policy.is_fresh(db_data.get("nav_date") or db_data.get("updated_at"), "mutual_fund_nav"),
                            "nav_date": db_data.get("nav_date"),
                            "amc_trace": ((best_match_row.get("provider_payload") or {}).get("amc_trace") if isinstance((best_match_row or {}).get("provider_payload"), dict) else None),
                            "holdings_as_of_date": holdings_as_of,
                        }
                        db_data.update(risk_metrics)
                        db_data["data_quality"] = {
                            "missing_fields": missing_fields,
                            "message": "Some mutual fund fields are unavailable from local Supabase data." if missing_fields else "Complete for requested fields.",
                            "coverage_status": "incomplete" if missing_fields else "complete",
                        }
                        db_data["source_summary"] = source_summary
                        db_data["history_coverage"] = {
                            "history_points": db_data.get("history_points"),
                            "first_nav_date": db_data.get("first_nav_date"),
                            "last_nav_date": db_data.get("last_nav_date"),
                        }
                        db_data["holdings"] = holdings_rows
                        db_data["sector_allocation"] = sector_rows
                        comparison_results[entity] = db_data
                    elif asset_type != "mutual_fund" and (stock_symbol or yf_ticker):
                        sym = stock_symbol or yf_ticker
                        comparison_results[entity] = _stock_compare_item(sym, risk_metrics)
                    elif asset_type != "mutual_fund":
                        comparison_results[entity] = _stock_compare_item(entity, risk_metrics)
                    else:
                        comparison_results[entity] = {
                            "error": "Data not found for this entity",
                            "data_quality": {
                                "missing_fields": ["scheme_code"],
                                "message": "Mutual fund could not be matched in local Supabase data.",
                                "coverage_status": "incomplete",
                            },
                            "source_summary": {"metadata": None, "stale": True, "nav_date": None},
                            "holdings": [],
                        }
                        
                why_better = build_mf_why_better(comparison_results, downside_focus=downside_focus)
                quant_data = {
                    "comparison": comparison_results,
                    "why_better": why_better,
                    "verdict_context": why_better.get("verdict_context"),
                    "source_freshness": why_better.get("source_freshness"),
                    "data_quality": {name: (payload.get("data_quality") or {}) for name, payload in comparison_results.items()},
                    "risk_analysis": why_better.get("risk_analysis"),
                    "asset_type": "mutual_fund",
                }
                quant_data["holdings_overlap"] = _build_holdings_overlap(comparison_results)
                quant_data["comparison_summary"] = _build_comparison_summary(quant_data)
    
    # Handle single quant lookup (or forced single comparison)
    if intent in ["quant", "both"]:
        quant_data = {}

        if asset_type != "mutual_fund":
            stock_symbol = resolve_stock_symbol(ticker or req.query)
            yf_ticker = await resolve_mf_ticker(ticker or req.query)
            final_ticker = stock_symbol or yf_ticker or ticker
            quant_data = fetch_quant_data(final_ticker, period)
        
        # Fallback to Supabase
        if (not quant_data or "error" in quant_data) and supabase and asset_type != "stock":
            try:
                search_term = ticker or req.query
                search_pattern = _fund_search_pattern(search_term)
                res = supabase.table('mutual_fund_core_snapshot').select('*').ilike('scheme_name', search_pattern).limit(25).execute()
                if not res.data:
                    res = supabase.table('mutual_funds').select('*').ilike('scheme_name', search_pattern).limit(25).execute()
                if res.data:
                    fund = _pick_best_fund_match(
                        search_term,
                        res.data,
                        nav_history_cache={},
                        min_history_points=MF_COMPARE_MIN_NAV_POINTS if intent == "compare" else 0,
                    )
                    scheme_code = fund['scheme_code']
                    quant_data = {
                        "name": fund['scheme_name'],
                        "price": fund['nav'],
                        "date": fund['nav_date'],
                        "fund_house": fund.get('amc_name') or fund.get('fund_house'),
                        "aum": fund.get('aum', "N/A"),
                        "expense_ratio": fund.get('expense_ratio', "N/A"),
                        "source": "FundersAI DB"
                    }
                    
                    # Compute risk metrics locally for single entity too!
                    hist = await get_mf_history_df(scheme_code)
                    nifty_hist = await get_nifty_history_df()
                    if not hist.empty and not nifty_hist.empty:
                        metrics = calculate_alpha_beta_v2(hist, nifty_hist)
                        quant_data.update({
                            "beta": metrics["beta"],
                            "alpha_vs_nifty": metrics["alpha"],
                            "risk_period": f"{metrics.get('period_years', 3)}Y"
                        })
            except: pass

        if (not quant_data or "error" in quant_data) and asset_type != "stock":
            fund_data = _fund_from_mfapi(ticker or req.query)
            if fund_data:
                quant_data = fund_data
            
        if intent in ["news", "both"]:
            news_items = fetch_news(req.query, ticker)
            if sentiment:
                news_items = await analyze_news_sentiment(news_items, usage_collector=usage_collector)
            news_data = news_items

    if intent in ["news", "compare"] and not news_data:
        news_items = fetch_news(req.query, ticker)
        if sentiment:
            news_items = await analyze_news_sentiment(news_items, usage_collector=usage_collector)
        news_data = news_items
            
    final_answer = await synthesis_response(
        req.query,
        intent_info,
        quant_data,
        news_data,
        screening_results,
        req.research_depth,
        req.explanation_mode,
        req.comparison_view_mode,
        usage_collector=usage_collector,
    )
    why_better_payload = quant_data.get("why_better") if isinstance(quant_data, dict) and isinstance(quant_data.get("why_better"), dict) else {}
    response_json = {
        "answer": final_answer,
        "debug_intent": intent_info,
        "quant_data": quant_data,
        "source_freshness": quant_data.get("source_freshness") if isinstance(quant_data, dict) else None,
        "data_quality": quant_data.get("data_quality") if isinstance(quant_data, dict) else None,
        "risk_analysis": quant_data.get("risk_analysis") if isinstance(quant_data, dict) else None,
        "confidence": why_better_payload.get("confidence"),
        "explanation_mode": req.explanation_mode or ("advanced" if req.research_depth == "deep" else "beginner"),
    }
    
    if intent == "compare":
        entities = intent_info.get("compare_entities", [])
        if len(entities) >= 2:
            compare_context = {
                "last_compare": {
                    "asset_type": intent_info.get("asset_type") or (quant_data.get("asset_type") if isinstance(quant_data, dict) else None) or ("stock" if asset_type == "stock" else "mutual_fund"),
                    "entities": [str(entity) for entity in entities[:2]],
                    "ids": [],
                    "query": intent_info.get("source_query") or req.query,
                    "last_focus": intent_info.get("followup_topic") or _detect_followup_topic(req.query),
                    "available_topics": ["returns", "risk", "cost", "holdings", "sectors", "data_quality"],
                }
            }
            response_json["conversation_context"] = compare_context
            resolved_ids = []
            seen_ids = set()
            nav_history_cache_for_ids: dict[str, dict[str, Any]] = {}
            comparison_payload = quant_data.get("comparison", {}) if isinstance(quant_data, dict) else {}
            fallback_map = {
                "hdfc flexi cap": "118955",
                "parag parikh flexi cap": "122639",
                "quant small cap": "120847",
                "nippon india small cap": "119332"
            }
            def _append_resolved_id(value: str) -> None:
                if value not in seen_ids:
                    seen_ids.add(value)
                    resolved_ids.append(value)
             
            for entity in entities:
                if comparison_payload and _is_unavailable_entity(comparison_payload.get(entity)):
                    continue
                if comparison_payload:
                    payload_row = comparison_payload.get(entity)
                    if isinstance(payload_row, dict):
                        payload_code = payload_row.get("scheme_code")
                        if payload_code not in (None, "", "N/A"):
                            payload_code_str = str(payload_code)
                            if asset_type != "stock":
                                payload_hist = _nav_history_summary_for_scheme(payload_code_str, nav_history_cache_for_ids)
                                if payload_hist.get("count", 0) < MF_COMPARE_MIN_NAV_POINTS:
                                    if DEBUG_MF_RESOLUTION:
                                        logger.info(
                                            "Skipping scheme_code=%s for entity='%s' due to low history_points=%s",
                                            payload_code_str,
                                            entity,
                                            payload_hist.get("count"),
                                        )
                                else:
                                    _append_resolved_id(payload_code_str)
                                    continue
                            else:
                                _append_resolved_id(payload_code_str)
                                continue
                ent_lower = entity.lower()
                resolved = False
                if asset_type != "stock":
                    for key, code in fallback_map.items():
                        if key in ent_lower:
                            fallback_hist = _nav_history_summary_for_scheme(code, nav_history_cache_for_ids)
                            if fallback_hist.get("count", 0) >= MF_COMPARE_MIN_NAV_POINTS:
                                _append_resolved_id(code)
                                resolved = True
                                break
                if resolved: continue
                if supabase and asset_type != "stock":
                    try:
                        search_term = _entity_search_term(entity)
                        search_pattern = _fund_search_pattern(search_term)
                        res = supabase.table('mutual_fund_core_snapshot').select('scheme_code,scheme_name').ilike('scheme_name', search_pattern).limit(25).execute()
                        if not res.data:
                            res = supabase.table('mutual_funds').select('scheme_code,scheme_name').ilike('scheme_name', search_pattern).limit(25).execute()
                        if res.data and len(res.data) > 0:
                            best_match = _pick_best_fund_match(
                                search_term,
                                res.data,
                                nav_history_cache=nav_history_cache_for_ids,
                                min_history_points=MF_COMPARE_MIN_NAV_POINTS,
                            )
                            _append_resolved_id(str(best_match['scheme_code']))
                            resolved = True
                    except: pass
                if resolved: continue
                if asset_type != "mutual_fund":
                    stock_symbol = resolve_stock_symbol(entity)
                    ticker_clean = stock_symbol or entity.split()[0].upper()
                    _append_resolved_id(ticker_clean); resolved = True
            
            if len(resolved_ids) >= 2:
                compare_context["last_compare"]["ids"] = resolved_ids[:2]
                response_json["system_action"] = {
                    "type": "COMPARE",
                    "ids": resolved_ids[:2],
                    "entities": [str(entity) for entity in entities[:2]],
                    "asset_type": compare_context["last_compare"]["asset_type"],
                }
                
    if trusted_proxy:
        response_json["_usage"] = _summarize_openrouter_usage(usage_collector)

    return response_json

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
