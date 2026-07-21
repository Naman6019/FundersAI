from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
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
    report_key = f"{key_prefix}/report.json"
    manifest_key = f"{key_prefix}/manifest.json"
    metadata = {
        "run_id": run_id,
        "status": str(payload.get("status") or "unknown"),
        "trigger_source": trigger_source,
    }

    report_upload = r2_store.upload_bytes(
        report_key,
        _render_json(payload),
        bucket=r2_bucket,
        content_type="application/json",
        metadata=metadata,
    )
    manifest_upload = r2_store.upload_bytes(
        manifest_key,
        _render_json(payload.get("manifest") or {}),
        bucket=r2_bucket,
        content_type="application/json",
        metadata=metadata,
    )

    summary = build_discovery_run_summary(
        payload,
        run_id=run_id,
        trigger_source=trigger_source,
        expected_month=expected_month,
        requested_amcs=requested_amcs,
        document_types=document_types,
        report_upload=report_upload,
        manifest_upload=manifest_upload,
    )
    (
        supabase_client.table("mf_discovery_runs")
        .upsert(summary, on_conflict="run_id")
        .execute()
    )
    return summary


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
        "started_at": payload.get("started_at"),
        "completed_at": payload.get("completed_at"),
        "updated_at": datetime.now(UTC).isoformat(),
    }


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
