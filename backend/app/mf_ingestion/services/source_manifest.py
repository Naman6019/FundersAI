from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any

from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument
from app.mf_ingestion.sources.registry import AMCDocumentSource


def load_source_manifest_documents(
    manifest_path: str,
    source: AMCDocumentSource,
    document_type: str,
) -> list[DiscoveredDocument]:
    raw_path = str(manifest_path or "").strip()
    if not raw_path:
        return []
    path = Path(raw_path)
    if not path.exists():
        return []

    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("documents", payload) if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return []

    docs: list[DiscoveredDocument] = []
    wanted_amc = str(source.amc_code or "").strip().lower()
    wanted_type = str(document_type or "").strip().lower()
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_amc = str(row.get("amc") or row.get("amc_code") or "").strip().lower()
        row_type = str(row.get("document_type") or "").strip().lower()
        if row_amc and row_amc != wanted_amc:
            continue
        if row_type and row_type != wanted_type:
            continue
        source_url = str(row.get("source_url") or row.get("url") or "").strip()
        if not source_url:
            continue

        expected_ext = _normalize_extension(row.get("expected_file_type") or row.get("file_ext") or source_url)
        docs.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type=wanted_type or row_type,
                title=str(row.get("title") or Path(source_url.split("?", 1)[0]).name or source_url),
                url=source_url,
                discovery_page_url=str(row.get("discovery_page_url") or f"manifest://{path.as_posix()}"),
                file_ext=expected_ext,
                report_month=_parse_manifest_month(row.get("report_month")),
                priority_score=float(row.get("priority_score") or 1000),
            )
        )
    return docs


def build_source_manifest(
    *,
    source: AMCDocumentSource,
    document_type: str,
    source_url: str,
    discovery_page_url: str | None,
    report_month: date | None,
    expected_file_type: str,
    checksum: str,
    acquisition_status: str,
) -> dict[str, Any]:
    return {
        "amc": source.amc_code,
        "document_type": document_type,
        "report_month": report_month.isoformat() if report_month else None,
        "source_url": source_url,
        "discovery_page_url": discovery_page_url,
        "expected_file_type": _normalize_extension(expected_file_type),
        "checksum": checksum,
        "acquisition_status": acquisition_status,
    }


def _parse_manifest_month(value: object) -> date | None:
    if value in (None, ""):
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            parsed = datetime.strptime(raw, fmt)
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            continue
    return None


def _normalize_extension(value: object) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    suffix = Path(raw.split("?", 1)[0]).suffix.lower()
    if suffix:
        return suffix
    if raw.startswith("."):
        return raw
    return f".{raw}"
