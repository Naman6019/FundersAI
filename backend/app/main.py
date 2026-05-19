import os
import json
import logging
import asyncio
import sys
import time
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Dict, Any, List, Literal
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import yfinance as yf
import feedparser
from datetime import datetime, timedelta, timezone
import pytz
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

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://marketmind.vercel.app",
        "https://mooliq.com",
        "https://www.mooliq.com",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.routes.quant import router as quant_router
app.include_router(quant_router)
from app.routes.indianapi import router as indianapi_router
app.include_router(indianapi_router)
from app.routes.mf_ingestion import router as mf_ingestion_router
app.include_router(mf_ingestion_router)

@app.get("/")
def read_root():
    return {"message": "Mooliq API is running. Use /health for health checks."}

@app.get("/health")
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
    if not expected_admin_key or x_admin_key != expected_admin_key:
        raise HTTPException(status_code=403, detail="admin_auth_required")


def _iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


@app.get("/api/data-health")
def data_health():
    now_utc = datetime.now(timezone.utc)
    metrics = [
        {"label": "MF NAV", "status": "Missing", "note": "No NAV snapshot rows found.", "last_updated": None},
        {"label": "AUM / TER", "status": "Missing", "note": "No AUM+TER rows found.", "last_updated": None},
        {"label": "Risk metrics", "status": "Missing", "note": "No risk metric rows found.", "last_updated": None},
        {"label": "Factsheets", "status": "Missing", "note": "No parsed factsheet/disclosure docs found.", "last_updated": None},
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
                {"label": "Factsheets", "status": "Missing", "note": "Not checked due core snapshot read failure.", "last_updated": None},
            ],
        }

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

    aum_ter_rows = [row for row in core_rows if row.get("aum") not in (None, "") and row.get("expense_ratio") not in (None, "")]
    latest_aum_ter_dt = max(
        [dt for dt in (_to_utc_datetime(row.get("last_updated")) for row in aum_ter_rows) if dt is not None],
        default=None,
    )
    aum_ter_age_days = _age_days(latest_aum_ter_dt, now_utc)
    if latest_aum_ter_dt:
        enrich_is_fresh = cache_policy.is_fresh(latest_aum_ter_dt.isoformat(), "mutual_fund_enrichment", now=now_utc)
        if enrich_is_fresh:
            metrics[1].update(status="Synced", note=f"Latest AUM/TER age {_fmt_age(aum_ter_age_days)}.", last_updated=latest_aum_ter_dt.isoformat())
        elif aum_ter_age_days is not None and aum_ter_age_days <= 60:
            metrics[1].update(status="Lagging", note=f"Latest AUM/TER age {_fmt_age(aum_ter_age_days)}.", last_updated=latest_aum_ter_dt.isoformat())
        else:
            metrics[1].update(status="Stale", note=f"Latest AUM/TER age {_fmt_age(aum_ter_age_days)}.", last_updated=latest_aum_ter_dt.isoformat())

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
            last_downloaded_at=last_downloaded_dt.isoformat() if last_downloaded_dt else None,
            last_parse_attempt_at=last_parse_attempt_dt.isoformat() if last_parse_attempt_dt else None,
            last_success_at=last_success_dt.isoformat() if last_success_dt else None,
            last_failure_at=last_failure_dt.isoformat() if last_failure_dt else None,
        )

        if total_documents == 0:
            metrics[3].update(
                status="Missing",
                note="No AMC factsheet/disclosure docs ingested yet.",
                last_updated=None,
            )
        else:
            success_age_days = _age_days(last_success_dt, now_utc)
            success_age = _fmt_age(success_age_days) or "n/a"
            note = (
                f"parsed={parsed_count}, pending={pending_count}, failed={failed_count}, "
                f"review={needs_review_count}, total={total_documents}"
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
        logger.warning("Data health factsheet read failed: %s", exc)
        metrics[3].update(status="Error", note="Factsheet pipeline tables not readable.", last_updated=None)

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

class ChatRequest(BaseModel):
    query: str
    asset_type: Literal["auto", "stock", "mutual_fund"] = "auto"
    research_depth: Literal["standard", "deep"] = "standard"
    comparison_view_mode: Literal["canvas", "chat"] = "canvas"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.1-8b-instant"
IST = pytz.timezone('Asia/Kolkata')
QUANT_CACHE: Dict[str, Any] = {}
QUANT_CACHE_TTL_SECONDS = int(os.getenv("QUANT_CACHE_TTL_SECONDS", "600"))
INDIANAPI_CHAT_STOCK_ENABLED = os.getenv("INDIANAPI_CHAT_STOCK_ENABLED", "1").strip().lower() in {"1", "true", "yes", "on"}
if "INDIANAPI_CHAT_STOCK_ENABLED" not in os.environ:
    INDIANAPI_CHAT_STOCK_ENABLED = os.getenv("INDIANAPI_ENABLE_LIVE_CALLS", "0").strip().lower() in {"1", "true", "yes", "on"}
DEBUG_MF_RESOLUTION = os.getenv("DEBUG_MF_RESOLUTION", "0").strip().lower() in {"1", "true", "yes", "on"}
MF_COMPARE_MIN_NAV_POINTS = max(int(os.getenv("MF_COMPARE_MIN_NAV_POINTS", "252")), 1)

async def function_ollama_chat(messages, format="json", max_retries=2):
    groq_key = os.environ.get("GROQ_API_KEY")
    if not groq_key:
        logger.error("Missing GROQ_API_KEY in environment!")
        return None
        
    req_messages = [dict(m) for m in messages]
    payload = {
        "model": GROQ_MODEL,
    }
    
    if format == "json":
        payload["response_format"] = {"type": "json_object"}
        if "json" not in req_messages[0]["content"].lower():
            req_messages[0]["content"] += "\nReturn output strictly in JSON format."
            
    payload["messages"] = req_messages
            
    headers = {
        "Authorization": f"Bearer {groq_key}",
        "Content-Type": "application/json"
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            response = await client.post(GROQ_BASE_URL, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Groq API Error: {e}")
            return None

async def route_query(query: str, asset_type: str = "auto") -> dict:
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

    system_prompt = """You are the Router Agent for Mooliq. Classify the user query intent.
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
    
    result = await function_ollama_chat(messages, format="json")
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
    
    return {"alpha": round(alpha, 2), "beta": beta, "period_years": round(years, 1)}

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

async def analyze_news_sentiment(news_items: list) -> list:
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
    
    result = await function_ollama_chat(messages, format="json")
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

def fetch_news(query: str, ticker: str, sentiment_flag: bool = False) -> list:
    """Agent 3: News Parser"""
    search_term = ticker.replace('.NS', '').replace('.BO', '') if ticker else query
    encoded_term = search_term.replace(' ', '+')
    rss_url = f"https://news.google.com/rss/search?q={encoded_term}+India+Stock+Market&hl=en-IN&gl=IN&ceid=IN:en"
    
    try:
        feed = feedparser.parse(rss_url)
        news_items = []
        for entry in feed.entries[:6]: 
            news_items.append({
                "title": entry.title,
                "source": entry.source.title if hasattr(entry, 'source') else "News Source",
                "published": entry.published,
                "url": getattr(entry, "link", None),
            })
        return news_items
    except Exception as e:
        logger.error(f"News Error: {e}")
        return []

DISCLAIMER = "> ⚠️ **Disclaimer:** *Mooliq is an informational research tool only. Nothing presented here constitutes investment advice, a solicitation, or a recommendation to buy or sell any security. Always conduct your own research and consult a SEBI-registered Investment Advisor before making any financial decision.*"
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
    return [
        ("Matched Name", _safe_value(data.get("name"))),
        ("NAV", _format_price(nav)),
        ("NAV Date", _safe_value(nav_date)),
        ("Fund House", _safe_value(fund_house)),
        ("Category", _safe_value(category)),
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
        f"{name} could not be matched in Mooliq data."
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
        return f"{available} of {total} requested entities have structured Mooliq data."
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
    comparison_view_mode: str = "canvas",
) -> str:
    """Synthesis Core"""
    
    intent = intent_info.get("intent")
    deep_research = research_depth == "deep"
    
    if intent == "general":
        system_prompt_gen = """You are Mooliq, an expert AI stock market research assistant and financial educator.
If the user asks basic educational questions (e.g., 'What is PE ratio?', 'Explain the metrics used here'), provide a clear, comprehensive, and beginner-friendly explanation. 
Break down metrics like P/E Ratio (valuation), RSI (momentum/overbought/oversold), and moving averages carefully. Use bullet points and analogies if helpful. 
Do NOT be overly brief when explaining concepts. Provide deep value to the user.
NEVER give direct financial advice to buy or sell a specific stock."""
        if deep_research:
            system_prompt_gen = """You are Mooliq, an expert AI stock market research assistant and financial educator.
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
        return await function_ollama_chat(messages, format="text")

    table_markdown, data_notes = _data_table_markdown(intent, quant_data, screening_results)
    news_markdown = _news_markdown(news_data)
    subject = _summary_subject(query, intent_info, quant_data)
    snapshot = _snapshot_line(intent, quant_data)
    compare_direct_answer = _compare_direct_answer_markdown(quant_data) if intent == "compare" else ""

    system_prompt = """You are Mooliq, a research-only Indian market analyst.
Write only the Trend Observation paragraph.
Use the provided structured facts only. Do not add new numbers.
Use neutral research language. Do not use advice words or phrases like buy, sell, invest, avoid, investors should, attractive option, or long-term investment.
If data is unavailable for an entity, mention that the comparison is limited by missing data.
Keep it to 3-5 concise sentences."""
    if deep_research:
        system_prompt = """You are Mooliq, a research-only Indian market analyst.
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

News Data:
{news_markdown}
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": context}
    ]
    
    trend = await function_ollama_chat(messages, format="text")
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

    title = "Deep Research Snapshot" if deep_research else "Snapshot"
    analysis_heading = "Deep Research Analysis" if deep_research else "Trend Observation"

    if intent == "compare" and comparison_view_mode == "canvas":
        return f"""### {subject} — {title}
> Detailed comparison metrics are visible in the canvas panel.

### News & Announcements *(last 48-72 hrs)*
{news_markdown}

### {analysis_heading}

{trend}

{DISCLAIMER}"""

    return f"""### {subject} — {title}
> {snapshot}
{"\n\n### How They Differ\n" + compare_direct_answer if compare_direct_answer else ""}

### Data Table
{table_markdown}{notes_markdown}

### News & Announcements *(last 48-72 hrs)*
{news_markdown}

### {analysis_heading}

{trend}

{DISCLAIMER}"""

@app.get("/api/trigger-fetch")
async def trigger_eod_fetch(background_tasks: BackgroundTasks):
    """Trigger background EOD fetching process via cron tool"""
    background_tasks.add_task(run_eod_fetch)
    return {"message": "Background fetch process triggered successfully."}

async def get_mf_history_df(scheme_code: int, days: int = 1100):
    """Fetch MF history from Supabase and return as a DataFrame compatible with risk functions."""
    if not supabase:
        return pd.DataFrame()

    def _fetch_rows_for_filter(code_filter: Any, max_rows: int) -> list[dict[str, Any]]:
        batch_size = 1000
        offset = 0
        collected: list[dict[str, Any]] = []
        while offset < max_rows:
            chunk = (
                supabase.table('mutual_fund_nav_history')
                .select('nav, nav_date')
                .eq('scheme_code', code_filter)
                .order('nav_date', desc=True)
                .range(offset, offset + batch_size - 1)
                .execute()
                .data
                or []
            )
            if not chunk:
                break
            collected.extend(chunk)
            if len(chunk) < batch_size:
                break
            offset += batch_size
        return collected[:max_rows]

    try:
        candidate_filters = [str(scheme_code)]
        try:
            candidate_filters.append(int(scheme_code))
        except Exception:
            pass

        best_rows: list[dict[str, Any]] = []
        for code_filter in candidate_filters:
            rows = _fetch_rows_for_filter(code_filter, days)
            if len(rows) > len(best_rows):
                best_rows = rows

        if best_rows:
            df = pd.DataFrame(best_rows)
            df['date'] = pd.to_datetime(df['nav_date'])
            df = df.sort_values('date')
            df.rename(columns={'nav': 'Close'}, inplace=True)
            df.set_index('date', inplace=True)
            return _normalize_price_df_index(df)
    except Exception as e:
        logger.error(f"Failed to fetch local MF history for {scheme_code}: {e}")
    return pd.DataFrame()

async def get_nifty_history_df(days: int = 1100):
    """Fetch NIFTY history from normalized stock price history."""
    if not supabase:
        return pd.DataFrame()
    try:
        res = supabase.table('stock_prices_daily').select('close, date').eq('symbol', 'NIFTY').order('date', desc=True).limit(days).execute()
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
        value += sum(10 for word in entity_words if word in name_norm)
        overlap_hits = sum(1 for word in entity_words if word in name_norm)
        if overlap_hits:
            notes.append(f"token_overlap:+{overlap_hits * 10}")
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
        fund_res = supabase.table('mutual_fund_core_snapshot').select('*').eq('scheme_code', str(scheme_code)).limit(1).execute()
        if not fund_res.data:
            fund_res = supabase.table('mutual_funds').select('*').eq('scheme_code', scheme_code).limit(1).execute()
        if not fund_res.data:
            raise HTTPException(status_code=404, detail="Mutual fund not found")

        details = fund_res.data[0]
        hist_df = await get_mf_history_df(scheme_code, days=2200)
        close_series = hist_df["Close"] if not hist_df.empty else pd.Series(dtype=float)

        returns = {
            "1Y": details.get("return_1y") if details.get("return_1y") is not None else _compute_cagr_from_close(close_series, 1),
            "3Y": details.get("return_3y") if details.get("return_3y") is not None else _compute_cagr_from_close(close_series, 3),
            "5Y": details.get("return_5y") if details.get("return_5y") is not None else _compute_cagr_from_close(close_series, 5)
        }
        risk_metrics = _compute_nav_risk_metrics(close_series)
        nifty_hist = await get_nifty_history_df(days=2200)
        if risk_metrics is None:
            risk_metrics = {}
        if details.get("volatility_1y") is not None:
            risk_metrics["stdDev"] = details.get("volatility_1y")
        if details.get("max_drawdown_1y") is not None:
            risk_metrics["maxDrawdown"] = details.get("max_drawdown_1y") / 100 if details.get("max_drawdown_1y") is not None else None
        if details.get("beta") is not None:
            risk_metrics["beta"] = details.get("beta")
        if details.get("alpha") is not None:
            risk_metrics["alpha_vs_nifty"] = details.get("alpha")
        if details.get("sharpe_ratio") is not None:
            risk_metrics["sharpeRatio"] = details.get("sharpe_ratio")
        if not hist_df.empty and not nifty_hist.empty:
            alpha_beta = calculate_alpha_beta_v2(hist_df, nifty_hist)
            risk_metrics.update({
                "beta": risk_metrics.get("beta") if risk_metrics.get("beta") is not None else alpha_beta.get("beta"),
                "alpha_vs_nifty": risk_metrics.get("alpha_vs_nifty") if risk_metrics.get("alpha_vs_nifty") is not None else alpha_beta.get("alpha"),
                "risk_period": f"{alpha_beta.get('period_years', 3)}Y"
            })

        chart_df = hist_df.sort_index().tail(250) if not hist_df.empty else pd.DataFrame()
        chart_data = []
        if not chart_df.empty:
            chart_data = [
                {
                    "date": idx.strftime("%d-%m-%Y"),
                    "value": round(float(val), 4)
                }
                for idx, val in chart_df["Close"].items()
            ]
        full_data = []
        if not hist_df.empty:
            full_data = [
                {
                    "date": idx.strftime("%d-%m-%Y"),
                    "value": round(float(val), 4)
                }
                for idx, val in hist_df.sort_index(ascending=False)["Close"].items()
            ]

        history_coverage = _history_coverage_from_df(hist_df)
        nav_ref = details.get("nav_date") or details.get("last_updated")
        stale = not cache_policy.is_fresh(nav_ref, "mutual_fund_nav")
        if DEBUG_MF_RESOLUTION:
            logger.info(
                "MF /api/mf scheme_code=%s points=%s first=%s last=%s stale=%s",
                scheme_code,
                history_coverage.get("history_points"),
                history_coverage.get("first_nav_date"),
                history_coverage.get("last_nav_date"),
                stale,
            )
        return {
            "details": details,
            "returns": returns,
            "riskMetrics": risk_metrics,
            "chartData": chart_data,
            "fullData": full_data,
            "historyCoverage": history_coverage,
            "freshness": {
                "stale": stale,
                "warning": "NAV data may be stale." if stale else None,
                "nav_date": details.get("nav_date"),
                "last_updated": details.get("last_updated"),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"MF details endpoint error for {scheme_code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    asset_type = req.asset_type
    intent_info = await route_query(req.query, asset_type)
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
        advisory_message = """### ⚠️ Mooliq Premium Advisor Notice

Mooliq currently only has active data pipelines set up for **PPFAS (Parag Parikh)** and **ICICI Prudential** mutual funds. 

Live ingestion, portfolio holdings tracking, and historical return pipelines are currently active for **PPFAS**, **ICICI Prudential**, **HDFC**, and **SBI**.
Other AMCs (such as **Nippon India**, **Quant**, **Axis**, etc.) are still being configured.

To experience Mooliq's advanced research capabilities, please try:
- Comparing **Parag Parikh**, **ICICI**, **HDFC**, or **SBI** funds
- Inspecting sector allocations, risk metrics, or portfolio holdings for these supported funds
- Asking about NAV trends, expense ratios, or Sharpe/Alpha comparisons across these supported AMCs."""
        
        return {
            "answer": advisory_message,
            "debug_intent": intent_info,
            "quant_data": {}
        }
    
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
                                    "source": "Mooliq DB"
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
                        holdings_rows, sector_rows, holdings_as_of = _load_amc_holdings_and_sectors(scheme_code)
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
                    "asset_type": "mutual_fund",
                }
    
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
                        "source": "Mooliq DB"
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
                news_items = await analyze_news_sentiment(news_items)
            news_data = news_items

    if intent in ["news", "compare"] and not news_data:
        news_items = fetch_news(req.query, ticker)
        if sentiment:
            news_items = await analyze_news_sentiment(news_items)
        news_data = news_items
            
    final_answer = await synthesis_response(
        req.query,
        intent_info,
        quant_data,
        news_data,
        screening_results,
        req.research_depth,
        req.comparison_view_mode,
    )
    response_json = {
        "answer": final_answer,
        "debug_intent": intent_info,
        "quant_data": quant_data
    }
    
    if intent == "compare":
        entities = intent_info.get("compare_entities", [])
        if len(entities) >= 2:
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
                response_json["system_action"] = {"type": "COMPARE", "ids": resolved_ids[:2]}
                
    return response_json

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
