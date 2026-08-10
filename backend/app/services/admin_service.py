from __future__ import annotations

import logging
import os
import re
import hmac
from contextvars import ContextVar
from datetime import date, datetime, timedelta, timezone
from typing import Any

from fastapi import Header, Query
from pydantic import BaseModel

from app.exceptions import AuthorizationError, ConflictError, DataUnavailableError, EntityNotFoundError
from app.repositories.admin_ops_repository import AdminOpsRepository
from app.services.review_priority_service import ReviewPriorityService
from app.services import cache_policy
from app.services.mf_nav_freshness import assess_nav_freshness
from app.services.chat_service import (
    _normalize_fund_text,
    _pick_best_fund_match,
    _resolver_horizon_to_min_points,
    _score_fund_candidates,
    _supports_from_history_summary,
)
from app.services.provider_usage import build_usage_dashboard
from app.services.supported_amcs import SUPPORTED_MF_AMC_MARKERS, supported_amc_label_from_text
from app.services.mf_metric_target_service import (
    MF_METRIC_HISTORY_MAX_AGE_DAYS,
    metric_history_is_ready,
    supported_metric_targets,
)
from app.utils.date_helpers import age_days as _age_days
from app.utils.date_helpers import fmt_age as _fmt_age
from app.utils.date_helpers import iso_or_none as _iso_or_none
from app.utils.date_helpers import to_utc_datetime as _to_utc_datetime

logger = logging.getLogger(__name__)

_default_admin_repository = AdminOpsRepository()
_current_admin_repository: ContextVar[AdminOpsRepository] = ContextVar("current_admin_repository", default=_default_admin_repository)


def get_admin_repository() -> AdminOpsRepository:
    return _current_admin_repository.get()


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
    if not get_admin_repository():
        return 0
    query = get_admin_repository().table("mf_raw_documents").select("id", count="exact")
    if status:
        query = query.eq("parse_status", status)
    response = query.execute()
    return int(response.count or 0)


def _has_metric_value(value: Any) -> bool:
    return value not in (None, "")


def _latest_core_snapshot_nav_date() -> datetime | None:
    """Read the actual latest NAV date instead of inferring it from a recent-write sample."""
    try:
        rows = (
            get_admin_repository().table("mutual_fund_core_snapshot")
            .select("nav_date")
            .order("nav_date", desc=True, nullsfirst=False)
            .limit(1)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("Data health latest NAV date read failed: %s", exc)
        return None
    return _to_utc_datetime(rows[0].get("nav_date")) if rows else None


def _supported_amc_label(value: Any) -> str | None:
    return supported_amc_label_from_text(value)


def _month_string(value: Any) -> str | None:
    dt = _to_utc_datetime(value)
    if dt:
        return dt.date().isoformat()[:7]
    raw = str(value or "").strip()
    if re.match(r"^\d{4}-\d{2}", raw):
        return raw[:7]
    return None


def _coverage_ratio(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count / total, 4)


def _build_amc_parser_quality(
    core_rows: list[dict[str, Any]],
    document_rows: list[dict[str, Any]],
    review_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    quality: dict[str, dict[str, Any]] = {
        label: {
            "amc": label,
            "latest_factsheet_month": None,
            "latest_holdings_month": None,
            "total_funds": 0,
            "ter_count": 0,
            "benchmark_count": 0,
            "risk_label_count": 0,
            "ter_coverage": 0.0,
            "benchmark_coverage": 0.0,
            "risk_label_coverage": 0.0,
            "parse_review_count": 0,
            "holdings_source_note": "Axis holdings are % of NAV rows from AMC factsheets, not ISIN-backed." if label == "AXIS" else None,
        }
        for label in SUPPORTED_MF_AMC_MARKERS
    }

    for row in core_rows:
        label = _supported_amc_label(row.get("amc_name") or row.get("scheme_name"))
        if not label or label not in quality:
            continue
        bucket = quality[label]
        bucket["total_funds"] += 1
        if _has_metric_value(row.get("expense_ratio")):
            bucket["ter_count"] += 1
        if _has_metric_value(row.get("benchmark")):
            bucket["benchmark_count"] += 1
        if _has_metric_value(row.get("risk_level")):
            bucket["risk_label_count"] += 1

    has_review_rows = bool(review_rows)

    for row in document_rows:
        label = _supported_amc_label(row.get("amc_code"))
        if not label or label not in quality:
            continue
        bucket = quality[label]
        doc_type = str(row.get("source_document_type") or "").strip().lower()
        status = str(row.get("parse_status") or "").strip().lower()
        report_month = _month_string(row.get("report_month") or row.get("parsed_at") or row.get("downloaded_at"))
        if status == "parsed" and doc_type == "factsheet" and report_month:
            current = bucket.get("latest_factsheet_month")
            if not current or report_month > current:
                bucket["latest_factsheet_month"] = report_month
        if status == "parsed" and doc_type in {"factsheet", "portfolio_disclosure"} and report_month:
            current = bucket.get("latest_holdings_month")
            if not current or report_month > current:
                bucket["latest_holdings_month"] = report_month
        if not has_review_rows and status in {"needs_review", "failed"}:
            bucket["parse_review_count"] += 1

    for row in review_rows:
        label = _supported_amc_label(row.get("amc_code"))
        if not label or label not in quality:
            continue
        if str(row.get("status") or "").strip().lower() in {"pending_review", "needs_review", "failed", ""}:
            quality[label]["parse_review_count"] += 1

    for bucket in quality.values():
        total = int(bucket["total_funds"] or 0)
        bucket["ter_coverage"] = _coverage_ratio(int(bucket["ter_count"] or 0), total)
        bucket["benchmark_coverage"] = _coverage_ratio(int(bucket["benchmark_count"] or 0), total)
        bucket["risk_label_coverage"] = _coverage_ratio(int(bucket["risk_label_count"] or 0), total)

    return [quality[label] for label in sorted(quality)]


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


def _empty_mf_metric_coverage() -> dict[str, Any]:
    return {
        "catalog_total": 0,
        "supported_mapped_total": 0,
        "metric_eligible_total": 0,
        "history_ready_count": 0,
        "history_freshness_window_days": MF_METRIC_HISTORY_MAX_AGE_DAYS,
        "alpha_beta_count": 0,
        "supported_history_alpha_beta_count": 0,
        "catalog_alpha_beta_coverage": 0.0,
        "supported_alpha_beta_coverage": 0.0,
        "supported_history_alpha_beta_coverage": 0.0,
        "supported_benchmark_count": 0,
        "supported_benchmark_coverage": 0.0,
        "supported_risk_count": 0,
        "supported_risk_coverage": 0.0,
        "benchmark_freshness": {
            "identifier": "NIFTY",
            "mode": "proxy",
            "latest_date": None,
            "business_day_lag": None,
            "fresh": False,
        },
        "last_known_good_usage": 0,
    }


def _business_day_lag(latest: date, current: date) -> int:
    if latest >= current:
        return 0
    lag = 0
    cursor = latest + timedelta(days=1)
    while cursor <= current:
        if cursor.weekday() < 5:
            lag += 1
        cursor += timedelta(days=1)
    return lag


def _mf_metric_coverage(now_utc: datetime) -> dict[str, Any]:
    coverage = _empty_mf_metric_coverage()
    repository = get_admin_repository()
    if not repository:
        return coverage
    try:
        coverage["catalog_total"] = int(
            repository.table("mutual_fund_core_snapshot")
            .select("scheme_code", count="exact")
            .limit(1)
            .execute()
            .count
            or 0
        )
    except Exception:
        pass

    try:
        targets = supported_metric_targets(repository)
        target_codes = [row["scheme_code"] for row in targets]
        coverage["supported_mapped_total"] = len(target_codes)
        if not target_codes:
            return coverage

        cache_by_code: dict[str, dict[str, Any]] = {}
        core_by_code: dict[str, dict[str, Any]] = {}
        for start in range(0, len(target_codes), 500):
            codes = target_codes[start : start + 500]
            cache_rows = (
                repository.table("nav_api_cache")
                .select("scheme_code,point_count,last_nav_date,fetched_at,expires_at,updated_at")
                .in_("scheme_code", codes)
                .execute()
                .data
                or []
            )
            cache_by_code.update({str(row["scheme_code"]): row for row in cache_rows if row.get("scheme_code")})
            core_rows = (
                repository.table("mutual_fund_core_snapshot")
                .select("scheme_code,alpha,beta,benchmark,risk_level,provider_payload")
                .in_("scheme_code", codes)
                .execute()
                .data
                or []
            )
            core_by_code.update({str(row["scheme_code"]): row for row in core_rows if row.get("scheme_code")})

        history_ready = 0
        supported_history_alpha_beta = 0
        eligible_codes: set[str] = set()
        alpha_beta = 0
        benchmark_count = 0
        risk_count = 0
        last_known_good = 0
        for code in target_codes:
            cache = cache_by_code.get(code, {})
            history_is_ready = metric_history_is_ready(cache, now=now_utc)
            if history_is_ready:
                history_ready += 1
            core = core_by_code.get(code, {})
            has_alpha_beta = (
                core.get("alpha") not in (None, "")
                and core.get("beta") not in (None, "")
            )
            if history_is_ready and has_alpha_beta:
                supported_history_alpha_beta += 1
            provider_payload = core.get("provider_payload")
            metric_snapshot = (
                provider_payload.get("metric_snapshot", {})
                if isinstance(provider_payload, dict)
                else {}
            )
            if int(metric_snapshot.get("overlap_points") or 0) >= int(metric_snapshot.get("minimum_overlap_points") or 30):
                eligible_codes.add(code)
                if has_alpha_beta:
                    alpha_beta += 1
            if core.get("benchmark") not in (None, ""):
                benchmark_count += 1
            if core.get("risk_level") not in (None, ""):
                risk_count += 1
            if metric_snapshot.get("last_known_good_used"):
                last_known_good += 1

        supported_total = len(target_codes)
        eligible_total = len(eligible_codes)
        coverage.update(
            metric_eligible_total=eligible_total,
            history_ready_count=history_ready,
            alpha_beta_count=alpha_beta,
            supported_history_alpha_beta_count=supported_history_alpha_beta,
            catalog_alpha_beta_coverage=_coverage_ratio(alpha_beta, int(coverage["catalog_total"])),
            supported_alpha_beta_coverage=_coverage_ratio(alpha_beta, eligible_total),
            supported_history_alpha_beta_coverage=_coverage_ratio(
                supported_history_alpha_beta,
                supported_total,
            ),
            supported_benchmark_count=benchmark_count,
            supported_benchmark_coverage=_coverage_ratio(benchmark_count, supported_total),
            supported_risk_count=risk_count,
            supported_risk_coverage=_coverage_ratio(risk_count, supported_total),
            last_known_good_usage=last_known_good,
        )
    except Exception as exc:
        logger.warning("Data health MF metric coverage read failed: %s", exc)

    try:
        benchmark_rows = (
            repository.table("stock_prices_daily")
            .select("date")
            .eq("symbol", "NIFTY")
            .order("date", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        latest = _to_utc_datetime((benchmark_rows or [{}])[0].get("date"))
        if latest:
            lag = _business_day_lag(latest.date(), now_utc.date())
            coverage["benchmark_freshness"].update(
                latest_date=latest.date().isoformat(),
                business_day_lag=lag,
                fresh=lag <= 3,
            )
    except Exception as exc:
        logger.warning("Data health benchmark freshness read failed: %s", exc)
    return coverage


def _latest_mf_doc_timestamp(*, status: str | None, field: str) -> datetime | None:
    if not get_admin_repository():
        return None
    query = get_admin_repository().table("mf_raw_documents").select(field).order(field, desc=True).limit(5)
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
        raise AuthorizationError("admin_auth_required")


def _iso_or_none(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


class AdminDocumentReviewAction(BaseModel):
    reviewer_notes: str | None = None
    issue_category: str | None = None


class PromotionReviewDecisionRequest(BaseModel):
    amc: str
    report_month: str
    scope: str
    subject_key: str
    subject_label: str | None = None
    resolution: str
    decided_value: dict[str, Any] = {}
    source_document_id: str | None = None
    reviewed_by: str
    note: str | None = None


class PromotionReviewPromoteRequest(BaseModel):
    decision_id: str
    requested_by: str


def _review_action_notes(payload: AdminDocumentReviewAction | None) -> str | None:
    if not payload or payload.reviewer_notes is None:
        return None
    notes = payload.reviewer_notes.strip()
    return notes or None


def _review_issue_category(payload: AdminDocumentReviewAction | None) -> str | None:
    value = str(payload.issue_category or "").strip() if payload else ""
    return value or None


def _load_mf_review_document(document_id: str) -> dict[str, Any]:
    if not get_admin_repository():
        raise DataUnavailableError("supabase_unavailable")

    rows = (
        get_admin_repository().table("mf_raw_documents")
        .select("id,parse_status,validation_issues")
        .eq("id", document_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise EntityNotFoundError("document_not_found")
    return rows[0]


def _mark_review_queue(document_id: str, status: str, reviewer_notes: str | None, issue_category: str | None = None) -> None:
    if not get_admin_repository():
        return

    payload: dict[str, Any] = {
        "status": status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    if reviewer_notes:
        payload["reviewer_notes"] = reviewer_notes
    if issue_category:
        payload["issue_category"] = issue_category.strip().lower()[:80]
    if status in {"approved", "skipped"}:
        payload["reviewer_decision"] = status
        payload["reviewed_at"] = payload["updated_at"]

    try:
        (
            get_admin_repository().table("mf_parse_review_queue")
            .update(payload)
            .eq("source_document_id", document_id)
            .eq("status", "pending_review")
            .execute()
        )
    except Exception as exc:
        logger.warning("event=review_queue_update_failed source_document_id=%s reason=%s", document_id, exc)


def _request_mf_document_reparse(document_id: str, reviewer_notes: str | None = None, issue_category: str | None = None) -> dict[str, Any]:
    document = _load_mf_review_document(document_id)
    current_status = str(document.get("parse_status") or "").strip().lower()
    if current_status not in {"needs_review", "failed"}:
        raise ConflictError("document_not_actionable")

    get_admin_repository().table("mf_raw_documents").update(
        {
            "parse_status": "needs_reparse",
            "validation_issues": [],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ).eq("id", document_id).execute()
    _mark_review_queue(document_id, "reparse_requested", reviewer_notes, issue_category)
    return {
        "status": "ok",
        "action": "reparse_requested",
        "source_document_id": document_id,
        "parse_status": "needs_reparse",
    }


def _resolve_mf_document_review(document_id: str, reviewer_notes: str | None = None, issue_category: str | None = None) -> dict[str, Any]:
    document = _load_mf_review_document(document_id)
    current_status = str(document.get("parse_status") or "").strip().lower()
    if current_status != "needs_review":
        raise ConflictError("document_not_in_needs_review")

    now = datetime.now(timezone.utc).isoformat()
    get_admin_repository().table("mf_raw_documents").update(
        {
            "parse_status": "parsed",
            "validation_issues": [],
            "parsed_at": now,
            "updated_at": now,
        }
    ).eq("id", document_id).execute()
    _mark_review_queue(document_id, "approved", reviewer_notes, issue_category)
    return {
        "status": "ok",
        "action": "resolved",
        "source_document_id": document_id,
        "parse_status": "parsed",
    }


def _skip_mf_document_review(document_id: str, reviewer_notes: str | None = None, issue_category: str | None = None) -> dict[str, Any]:
    document = _load_mf_review_document(document_id)
    current_status = str(document.get("parse_status") or "").strip().lower()
    if current_status not in {"needs_review", "failed", "needs_reparse"}:
        raise ConflictError("document_not_actionable")

    issues = document.get("validation_issues") if isinstance(document.get("validation_issues"), list) else []
    cleaned_issues = [str(issue) for issue in issues if str(issue or "").strip()]
    if "skipped_irrelevant_document" not in cleaned_issues:
        cleaned_issues.append("skipped_irrelevant_document")

    now = datetime.now(timezone.utc).isoformat()
    get_admin_repository().table("mf_raw_documents").update(
        {
            "parse_status": "skipped_not_supported",
            "validation_issues": cleaned_issues,
            "parsed_at": now,
            "updated_at": now,
        }
    ).eq("id", document_id).execute()
    _mark_review_queue(document_id, "skipped", reviewer_notes, issue_category)
    return {
        "status": "ok",
        "action": "skipped",
        "source_document_id": document_id,
        "parse_status": "skipped_not_supported",
    }


def data_health():
    now_utc = datetime.now(timezone.utc)
    metrics = [
        {"label": "MF NAV", "status": "Missing", "note": "No NAV snapshot rows found.", "last_updated": None},
        {"label": "AUM / TER", "status": "Missing", "note": "No AUM+TER rows found.", "last_updated": None},
        {"label": "Risk metrics", "status": "Missing", "note": "No risk metric rows found.", "last_updated": None},
        {"label": "AMC docs", "status": "Missing", "note": "No parsed AMC factsheet/disclosure docs found.", "last_updated": None},
    ]
    amc_parser_quality: list[dict[str, Any]] = _build_amc_parser_quality([], [], [])
    mf_metric_coverage = _empty_mf_metric_coverage()

    if not get_admin_repository():
        return {
            "status": "degraded",
            "source": "supabase_unavailable",
            "checked_at": now_utc.isoformat(),
            "metrics": metrics,
            "amc_parser_quality": amc_parser_quality,
            "mf_metric_coverage": mf_metric_coverage,
        }

    try:
        core_rows = (
            get_admin_repository().table("mutual_fund_core_snapshot")
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
            "amc_parser_quality": amc_parser_quality,
            "mf_metric_coverage": mf_metric_coverage,
        }

    try:
        enrichment_rows = (
            get_admin_repository().table("mutual_fund_core_snapshot")
            .select("scheme_code,scheme_name,amc_name,last_updated,aum,expense_ratio,benchmark,risk_level")
            .order("last_updated", desc=True)
            .limit(5000)
            .execute()
            .data
            or []
        )
    except Exception as exc:
        logger.warning("Data health enrichment coverage read failed: %s", exc)
        enrichment_rows = core_rows

    latest_nav_dt = _latest_core_snapshot_nav_date() or max(
        [dt for dt in (_to_utc_datetime(row.get("nav_date")) for row in core_rows) if dt is not None],
        default=None,
    )
    nav_age_days = _age_days(latest_nav_dt, now_utc)
    if latest_nav_dt:
        nav_freshness = assess_nav_freshness(latest_nav_dt, now=now_utc)
        expected_nav_date = nav_freshness["expected_nav_date"]
        missed_business_days = nav_freshness["missed_business_days"]
        if nav_freshness["status"] == "fresh":
            metrics[0].update(status="Fresh", note=f"Latest NAV date {latest_nav_dt.date().isoformat()} matches the last expected business day {expected_nav_date}.", last_updated=latest_nav_dt.isoformat())
        elif nav_freshness["status"] == "lagging":
            metrics[0].update(status="Lagging", note=f"Latest NAV date {latest_nav_dt.date().isoformat()} is {missed_business_days} business day behind expected {expected_nav_date}.", last_updated=latest_nav_dt.isoformat())
        else:
            metrics[0].update(status="Stale", note=f"Latest NAV date {latest_nav_dt.date().isoformat()} is {missed_business_days} business days behind expected {expected_nav_date}.", last_updated=latest_nav_dt.isoformat())

    enrichment = _core_snapshot_enrichment_summary(enrichment_rows)
    mf_metric_coverage = _mf_metric_coverage(now_utc)
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
    raw_document_rows: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    try:
        try:
            raw_document_rows = (
                get_admin_repository().table("mf_raw_documents")
                .select("amc_code,source_document_type,parse_status,report_month,downloaded_at,parsed_at")
                .order("downloaded_at", desc=True)
                .limit(5000)
                .execute()
                .data
                or []
            )
        except Exception as exc:
            logger.warning("Data health AMC quality document rows read failed: %s", exc)
            raw_document_rows = []

        try:
            review_rows = (
                get_admin_repository().table("mf_parse_review_queue")
                .select("amc_code,status,report_month")
                .order("report_month", desc=True)
                .limit(5000)
                .execute()
                .data
                or []
            )
        except Exception as exc:
            logger.warning("Data health AMC quality review rows read failed: %s", exc)
            review_rows = []

        amc_parser_quality = _build_amc_parser_quality(enrichment_rows, raw_document_rows, review_rows)
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
        "amc_parser_quality": amc_parser_quality,
        "mf_metric_coverage": mf_metric_coverage,
    }


def admin_ops_overview(x_admin_key: str | None = Header(default=None, alias="X-Admin-Key")):
    _require_admin_key(x_admin_key)
    now_utc = datetime.now(timezone.utc)
    if not get_admin_repository():
        raise DataUnavailableError("supabase_unavailable")

    workflow_runs: list[dict[str, Any]] = []
    workflow_source_table = "data_provider_runs"
    try:
        rows = (
            get_admin_repository().table("data_provider_runs")
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
                get_admin_repository().table("provider_runs")
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
        elif status in {"failed", "error", "partial_failed", "timeout", "timed_out"}:
            failures_24h += 1

    mf_pipeline_rows: list[dict[str, Any]] = []
    try:
        raw_rows = (
            get_admin_repository().table("mf_raw_documents")
            .select("amc_code,source_document_type,parse_status,downloaded_at,parsed_at,updated_at")
            .order("downloaded_at", desc=True)
            .limit(5000)
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
            get_admin_repository().table("data_quality_issues")
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
                get_admin_repository().table("mf_raw_documents")
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
                get_admin_repository().table("mf_parse_review_queue")
                .select("id", count="exact")
                .eq("status", "pending_review")
                .execute()
                .count
            )
            or 0
        )
    except Exception:
        mf_review_queue = 0

    try:
        quality_core_rows = (
            get_admin_repository().table("mutual_fund_core_snapshot")
            .select("scheme_code,scheme_name,amc_name,expense_ratio,benchmark,risk_level")
            .order("last_updated", desc=True)
            .limit(5000)
            .execute()
            .data
            or []
        )
    except Exception:
        quality_core_rows = []

    try:
        quality_review_rows = (
            get_admin_repository().table("mf_parse_review_queue")
            .select("amc_code,status,report_month")
            .order("report_month", desc=True)
            .limit(5000)
            .execute()
            .data
            or []
        )
    except Exception:
        quality_review_rows = []

    amc_parser_quality = _build_amc_parser_quality(quality_core_rows, raw_rows, quality_review_rows)

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
        "amc_parser_quality": amc_parser_quality,
    }


def admin_mf_review_priorities(limit: int, x_admin_key: str | None) -> dict[str, Any]:
    _require_admin_key(x_admin_key)
    repository = get_admin_repository()
    if not repository:
        raise DataUnavailableError("supabase_unavailable")
    return ReviewPriorityService(repository).list_prioritized(limit=limit)


def admin_request_mf_document_reparse(
    document_id: str,
    payload: AdminDocumentReviewAction | None = None,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    return _request_mf_document_reparse(document_id, _review_action_notes(payload), _review_issue_category(payload))


def admin_resolve_mf_document_review(
    document_id: str,
    payload: AdminDocumentReviewAction | None = None,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    return _resolve_mf_document_review(document_id, _review_action_notes(payload), _review_issue_category(payload))


def admin_skip_mf_document_review(
    document_id: str,
    payload: AdminDocumentReviewAction | None = None,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    return _skip_mf_document_review(document_id, _review_action_notes(payload), _review_issue_category(payload))


def admin_mf_resolver_debug(
    query: str = Query(..., min_length=2),
    horizon: str = Query("3Y", pattern="^(1Y|3Y|5Y)$"),
    limit: int = Query(20, ge=5, le=50),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    if not get_admin_repository():
        raise DataUnavailableError("supabase_unavailable")

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
    if not words:
        return {
            "input_query": query_text,
            "normalized_query": normalized_query,
            "selected_candidate": None,
            "top_candidates": [],
            "scoring_breakdown": {
                "horizon": horizon,
                "min_history_points": _resolver_horizon_to_min_points(horizon),
                "error": "empty_search_pattern_after_normalization",
            },
        }
    search_pattern = f"%{'%'.join(words)}%"

    rows = (
        get_admin_repository().table("mutual_fund_core_snapshot")
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


def admin_mf_promotion_review_flags(
    amc: str = Query(...),
    scope: str = Query(..., pattern="^(risk|holdings)$"),
    report_month: str = Query(...),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    from app.mf_ingestion.services import promotion_review_service as review_service

    if not get_admin_repository():
        raise DataUnavailableError("supabase_unavailable")

    if scope == "risk":
        rows = review_service.find_risk_conflicts(amc=amc, report_month=report_month)
    else:
        rows = review_service.find_holdings_out_of_band(amc=amc, report_month=report_month)
    return {"status": "ok", "amc": amc, "scope": scope, "report_month": report_month, "count": len(rows), "rows": rows}


def admin_mf_promotion_review_decide(
    payload: PromotionReviewDecisionRequest,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    from app.mf_ingestion.services import promotion_review_service as review_service

    if not get_admin_repository():
        raise DataUnavailableError("supabase_unavailable")

    try:
        decision = review_service.upsert_decision(
            amc=payload.amc,
            report_month=payload.report_month,
            scope=payload.scope,
            subject_key=payload.subject_key,
            subject_label=payload.subject_label,
            resolution=payload.resolution,
            decided_value=payload.decided_value,
            source_document_id=payload.source_document_id,
            reviewed_by=payload.reviewed_by,
            note=payload.note,
        )
    except ValueError as exc:
        raise ConflictError(str(exc)) from exc
    return {"status": "ok", "decision": decision}


def admin_mf_promotion_review_promote(
    payload: PromotionReviewPromoteRequest,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
):
    _require_admin_key(x_admin_key)
    from app.mf_ingestion.services import promotion_review_service as review_service

    repository = get_admin_repository()
    if not repository:
        raise DataUnavailableError("supabase_unavailable")

    decision_rows = (
        repository.table("mf_promotion_review_decisions")
        .select("scope")
        .eq("id", payload.decision_id)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not decision_rows:
        raise EntityNotFoundError("decision_not_found")
    scope = decision_rows[0]["scope"]
    if scope == "risk":
        result = review_service.promote_risk_decision(decision_id=payload.decision_id, requested_by=payload.requested_by)
    else:
        result = review_service.promote_holdings_decision(decision_id=payload.decision_id, requested_by=payload.requested_by)
    if result.get("status") != "ok":
        raise ConflictError(result.get("reason", "promotion_failed"))
    return result


def admin_pending_promotion_review_count(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
) -> dict[str, Any]:
    """Cheap cross-AMC count of mf_promotion_review_decisions rows still awaiting the
    Promote step (promoted_at is null), broken down by AMC and resolution. Feeds the
    Issues tab's link-out to Promotion Review without duplicating its per-AMC/scope
    flag-finding logic."""
    _require_admin_key(x_admin_key)
    repository = get_admin_repository()
    if not repository:
        raise DataUnavailableError("supabase_unavailable")

    rows = (
        repository.table("mf_promotion_review_decisions")
        .select("amc_code,scope,resolution")
        .is_("promoted_at", "null")
        .execute()
        .data
        or []
    )

    by_amc: dict[str, dict[str, int]] = {}
    actionable_total = 0
    for row in rows:
        amc_code = str(row.get("amc_code") or "unknown")
        resolution = str(row.get("resolution") or "unknown")
        bucket = by_amc.setdefault(amc_code, {"use_staged": 0, "use_live": 0, "exclude": 0})
        bucket[resolution] = bucket.get(resolution, 0) + 1
        if resolution == "use_staged":
            actionable_total += 1

    pending_by_amc = [
        {"amc_code": amc_code, **counts} for amc_code, counts in sorted(by_amc.items())
    ]
    return {
        "status": "ok",
        "total_pending": len(rows),
        "actionable_pending": actionable_total,
        "pending_by_amc": pending_by_amc,
    }


def provider_usage_dashboard():
    enabled = os.getenv("ENABLE_PROVIDER_USAGE_ENDPOINT", "false").strip().lower() in {"1", "true", "yes", "on"}
    if not enabled:
        raise EntityNotFoundError("Provider usage endpoint is disabled.")

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


class DataHealthService:
    def __init__(self, repository: AdminOpsRepository | None = None):
        self.repository = repository or _default_admin_repository

    def get_data_health(self) -> dict[str, Any]:
        token = _current_admin_repository.set(self.repository)
        try:
            return data_health()
        finally:
            _current_admin_repository.reset(token)


class AdminService:
    def __init__(self, repository: AdminOpsRepository | None = None):
        self.repository = repository or _default_admin_repository

    def ops_overview(self, x_admin_key: str | None) -> dict[str, Any]:
        token = _current_admin_repository.set(self.repository)
        try:
            return admin_ops_overview(x_admin_key)
        finally:
            _current_admin_repository.reset(token)

    def review_priorities(self, limit: int, x_admin_key: str | None) -> dict[str, Any]:
        token = _current_admin_repository.set(self.repository)
        try:
            return admin_mf_review_priorities(limit, x_admin_key)
        finally:
            _current_admin_repository.reset(token)

    def request_reparse(self, document_id: str, payload: AdminDocumentReviewAction | None, x_admin_key: str | None) -> dict[str, Any]:
        token = _current_admin_repository.set(self.repository)
        try:
            return admin_request_mf_document_reparse(document_id, payload, x_admin_key)
        finally:
            _current_admin_repository.reset(token)

    def resolve_review(self, document_id: str, payload: AdminDocumentReviewAction | None, x_admin_key: str | None) -> dict[str, Any]:
        token = _current_admin_repository.set(self.repository)
        try:
            return admin_resolve_mf_document_review(document_id, payload, x_admin_key)
        finally:
            _current_admin_repository.reset(token)

    def skip_review(self, document_id: str, payload: AdminDocumentReviewAction | None, x_admin_key: str | None) -> dict[str, Any]:
        token = _current_admin_repository.set(self.repository)
        try:
            return admin_skip_mf_document_review(document_id, payload, x_admin_key)
        finally:
            _current_admin_repository.reset(token)

    def resolver_debug(self, query: str, horizon: str, limit: int, x_admin_key: str | None) -> dict[str, Any]:
        token = _current_admin_repository.set(self.repository)
        try:
            return admin_mf_resolver_debug(query, horizon, limit, x_admin_key)
        finally:
            _current_admin_repository.reset(token)

    def promotion_review_flags(self, amc: str, scope: str, report_month: str, x_admin_key: str | None) -> dict[str, Any]:
        return admin_mf_promotion_review_flags(amc, scope, report_month, x_admin_key)

    def promotion_review_decide(self, payload: PromotionReviewDecisionRequest, x_admin_key: str | None) -> dict[str, Any]:
        return admin_mf_promotion_review_decide(payload, x_admin_key)

    def promotion_review_promote(self, payload: PromotionReviewPromoteRequest, x_admin_key: str | None) -> dict[str, Any]:
        return admin_mf_promotion_review_promote(payload, x_admin_key)

    def promotion_review_pending_count(self, x_admin_key: str | None) -> dict[str, Any]:
        return admin_pending_promotion_review_count(x_admin_key)


class ProviderUsageService:
    def usage_dashboard(self) -> dict[str, Any]:
        return provider_usage_dashboard()
