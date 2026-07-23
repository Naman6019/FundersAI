from __future__ import annotations

from datetime import date
from typing import Any

from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument
from app.mf_ingestion.sources.registry import AMCDocumentSource


def load_last_known_good_documents(
    supabase_client: Any,
    source: AMCDocumentSource,
    document_type: str,
) -> list[DiscoveredDocument]:
    """Read only previously promotable official documents; failures stay non-fatal."""
    if supabase_client is None:
        return []
    response = (
        supabase_client.table("mf_discovery_documents")
        .select("amc,document_type,report_month,source_url,discovery_page_url,evidence,observed_at")
        .eq("amc", source.amc_code)
        .eq("document_type", document_type)
        .eq("readiness", "promotable")
        .order("observed_at", desc=True)
        .limit(3)
        .execute()
    )
    documents: list[DiscoveredDocument] = []
    seen_urls: set[str] = set()
    for row in getattr(response, "data", None) or []:
        url = str(row.get("source_url") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        evidence = row.get("evidence") or {}
        documents.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type=document_type,
                title=str(evidence.get("title") or "Last known good document"),
                url=url,
                discovery_page_url=str(row.get("discovery_page_url") or url),
                file_ext=str(evidence.get("expected_file_type") or ".pdf"),
                report_month=_parse_date(row.get("report_month")),
                priority_score=8_000_000,
            )
        )
    return documents


def build_discovery_diff(
    previous_documents: list[dict[str, Any]],
    current_documents: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Return only meaningful source and readiness changes by monthly identity."""
    previous = {_identity(document): document for document in previous_documents if _identity(document)}
    current = {_identity(document): document for document in current_documents if _identity(document)}
    added = [current[key] for key in current.keys() - previous.keys()]
    removed = [previous[key] for key in previous.keys() - current.keys()]
    changed: list[dict[str, Any]] = []
    for key in current.keys() & previous.keys():
        old = previous[key]
        new = current[key]
        fields = ("source_url", "content_sha256", "discovery_agent_status", "month_confirmation")
        delta = {field: {"before": old.get(field), "after": new.get(field)} for field in fields if old.get(field) != new.get(field)}
        if delta:
            changed.append({"identity": key, "changes": delta})
    return {"added": added, "removed": removed, "changed": changed}


def load_recent_document_observations(
    supabase_client: Any,
    *,
    amcs: list[str],
    document_types: tuple[str, ...],
) -> list[dict[str, Any]]:
    if supabase_client is None:
        return []
    response = (
        supabase_client.table("mf_discovery_documents")
        .select("amc,document_type,report_month,source_url,content_sha256,readiness,month_confirmation,observed_at")
        .in_("amc", amcs)
        .in_("document_type", list(document_types))
        .order("observed_at", desc=True)
        .limit(250)
        .execute()
    )
    return [
        {
            **row,
            "discovery_agent_status": row.get("readiness"),
        }
        for row in (getattr(response, "data", None) or [])
    ]


def build_source_configuration_candidates(documents: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Stage, never apply, source updates after three promotable observations."""
    counts: dict[tuple[str, str, str], int] = {}
    candidates: list[dict[str, Any]] = []
    for document in documents:
        if document.get("discovery_agent_status") != "promotable":
            continue
        key = (str(document.get("amc") or ""), str(document.get("document_type") or ""), str(document.get("source_url") or ""))
        if not all(key):
            continue
        counts[key] = counts.get(key, 0) + 1
        if counts[key] == 3:
            candidates.append(
                {
                    "amc": key[0],
                    "document_type": key[1],
                    "source_url": key[2],
                    "state": "staged_for_review",
                    "consecutive_promotable_runs": 3,
                }
            )
    return candidates


def _identity(document: dict[str, Any]) -> str:
    amc = str(document.get("amc") or "").strip()
    document_type = str(document.get("document_type") or "").strip()
    report_month = str(document.get("report_month") or "").strip()
    return "|".join((amc, document_type, report_month)) if all((amc, document_type, report_month)) else ""


def _parse_date(value: object) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None
