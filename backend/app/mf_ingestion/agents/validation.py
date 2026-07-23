from __future__ import annotations

from datetime import date
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument, DownloadedDocument
from app.mf_ingestion.sources.registry import AMCDocumentSource

SUPPORTED_DOCUMENT_TYPES = {"factsheet", "portfolio_disclosure"}
SUPPORTED_EXTENSIONS = {".pdf", ".xls", ".xlsx", ".xlsm", ".csv", ".zip", ".html", ".htm"}

EXTRA_OFFICIAL_HOST_SUFFIXES: dict[str, tuple[str, ...]] = {
    "aditya_birla": ("adityabirlacapital.com",),
    "axis": ("axismf.com",),
    "dsp": ("dspim.com",),
    "hdfc": ("hdfcfund.com",),
    "icici": ("icicipruamc.com",),
    "kotak": ("kotakmf.com",),
    "mirae": ("miraeassetmf.co.in",),
    "nippon": ("nipponindiaim.com",),
    "ppfas": ("ppfas.com",),
    "sbi": ("sbimf.com",),
    "uti": ("utimf.com", "d3ce1o48hc5oli.cloudfront.net"),
}


def validate_candidate(
    source: AMCDocumentSource,
    document: DiscoveredDocument,
    *,
    expected_month: date | None,
    expected_month_grace_days: int = 14,
    observed_on: date | None = None,
) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    document_type = str(document.document_type or "").strip().lower()

    if document_type not in SUPPORTED_DOCUMENT_TYPES:
        errors.append(f"unsupported_document_type:{document_type or 'missing'}")

    parsed = urlsplit(str(document.url or ""))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        errors.append("invalid_source_url")
    elif not _is_official_host(source, parsed.hostname):
        errors.append(f"non_official_host:{parsed.hostname.lower()}")

    extension = _normalize_extension(document.file_ext or document.url)
    if extension not in SUPPORTED_EXTENSIONS:
        errors.append(f"unsupported_file_type:{extension or 'missing'}")

    if document.report_month is None:
        warnings.append("report_month_unknown")
    elif expected_month and _month_index(document.report_month) != _month_index(expected_month):
        grace_deadline = date(
            expected_month.year,
            expected_month.month,
            min(max(int(expected_month_grace_days), 1), 28),
        )
        if (observed_on or date.today()) <= grace_deadline:
            warnings.append(f"report_month_pending_expected:{document.report_month.isoformat()}")
        elif _month_index(document.report_month) < _month_index(expected_month):
            warnings.append(f"report_month_before_expected:{document.report_month.isoformat()}")
        else:
            warnings.append(f"report_month_after_expected:{document.report_month.isoformat()}")

    if not str(document.discovery_page_url or "").strip():
        warnings.append("discovery_page_unknown")

    return errors, warnings


def validate_download(
    source: AMCDocumentSource,
    downloaded: DownloadedDocument,
) -> list[str]:
    errors: list[str] = []
    parsed = urlsplit(str(downloaded.source_url or ""))
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        errors.append("invalid_download_url")
    elif not _is_official_host(source, parsed.hostname):
        errors.append(f"download_redirected_to_non_official_host:{parsed.hostname.lower()}")

    if downloaded.file_size_bytes <= 0 or not downloaded.file_bytes:
        errors.append("empty_download")
        return errors

    extension = _normalize_extension(downloaded.file_ext or downloaded.file_name)
    head = downloaded.file_bytes[:512].lstrip().lower()
    if head.startswith((b"<!doctype html", b"<html")) or b"<title>" in head:
        errors.append("html_response")
    elif extension == ".pdf" and not downloaded.file_bytes.startswith(b"%PDF-"):
        errors.append("invalid_pdf_body")
    elif extension in {".xlsx", ".xlsm", ".zip"} and not downloaded.file_bytes.startswith(b"PK"):
        errors.append("invalid_zip_body")
    elif extension == ".xls" and not downloaded.file_bytes.startswith(b"\xd0\xcf\x11\xe0"):
        errors.append("invalid_xls_body")

    return errors


def validate_parser_smoke(downloaded: DownloadedDocument) -> list[str]:
    """Check that a validated body is structurally readable without ingesting it."""
    extension = _normalize_extension(downloaded.file_ext or downloaded.file_name)
    if extension == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(downloaded.file_bytes), strict=False)
            if not reader.pages:
                return ["parser_smoke_pdf_no_pages"]
        except Exception as exc:
            return [f"parser_smoke_pdf_failed:{type(exc).__name__}"]
    elif extension in {".xlsx", ".xlsm"}:
        try:
            from openpyxl import load_workbook

            workbook = load_workbook(BytesIO(downloaded.file_bytes), read_only=True, data_only=True)
            if not workbook.sheetnames:
                return ["parser_smoke_excel_no_sheets"]
            workbook.close()
        except Exception as exc:
            return [f"parser_smoke_excel_failed:{type(exc).__name__}"]
    elif extension == ".xls":
        # The compound-file signature was checked above. Full XLS parsing remains
        # owned by the existing ingestion parser, which supports its configured engine.
        return []
    return []


def content_sha256(downloaded: DownloadedDocument) -> str:
    return sha256(downloaded.file_bytes).hexdigest()


def _is_official_host(source: AMCDocumentSource, hostname: str) -> bool:
    host = hostname.strip().lower().rstrip(".")
    allowed = set(EXTRA_OFFICIAL_HOST_SUFFIXES.get(source.adapter_key.lower(), ()))
    for raw_url in (source.factsheet_page_url, source.portfolio_disclosure_page_url):
        parsed = urlsplit(str(raw_url or ""))
        if parsed.hostname:
            allowed.add(parsed.hostname.lower())

    return any(host == suffix or host.endswith(f".{suffix}") for suffix in allowed)


def _normalize_extension(value: object) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    if raw.startswith(".") and "/" not in raw:
        return raw
    return Path(raw.split("?", 1)[0]).suffix.lower()


def _month_index(value: date) -> int:
    return value.year * 12 + value.month
