from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.mf_ingestion.services.source_manifest import load_source_manifest_documents
from app.mf_ingestion.sources.registry import get_source

DOCUMENT_TYPES = ("factsheet", "portfolio_disclosure")
DEFAULT_MANIFEST_PATH = "backend/config/mf_document_sources.json"
ALLOWED_EXTENSIONS = {".pdf", ".xls", ".xlsx", ".xlsm", ".html", ".htm"}


@dataclass(frozen=True)
class LinkCandidate:
    amc: str
    document_type: str
    source_url: str
    expected_file_type: str
    report_month: date | None
    source: str


def collect_link_candidates(
    *,
    amcs: list[str],
    manifest_path: str,
    env: dict[str, str] | None = None,
) -> list[LinkCandidate]:
    env = env or dict(os.environ)
    candidates: list[LinkCandidate] = []
    for amc in amcs:
        source = get_source(amc)
        for document_type in DOCUMENT_TYPES:
            for doc in load_source_manifest_documents(manifest_path, source, document_type):
                candidates.append(
                    LinkCandidate(
                        amc=source.amc_code,
                        document_type=document_type,
                        source_url=doc.url,
                        expected_file_type=doc.file_ext,
                        report_month=doc.report_month,
                        source="manifest",
                    )
                )
            for url in _env_document_urls(source.amc_code, document_type, env):
                candidates.append(
                    LinkCandidate(
                        amc=source.amc_code,
                        document_type=document_type,
                        source_url=url,
                        expected_file_type=_extension_from_url(url, default=".pdf" if document_type == "factsheet" else ".xlsx"),
                        report_month=None,
                        source="env",
                    )
                )
    return _dedupe_candidates(candidates)


def validate_link(
    candidate: LinkCandidate,
    *,
    session: Any,
    timeout_seconds: float,
    max_stale_months: int,
    today: date | None = None,
) -> dict[str, Any]:
    parsed = urlparse(candidate.source_url)
    result: dict[str, Any] = {
        "amc": candidate.amc,
        "document_type": candidate.document_type,
        "source": candidate.source,
        "source_url": candidate.source_url,
        "status": "ok",
        "warnings": [],
    }
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        result["status"] = "error"
        result["reason"] = "invalid_url"
        return result

    expected_ext = _normalize_extension(candidate.expected_file_type)
    actual_ext = _extension_from_url(candidate.source_url)
    if expected_ext and actual_ext and expected_ext != actual_ext:
        result["status"] = "error"
        result["reason"] = f"extension_mismatch:{expected_ext}!={actual_ext}"
        return result
    if expected_ext and expected_ext not in ALLOWED_EXTENSIONS:
        result["status"] = "error"
        result["reason"] = f"unsupported_extension:{expected_ext}"
        return result

    try:
        response = session.get(
            candidate.source_url,
            headers={"User-Agent": os.getenv("MF_INGESTION_USER_AGENT", "FundersAIResearchBot/1.0")},
            timeout=timeout_seconds,
        )
    except Exception as exc:
        result["status"] = "error"
        result["reason"] = f"request_failed:{type(exc).__name__}"
        return result

    status_code = int(getattr(response, "status_code", 0) or 0)
    result["http_status"] = status_code
    if status_code >= 400:
        result["status"] = "error"
        result["reason"] = f"http_{status_code}"
        return result

    content = bytes(getattr(response, "content", b"") or b"")
    if not content:
        result["status"] = "error"
        result["reason"] = "empty_body"
        return result

    content_type = str(getattr(response, "headers", {}).get("Content-Type", "") or "").lower()
    result["content_type"] = content_type
    if expected_ext not in {".html", ".htm"} and ("text/html" in content_type or content.lstrip().lower().startswith((b"<html", b"<!doctype"))):
        result["status"] = "error"
        result["reason"] = "html_response"
        return result

    stale_warning = _freshness_warning(candidate.report_month, max_stale_months=max_stale_months, today=today)
    if stale_warning:
        result["warnings"].append(stale_warning)
    return result


def run_preflight(
    *,
    amcs: list[str],
    manifest_path: str,
    timeout_seconds: float = 20.0,
    max_stale_months: int = 2,
    require_links: bool = False,
    session: Any | None = None,
) -> dict[str, Any]:
    candidates = collect_link_candidates(amcs=amcs, manifest_path=manifest_path, env=dict(os.environ))
    session = session or requests.Session()
    results = [
        validate_link(
            candidate,
            session=session,
            timeout_seconds=timeout_seconds,
            max_stale_months=max_stale_months,
        )
        for candidate in candidates
    ]
    missing_amcs = sorted({amc.upper() for amc in amcs} - {str(item.get("amc") or "").upper() for item in results})
    warnings = []
    if missing_amcs:
        warnings.append(f"no_links_found:{','.join(missing_amcs)}")
    status = "ok"
    if any(item.get("status") == "error" for item in results) or (require_links and missing_amcs):
        status = "error"
    return {"status": status, "results": results, "warnings": warnings}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--amcs", default="axis,hdfc,sbi,icici,ppfas,nippon")
    parser.add_argument("--manifest-path", default=os.getenv("MF_SOURCE_MANIFEST_PATH") or DEFAULT_MANIFEST_PATH)
    parser.add_argument("--timeout-seconds", type=float, default=20.0)
    parser.add_argument("--max-stale-months", type=int, default=2)
    parser.add_argument("--require-links", action="store_true")
    args = parser.parse_args()

    amcs = [token.strip().lower() for token in args.amcs.split(",") if token.strip()]
    report = run_preflight(
        amcs=amcs,
        manifest_path=args.manifest_path,
        timeout_seconds=args.timeout_seconds,
        max_stale_months=args.max_stale_months,
        require_links=args.require_links,
    )
    print(json.dumps(report, indent=2, default=str))
    return 1 if report["status"] == "error" else 0


def _env_document_urls(amc_code: str, document_type: str, env: dict[str, str]) -> list[str]:
    suffix = "FACTSHEET_DOCUMENT_URLS" if document_type == "factsheet" else "PORTFOLIO_DOCUMENT_URLS"
    raw = env.get(f"MF_{amc_code.upper()}_{suffix}", "")
    if document_type == "portfolio_disclosure" and not raw.strip():
        allow_reuse = str(env.get("MF_ALLOW_FACTSHEET_AS_PORTFOLIO") or env.get("MF_ALLOW_HDFC_FACTSHEET_AS_PORTFOLIO") or "").lower()
        if allow_reuse in {"1", "true", "yes", "on"}:
            raw = env.get(f"MF_{amc_code.upper()}_FACTSHEET_DOCUMENT_URLS", "")
    urls: list[str] = []
    for token in raw.split(","):
        value = token.strip()
        if value and value not in urls:
            urls.append(value)
    return urls


def _dedupe_candidates(candidates: list[LinkCandidate]) -> list[LinkCandidate]:
    deduped: list[LinkCandidate] = []
    seen: set[tuple[str, str, str]] = set()
    for item in candidates:
        key = (item.amc.lower(), item.document_type.lower(), item.source_url.lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _normalize_extension(value: str) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    if raw.startswith(".") and "/" not in raw:
        return raw
    return _extension_from_url(raw)


def _extension_from_url(url: str, default: str = "") -> str:
    suffix = Path(urlparse(str(url or "").split("?", 1)[0]).path).suffix.lower()
    return suffix or default


def _freshness_warning(report_month: date | None, *, max_stale_months: int, today: date | None = None) -> str | None:
    if not report_month:
        return None
    today = today or datetime.now(timezone.utc).date()
    month_delta = (today.year - report_month.year) * 12 + today.month - report_month.month
    if month_delta > max(max_stale_months, 0):
        return f"stale_report_month:{report_month.isoformat()}"
    return None


if __name__ == "__main__":
    raise SystemExit(main())
