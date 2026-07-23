from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from typing import Any

from app.mf_ingestion.storage.r2_store import R2Store


def persist_discovery_run(
    payload: dict[str, Any],
    *,
    run_id: str,
    trigger_source: str,
    expected_month: str | None,
    requested_amcs: list[str],
    document_types: tuple[str, ...],
    r2_store: R2Store,
    r2_bucket: str,
    supabase_client: Any,
) -> dict[str, Any]:
    if not r2_store.enabled:
        raise RuntimeError("discovery_run_r2_not_configured")
    if not r2_bucket.strip():
        raise RuntimeError("discovery_run_r2_bucket_not_configured")
    if supabase_client is None:
        raise RuntimeError("discovery_run_supabase_not_configured")

    completed_at = _parse_timestamp(payload.get("completed_at"))
    key_prefix = (
        f"agent-discovery/{completed_at:%Y/%m/%d}/{run_id}"
    )
    report_bytes = _render_json(payload)
    manifest_bytes = _render_json(payload.get("manifest") or {})
    report_sha256 = sha256(report_bytes).hexdigest()
    manifest_sha256 = sha256(manifest_bytes).hexdigest()
    report_key = f"{key_prefix}/report-{report_sha256}.json"
    manifest_key = f"{key_prefix}/manifest-{manifest_sha256}.json"
    metadata = {
        "run_id": run_id,
        "status": str(payload.get("status") or "unknown"),
        "trigger_source": trigger_source,
        "report_sha256": report_sha256,
        "manifest_sha256": manifest_sha256,
    }

    report_upload = {"bucket": r2_bucket, "key": report_key}
    manifest_upload = {"bucket": r2_bucket, "key": manifest_key}
    summary = build_discovery_run_summary(
        payload,
        run_id=run_id,
        trigger_source=trigger_source,
        expected_month=expected_month,
        requested_amcs=requested_amcs,
        document_types=document_types,
        report_upload=report_upload,
        manifest_upload=manifest_upload,
        report_sha256=report_sha256,
        manifest_sha256=manifest_sha256,
        persistence_state="pending",
    )
    _upsert_run_summary(supabase_client, summary)
    try:
        report_upload = r2_store.upload_bytes(
            report_key,
            report_bytes,
            bucket=r2_bucket,
            content_type="application/json",
            metadata=metadata,
        )
        summary["persistence_state"] = "r2_report_stored"
        _upsert_run_summary(supabase_client, summary)

        manifest_upload = r2_store.upload_bytes(
            manifest_key,
            manifest_bytes,
            bucket=r2_bucket,
            content_type="application/json",
            metadata=metadata,
        )
        summary["persistence_state"] = "r2_manifest_stored"
        _upsert_run_summary(supabase_client, summary)

        documents = build_discovery_document_observations(payload, run_id=run_id)
        for document in documents:
            (
                supabase_client.table("mf_discovery_documents")
                .upsert(document, on_conflict="run_id,source_url")
                .execute()
            )
        summary["persistence_state"] = "complete"
        summary["persistence_error"] = None
        _upsert_run_summary(supabase_client, summary)
        return summary
    except Exception as exc:
        summary["persistence_state"] = "failed"
        summary["persistence_error"] = str(exc)[:1000]
        summary["persistence_retry_count"] = int(summary.get("persistence_retry_count") or 0) + 1
        _upsert_run_summary(supabase_client, summary)
        raise


def _upsert_run_summary(supabase_client: Any, summary: dict[str, Any]) -> None:
    (
        supabase_client.table("mf_discovery_runs")
        .upsert(summary, on_conflict="run_id")
        .execute()
    )


def reconcile_discovery_run(
    payload: dict[str, Any],
    **kwargs: Any,
) -> dict[str, Any]:
    """Replay a run with its stable run ID; checksum-addressed writes are idempotent."""
    return persist_discovery_run(payload, **kwargs)


def build_discovery_run_summary(
    payload: dict[str, Any],
    *,
    run_id: str,
    trigger_source: str,
    expected_month: str | None,
    requested_amcs: list[str],
    document_types: tuple[str, ...],
    report_upload: dict[str, str],
    manifest_upload: dict[str, str],
    report_sha256: str | None = None,
    manifest_sha256: str | None = None,
    persistence_state: str = "complete",
) -> dict[str, Any]:
    agents = list(payload.get("agents") or [])
    status_counts = Counter(str(agent.get("status") or "unknown") for agent in agents)
    manifest = payload.get("manifest") or {}
    documents = list(manifest.get("documents") or [])
    return {
        "run_id": run_id,
        "trigger_source": trigger_source,
        "status": str(payload.get("status") or "failed"),
        "expected_month": expected_month,
        "document_types": list(document_types),
        "requested_amcs": requested_amcs,
        "agent_status_counts": dict(status_counts),
        "completed_agent_count": status_counts.get("completed", 0),
        "document_count": len(documents),
        "report_bucket": report_upload["bucket"],
        "report_key": report_upload["key"],
        "manifest_bucket": manifest_upload["bucket"],
        "manifest_key": manifest_upload["key"],
        "report_sha256": report_sha256,
        "manifest_sha256": manifest_sha256,
        "persistence_state": persistence_state,
        "persistence_error": None,
        "persistence_retry_count": 0,
        "started_at": payload.get("started_at"),
        "completed_at": payload.get("completed_at"),
        "updated_at": datetime.now(UTC).isoformat(),
    }


def build_discovery_document_observations(payload: dict[str, Any], *, run_id: str) -> list[dict[str, Any]]:
    manifest = payload.get("manifest") or {}
    observed_at = payload.get("completed_at") or datetime.now(UTC).isoformat()
    observations: list[dict[str, Any]] = []
    for document in manifest.get("documents") or []:
        source_url = str(document.get("source_url") or "").strip()
        if not source_url:
            continue
        observations.append(
            {
                "run_id": run_id,
                "amc": str(document.get("amc") or "").strip(),
                "document_type": str(document.get("document_type") or "").strip(),
                "report_month": document.get("report_month"),
                "source_url": source_url,
                "discovery_page_url": document.get("discovery_page_url"),
                "content_sha256": document.get("content_sha256"),
                "readiness": document.get("discovery_agent_status") or "needs_review",
                "month_confirmation": document.get("month_confirmation") or "unconfirmed",
                "evidence": document,
                "observed_at": observed_at,
            }
        )
    return observations


def _render_json(payload: object) -> bytes:
    return (json.dumps(payload, indent=2, default=str) + "\n").encode("utf-8")


def _parse_timestamp(value: object) -> datetime:
    text = str(value or "").strip()
    if text:
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
        except ValueError:
            pass
    return datetime.now(UTC)
