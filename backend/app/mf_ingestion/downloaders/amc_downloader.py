from __future__ import annotations

import logging
import os
import re
import time
import uuid
from html import unescape
from datetime import UTC, date, datetime
from calendar import monthrange
from pathlib import Path
from urllib.parse import urljoin, urlsplit, urlunsplit, unquote

import requests
from bs4 import BeautifulSoup
from app.mf_ingestion.downloaders.base_downloader import BaseDownloader, DiscoveredDocument, DownloadedDocument
from app.mf_ingestion.parsers.adapters.ppfas_adapter import PPFASAdapter
from app.mf_ingestion.parsers.adapters.axis_adapter import AxisAdapter
from app.mf_ingestion.sources.registry import AMCDocumentSource

logger = logging.getLogger(__name__)

ICICI_SITE_BASE_URL = "https://www.icicipruamc.com"
ICICI_API_BASE_URL = "https://apimf.icicipruamc.com"
ICICI_CATEGORIES_ENDPOINT = f"{ICICI_API_BASE_URL}/nms/v1/downloads/categories"
ICICI_FILES_ENDPOINT = f"{ICICI_API_BASE_URL}/nms/v1/downloads/files"
ICICI_PAGE_SIZE = 20
ICICI_MAX_PAGES = 6
ICICI_USER_TYPE = "Investor"
ICICI_SUBCATEGORY_BY_DOCUMENT_TYPE = {
    "portfolio_disclosure": "monthly-portfolio-disclosures",
    "factsheet": "complete-factsheet",
}
MONTH_PATTERN = re.compile(
    r"(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(?:[\s\-_]+(?P<day>\d{1,2}))?[\s\-_\,]+(?P<year>20\d{2})",
    re.IGNORECASE,
)
DAY_FIRST_MONTH_PATTERN = re.compile(
    r"\b\d{1,2}(?:st|nd|rd|th)?[\s\-_]+(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-_\,]+(?P<year>20\d{2})",
    re.IGNORECASE,
)
SUPPORTED_FILE_EXTENSIONS = {".pdf", ".xls", ".xlsx", ".xlsm", ".csv", ".zip", ".html", ".htm"}
GENERIC_KEYWORDS = {
    "factsheet": ("factsheet", "fact sheet", "fund sheet", "monthly factsheet"),
    "portfolio_disclosure": ("portfolio", "disclosure", "holdings", "statutory", "monthly portfolio"),
}
GENERIC_REQUIRED_KEYWORDS: dict[str, dict[str, tuple[str, ...]]] = {
    "hdfc": {
        "factsheet": ("factsheet", "fact sheet", "fund fact"),
        "portfolio_disclosure": ("portfolio", "holding", "monthly portfolio", "monthly hdfc"),
    },
    "sbi": {
        "factsheet": ("factsheet", "fact sheet", "fund fact"),
        "portfolio_disclosure": ("portfolio", "holding", "monthly portfolio"),
    },
    "nippon": {
        "factsheet": ("factsheet", "fundamental", "fundamentals", "fund facts", "fund", "nippon"),
        "portfolio_disclosure": ("portfolio", "monthly portfolio", "disclosure", "nippon"),
    },
}
GENERIC_EXCLUDE_KEYWORDS = (
    "moa",
    "aoa",
    "statement of additional information",
    "sai",
    "update on valuation",
    "valuation of",
    "addendum",
    "notice",
    "voting policy",
    "aspxerrorpath=",
    "/error?",
)
RETRYABLE_STATUS_CODES = {408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 523, 524}
HTTP_MAX_RETRIES = max(int(os.getenv("MF_DISCOVERY_MAX_RETRIES", "3")), 0)
HTTP_BACKOFF_SECONDS = max(float(os.getenv("MF_DISCOVERY_BACKOFF_SECONDS", "1.2")), 0.1)


class AMCDownloader(BaseDownloader):
    def __init__(self, source: AMCDocumentSource, timeout_seconds: float, user_agent: str) -> None:
        self.source = source
        self.timeout_seconds = timeout_seconds
        self.user_agent = user_agent

    def list_documents(self, document_type: str) -> list[DiscoveredDocument]:
        adapter_key = (self.source.adapter_key or "").lower()
        if adapter_key == "ppfas":
            adapter = PPFASAdapter(user_agent=self.user_agent, timeout_seconds=int(self.timeout_seconds))
            docs = adapter.discover_documents(self.source, document_type=document_type)
            logger.info(
                "event=amc_discovery_complete amc_code=%s adapter=%s document_type=%s count=%s",
                self.source.amc_code,
                adapter_key,
                document_type,
                len(docs),
            )
            return docs
        if adapter_key == "icici":
            docs = _discover_icici_documents(
                self.source,
                document_type=document_type,
                timeout_seconds=self.timeout_seconds,
                user_agent=self.user_agent,
            )
            logger.info(
                "event=amc_discovery_complete amc_code=%s adapter=%s document_type=%s count=%s",
                self.source.amc_code,
                adapter_key,
                document_type,
                len(docs),
            )
            return docs
        if adapter_key == "axis":
            adapter = AxisAdapter(user_agent=self.user_agent, timeout_seconds=int(self.timeout_seconds))
            docs = adapter.discover_documents(self.source, document_type=document_type)
            logger.info(
                "event=amc_discovery_complete amc_code=%s adapter=%s document_type=%s count=%s",
                self.source.amc_code,
                adapter_key,
                document_type,
                len(docs),
            )
            return docs
        if adapter_key in {"hdfc", "sbi", "motilal", "nippon"}:
            if adapter_key == "sbi" and (document_type or "").strip().lower() == "factsheet":
                docs = _discover_sbi_factsheet_documents(
                    self.source,
                    timeout_seconds=self.timeout_seconds,
                    user_agent=self.user_agent,
                )
                logger.info(
                    "event=amc_discovery_complete amc_code=%s adapter=%s document_type=%s count=%s",
                    self.source.amc_code,
                    adapter_key,
                    document_type,
                    len(docs),
                )
                return docs
            docs = _discover_generic_anchor_documents(
                self.source,
                document_type=document_type,
                timeout_seconds=self.timeout_seconds,
                user_agent=self.user_agent,
            )
            logger.info(
                "event=amc_discovery_complete amc_code=%s adapter=%s document_type=%s count=%s",
                self.source.amc_code,
                adapter_key,
                document_type,
                len(docs),
            )
            return docs

        raise NotImplementedError(f"No discovery adapter configured for adapter_key={adapter_key}")

    def download(self, discovered: DiscoveredDocument) -> DownloadedDocument:
        adapter_key = (self.source.adapter_key or "").lower()
        if adapter_key == "icici":
            response = None
            attempted_urls = []
            for candidate_url in _icici_download_url_candidates(discovered.url):
                attempted_urls.append(candidate_url)
                try:
                    response = _request_with_retry(
                        "GET",
                        candidate_url,
                        timeout_seconds=self.timeout_seconds,
                        headers={
                            "User-Agent": self.user_agent,
                            "Referer": ICICI_SITE_BASE_URL + "/",
                        },
                    )
                    break
                except Exception:
                    response = None

            if not response:
                raise RuntimeError(f"icici_download_failed urls={attempted_urls}")

            source_url = response.url or discovered.url
            file_name = _derive_file_name(source_url, discovered.title)
            return DownloadedDocument(
                amc_name=discovered.amc_name,
                amc_code=discovered.amc_code,
                document_type=discovered.document_type,
                source_url=source_url,
                discovery_page_url=discovered.discovery_page_url,
                file_name=file_name,
                file_ext=discovered.file_ext,
                report_month=discovered.report_month,
                content_type=response.headers.get("Content-Type"),
                file_size_bytes=len(response.content),
                file_bytes=response.content,
            )

        if adapter_key in {"hdfc", "sbi", "axis", "motilal", "nippon"}:
            referer = discovered.discovery_page_url or _base_site_url(discovered.url)
            response = _request_with_retry(
                "GET",
                discovered.url,
                timeout_seconds=self.timeout_seconds,
                headers={
                    "User-Agent": self.user_agent,
                    "Referer": referer,
                },
            )
            _validate_generic_download_response(self.source, discovered, response)
            source_url = response.url or discovered.url
            file_name = _derive_file_name(source_url, discovered.title)
            return DownloadedDocument(
                amc_name=discovered.amc_name,
                amc_code=discovered.amc_code,
                document_type=discovered.document_type,
                source_url=source_url,
                discovery_page_url=discovered.discovery_page_url,
                file_name=file_name,
                file_ext=discovered.file_ext,
                report_month=discovered.report_month,
                content_type=response.headers.get("Content-Type"),
                file_size_bytes=len(response.content),
                file_bytes=response.content,
            )

        if adapter_key != "ppfas":
            raise NotImplementedError(f"No downloader configured for adapter_key={adapter_key}")

        adapter = PPFASAdapter(user_agent=self.user_agent, timeout_seconds=int(self.timeout_seconds))
        response = adapter.download_document(discovered.url)
        file_name = _derive_file_name(discovered.url, discovered.title)
        return DownloadedDocument(
            amc_name=discovered.amc_name,
            amc_code=discovered.amc_code,
            document_type=discovered.document_type,
            source_url=discovered.url,
            discovery_page_url=discovered.discovery_page_url,
            file_name=file_name,
            file_ext=discovered.file_ext,
            report_month=discovered.report_month,
            content_type=response.headers.get("Content-Type"),
            file_size_bytes=len(response.content),
            file_bytes=response.content,
        )


def _derive_file_name(url: str, fallback_title: str) -> str:
    path = Path(url.split("?", 1)[0])
    name = path.name.strip()
    if name:
        return name

    safe = "_".join((fallback_title or "document").split())
    return safe or "document"


def _discover_generic_anchor_documents(
    source: AMCDocumentSource,
    document_type: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    doc_type = (document_type or "").strip().lower()
    listing_url = source.factsheet_page_url if doc_type == "factsheet" else source.portfolio_disclosure_page_url
    if not listing_url:
        listing_url = source.factsheet_page_url or source.portfolio_disclosure_page_url
    if not listing_url:
        return []

    manual_docs = _manual_discovered_documents_for_source(source, doc_type, listing_url)
    docs: list[DiscoveredDocument] = list(manual_docs)
    seen_urls: set[str] = {item.url for item in manual_docs}

    try:
        response = _request_with_retry(
            "GET",
            listing_url,
            timeout_seconds=timeout_seconds,
            headers={"User-Agent": user_agent, "Referer": _base_site_url(listing_url)},
        )
    except Exception as exc:
        logger.exception(
            "event=generic_discovery_failed amc_code=%s document_type=%s reason=%s",
            source.amc_code,
            doc_type,
            exc,
        )
        return docs

    soup = BeautifulSoup(response.text or "", "html.parser")
    keywords = GENERIC_KEYWORDS.get(doc_type, ())
    required_keywords = _required_keywords_for_generic_source(source, doc_type)
    adapter_key = (source.adapter_key or "").strip().lower()

    for anchor in soup.find_all("a"):
        href = str(anchor.get("href") or "").strip()
        if not href or href.startswith("#") or href.lower().startswith("javascript:") or href.lower().startswith("mailto:"):
            continue

        url = urljoin(response.url or listing_url, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        title = " ".join(anchor.get_text(" ", strip=True).split()) or Path(url.split("?", 1)[0]).name
        combined = f"{title} {url}".lower()
        ext = Path(urlsplit(url).path).suffix.lower() or _infer_file_ext_from_text(combined)
        if ext not in SUPPORTED_FILE_EXTENSIONS:
            continue
        if not _generic_candidate_allowed(source, combined, doc_type, ext, required_keywords):
            continue

        report_month = _detect_report_month_from_text(combined)
        keyword_hits = sum(1 for keyword in keywords if keyword in combined)
        if keywords and keyword_hits == 0:
            # Keep weak matches for coverage, but with a lower ranking.
            score_boost = -35
        else:
            score_boost = keyword_hits * 20

        base_score = _generic_base_score(ext=ext, document_type=doc_type)
        recency_score = 0
        if report_month:
            recency_score = (report_month.year * 12 + report_month.month) * 10

        docs.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type=doc_type,
                title=title,
                url=url,
                discovery_page_url=response.url or listing_url,
                file_ext=ext,
                report_month=report_month,
                priority_score=base_score + recency_score + score_boost,
            )
        )

    if adapter_key == "nippon" and doc_type == "factsheet" and not docs:
        listing_ext = Path(urlsplit(response.url or listing_url).path).suffix.lower() or ".html"
        if listing_ext in {".html", ".htm"}:
            combined = f"{_human_title_from_url(response.url or listing_url)} {response.url or listing_url}".lower()
            docs.append(
                DiscoveredDocument(
                    amc_name=source.amc_name,
                    amc_code=source.amc_code,
                    document_type=doc_type,
                    title=_human_title_from_url(response.url or listing_url),
                    url=response.url or listing_url,
                    discovery_page_url=response.url or listing_url,
                    file_ext=listing_ext,
                    report_month=_detect_report_month_from_text(combined),
                    priority_score=_generic_base_score(ext=listing_ext, document_type=doc_type),
                )
            )

    if adapter_key == "hdfc":
        hdfc_extensions = (".pdf",) if doc_type == "factsheet" else (".xlsx", ".xlsm", ".xls", ".csv", ".zip", ".pdf")
        embedded_urls = _extract_embedded_file_urls(response.text or "", response.url or listing_url, extensions=hdfc_extensions)
        for url in embedded_urls:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            title = _human_title_from_url(url)
            combined = f"{title} {url}".lower()
            ext = Path(urlsplit(url).path).suffix.lower() or _infer_file_ext_from_text(combined)
            if ext not in SUPPORTED_FILE_EXTENSIONS:
                continue
            if not _generic_candidate_allowed(source, combined, doc_type, ext, required_keywords):
                continue
            report_month = _detect_report_month_from_text(combined)
            base_score = _generic_base_score(ext=ext, document_type=doc_type)
            recency_score = 0
            if report_month:
                recency_score = (report_month.year * 12 + report_month.month) * 10
            docs.append(
                DiscoveredDocument(
                    amc_name=source.amc_name,
                    amc_code=source.amc_code,
                    document_type=doc_type,
                    title=title,
                    url=url,
                    discovery_page_url=response.url or listing_url,
                    file_ext=ext,
                    report_month=report_month,
                    priority_score=base_score + recency_score + 40,
                )
            )

    # SBI portfolios page often exposes XLSX links inside scripts/JSON, not plain anchors.
    if adapter_key == "sbi" and doc_type == "portfolio_disclosure":
        embedded_urls = _extract_embedded_file_urls(response.text or "", response.url or listing_url, extensions=(".xlsx", ".xlsm", ".xls", ".csv", ".zip"))
        for url in embedded_urls:
            if url in seen_urls:
                continue
            seen_urls.add(url)
            title = _human_title_from_url(url)
            combined = f"{title} {url}".lower()
            ext = Path(urlsplit(url).path).suffix.lower() or _infer_file_ext_from_text(combined)
            if ext not in SUPPORTED_FILE_EXTENSIONS:
                continue
            if not _generic_candidate_allowed(source, combined, doc_type, ext, required_keywords):
                continue
            report_month = _detect_report_month_from_text(combined)
            base_score = _generic_base_score(ext=ext, document_type=doc_type)
            recency_score = 0
            if report_month:
                recency_score = (report_month.year * 12 + report_month.month) * 10
            docs.append(
                DiscoveredDocument(
                    amc_name=source.amc_name,
                    amc_code=source.amc_code,
                    document_type=doc_type,
                    title=title,
                    url=url,
                    discovery_page_url=response.url or listing_url,
                    file_ext=ext,
                    report_month=report_month,
                    priority_score=base_score + recency_score + 30,
                )
            )
        if not any(doc.document_type == doc_type for doc in docs):
            guessed_urls = _guess_sbi_portfolio_urls(now_utc=datetime.now(UTC))
            for url in guessed_urls:
                if url in seen_urls:
                    continue
                try:
                    probe = _request_with_retry(
                        "GET",
                        url,
                        timeout_seconds=timeout_seconds,
                        headers={"User-Agent": user_agent, "Referer": _base_site_url(listing_url)},
                    )
                except Exception:
                    continue
                final_url = probe.url or url
                if not _sbi_guessed_portfolio_probe_is_valid(probe, final_url):
                    continue
                seen_urls.add(final_url)
                title = _human_title_from_url(final_url)
                combined = f"{title} {final_url}".lower()
                ext = Path(urlsplit(final_url).path).suffix.lower() or _infer_file_ext_from_text(combined)
                if ext not in SUPPORTED_FILE_EXTENSIONS:
                    continue
                if not _generic_candidate_allowed(source, combined, doc_type, ext, required_keywords):
                    continue
                report_month = _detect_report_month_from_text(combined)
                base_score = _generic_base_score(ext=ext, document_type=doc_type)
                recency_score = 0
                if report_month:
                    recency_score = (report_month.year * 12 + report_month.month) * 10
                docs.append(
                    DiscoveredDocument(
                        amc_name=source.amc_name,
                        amc_code=source.amc_code,
                        document_type=doc_type,
                        title=title,
                        url=final_url,
                        discovery_page_url=response.url or listing_url,
                        file_ext=ext,
                        report_month=report_month,
                        priority_score=base_score + recency_score + 25,
                    )
                )

    docs.sort(key=lambda item: item.priority_score, reverse=True)
    return docs


def _discover_sbi_factsheet_documents(
    source: AMCDocumentSource,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    listing_url = source.factsheet_page_url or "https://www.sbimf.com/factsheets"
    endpoint = urljoin(listing_url, "/ajaxcall/CMS/GetRecentFactSheets")
    try:
        response = _request_with_retry(
            "POST",
            endpoint,
            timeout_seconds=timeout_seconds,
            headers={
                "User-Agent": user_agent,
                "Referer": listing_url,
                "Content-Type": "application/json;charset=utf-8",
            },
            json_payload={},
        )
    except Exception as exc:
        logger.exception("event=sbi_factsheet_discovery_failed reason=%s", exc)
        return []

    soup = BeautifulSoup(response.text or "", "html.parser")
    docs: list[DiscoveredDocument] = []
    seen_urls: set[str] = set()
    for anchor in soup.find_all("a"):
        href = str(anchor.get("href") or "").strip()
        if not href:
            continue
        url = urljoin(listing_url, href)
        if url in seen_urls:
            continue
        title = " ".join(anchor.get_text(" ", strip=True).split()) or _human_title_from_url(url)
        combined = f"{title} {url}".lower()
        ext = Path(urlsplit(url).path).suffix.lower() or _infer_file_ext_from_text(combined)
        if ext != ".pdf":
            continue
        if "factsheet" not in combined:
            continue
        seen_urls.add(url)
        report_month = _detect_report_month_from_text(combined)
        recency_score = (report_month.year * 12 + report_month.month) * 10 if report_month else 0
        docs.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type="factsheet",
                title=title,
                url=url,
                discovery_page_url=listing_url,
                file_ext=ext,
                report_month=report_month,
                priority_score=_generic_base_score(ext=ext, document_type="factsheet") + recency_score,
            )
        )
    docs.sort(key=lambda item: item.priority_score, reverse=True)
    return docs


def _sbi_guessed_portfolio_probe_is_valid(response: requests.Response, final_url: str) -> bool:
    low_url = str(final_url or "").lower()
    if "aspxerrorpath=" in low_url:
        return False

    parsed = urlsplit(final_url or "")
    low_path = (parsed.path or "").lower()
    if low_path.rstrip("/").endswith("/error") or "/error/" in low_path:
        return False

    content_type = str(response.headers.get("Content-Type") or "").lower()
    if "text/html" in content_type:
        return False

    ext = Path(low_path).suffix.lower()
    prefix = bytes(response.content[:8] or b"")
    if ext in {".xlsx", ".xlsm"}:
        if not prefix.startswith(b"PK\x03\x04"):
            return False
    if ext == ".xls":
        is_legacy_excel = prefix.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1")
        is_zip_excel = prefix.startswith(b"PK\x03\x04")
        if not (is_legacy_excel or is_zip_excel):
            return False

    return True


def _validate_generic_download_response(
    source: AMCDocumentSource,
    discovered: DiscoveredDocument,
    response: requests.Response,
) -> None:
    final_url = response.url or discovered.url
    low_url = str(final_url or "").lower()
    if any(blocked in low_url for blocked in ("aspxerrorpath=", "/error?", "/error/")):
        raise RuntimeError(f"download_rejected_error_page url={final_url}")

    content_type = str(response.headers.get("Content-Type") or "").lower()
    prefix = bytes(response.content[:8] or b"").lstrip()
    ext = Path(urlsplit(final_url).path).suffix.lower() or discovered.file_ext.lower()
    html_factsheet_allowed = discovered.document_type == "factsheet" and ext in {".html", ".htm"}
    if not html_factsheet_allowed and ("text/html" in content_type or prefix.startswith((b"<html", b"<!doc"))):
        raise RuntimeError(f"download_rejected_html_response url={final_url}")

    adapter_key = (source.adapter_key or "").strip().lower()
    if adapter_key == "sbi" and discovered.document_type == "portfolio_disclosure":
        if not _sbi_guessed_portfolio_probe_is_valid(response, final_url):
            raise RuntimeError(f"download_rejected_invalid_sbi_portfolio url={final_url}")

    if ext in {".xlsx", ".xlsm"} and not prefix.startswith(b"PK\x03\x04"):
        raise RuntimeError(f"download_rejected_invalid_excel url={final_url}")
    if ext == ".xls":
        legacy_excel = prefix.startswith(b"\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1")
        zip_excel = prefix.startswith(b"PK\x03\x04")
        if not (legacy_excel or zip_excel):
            raise RuntimeError(f"download_rejected_invalid_excel url={final_url}")


def _manual_discovered_documents_for_source(
    source: AMCDocumentSource,
    document_type: str,
    listing_url: str,
) -> list[DiscoveredDocument]:
    urls = _manual_document_urls(source, document_type)
    if not urls:
        return []

    docs: list[DiscoveredDocument] = []
    for url in urls:
        absolute_url = urljoin(listing_url, url)
        ext = Path(urlsplit(absolute_url).path).suffix.lower() or _infer_file_ext_from_text(absolute_url)
        if ext not in SUPPORTED_FILE_EXTENSIONS:
            ext = ".pdf" if document_type == "factsheet" else ".xlsx"
        title = _human_title_from_url(absolute_url)
        combined = f"{title} {absolute_url}".lower()
        report_month = _detect_report_month_from_text(combined)
        docs.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type=document_type,
                title=title,
                url=absolute_url,
                discovery_page_url=listing_url,
                file_ext=ext,
                report_month=report_month,
                priority_score=9_000_000,  # Force manual URLs to be attempted first.
            )
        )
    return docs


def _manual_document_urls(source: AMCDocumentSource, document_type: str) -> list[str]:
    amc = str(source.amc_code or "").strip().upper()
    if not amc:
        return []
    suffix = "FACTSHEET_DOCUMENT_URLS" if document_type == "factsheet" else "PORTFOLIO_DOCUMENT_URLS"
    env_name = f"MF_{amc}_{suffix}"
    raw = str(os.getenv(env_name, "") or "")

    allow_hdfc_factsheet_portfolio = str(
        os.getenv("MF_ALLOW_HDFC_FACTSHEET_AS_PORTFOLIO", "") or ""
    ).strip().lower() in {"1", "true", "yes", "on"}
    if document_type == "portfolio_disclosure" and amc == "HDFC" and allow_hdfc_factsheet_portfolio and not raw.strip():
        raw = str(os.getenv("MF_HDFC_FACTSHEET_DOCUMENT_URLS", "") or "")

    if not raw.strip():
        return []
    urls: list[str] = []
    seen: set[str] = set()
    for token in raw.split(","):
        value = token.strip()
        if not value or value in seen:
            continue
        seen.add(value)
        urls.append(value)
    return urls


def _human_title_from_url(url: str) -> str:
    path_name = Path(urlsplit(url).path).name
    decoded = unquote(path_name).replace("+", " ")
    return decoded or "document"


def _extract_embedded_file_urls(html: str, base_url: str, extensions: tuple[str, ...]) -> list[str]:
    raw = unescape(str(html or ""))
    if not raw.strip():
        return []
    ordered_extensions = sorted({ext.lstrip(".") for ext in extensions}, key=len, reverse=True)
    extension_pattern = "|".join(re.escape(ext) for ext in ordered_extensions)
    patterns = [
        re.compile(rf"https?://[^\s\"'<>]+\.({extension_pattern})(?:\?[^\s\"'<>]*)?", re.IGNORECASE),
        re.compile(rf"/[^\s\"'<>]+\.({extension_pattern})(?:\?[^\s\"'<>]*)?", re.IGNORECASE),
    ]
    urls: list[str] = []
    seen: set[str] = set()
    for pattern in patterns:
        for match in pattern.finditer(raw):
            value = match.group(0).strip()
            absolute = urljoin(base_url, value)
            if absolute in seen:
                continue
            seen.add(absolute)
            urls.append(absolute)
    return urls


def _guess_sbi_portfolio_urls(*, now_utc: datetime) -> list[str]:
    # SBI naming pattern:
    # /docs/default-source/scheme-portfolios/all-schemes-monthly-portfolio---as-on-30th-april-2026.xlsx
    months = _recent_months_for_portfolio_guess(now_utc.date(), count=3)
    urls: list[str] = []
    for year, month in months:
        last_day = monthrange(year, month)[1]
        for day in (last_day, 30, 31, 29, 28):
            if day < 1 or day > last_day:
                continue
            suffix = _ordinal_suffix(day)
            month_name = datetime(year, month, 1, tzinfo=UTC).strftime("%B").lower()
            urls.append(
                f"https://www.sbimf.com/docs/default-source/scheme-portfolios/"
                f"all-schemes-monthly-portfolio---as-on-{day}{suffix}-{month_name}-{year}.xlsx"
            )
    # Preserve order and uniqueness.
    deduped: list[str] = []
    seen: set[str] = set()
    for url in urls:
        if url in seen:
            continue
        seen.add(url)
        deduped.append(url)
    return deduped


def _recent_months_for_portfolio_guess(today: date, count: int = 3) -> list[tuple[int, int]]:
    # start from previous month (most likely published portfolio)
    year = today.year
    month = today.month - 1
    if month == 0:
        month = 12
        year -= 1
    pairs: list[tuple[int, int]] = []
    for _ in range(max(count, 1)):
        pairs.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return pairs


def _ordinal_suffix(day: int) -> str:
    if 10 <= (day % 100) <= 20:
        return "th"
    return {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")


def _required_keywords_for_generic_source(source: AMCDocumentSource, document_type: str) -> tuple[str, ...]:
    adapter_key = (source.adapter_key or "").strip().lower()
    per_source = GENERIC_REQUIRED_KEYWORDS.get(adapter_key) or {}
    keywords = per_source.get(document_type)
    if keywords:
        return keywords
    return GENERIC_KEYWORDS.get(document_type, ())


def _generic_candidate_allowed(
    source: AMCDocumentSource,
    combined_text: str,
    document_type: str,
    file_ext: str,
    required_keywords: tuple[str, ...],
) -> bool:
    low = str(combined_text or "").lower()
    adapter_key = (source.adapter_key or "").strip().lower()
    if any(blocked in low for blocked in GENERIC_EXCLUDE_KEYWORDS):
        return False

    # Require direct signal to avoid picking random legal/compliance PDFs.
    if required_keywords and not any(token in low for token in required_keywords):
        return False

    # Portfolio ingestion should avoid non-portfolio disclosures.
    if document_type == "portfolio_disclosure" and "portfolio" not in low and "holding" not in low:
        if not (adapter_key == "hdfc" and "monthly hdfc" in low):
            return False

    # SBI portfolio disclosures are expected as spreadsheet payloads.
    if adapter_key == "sbi" and document_type == "portfolio_disclosure":
        if file_ext not in {".xlsx", ".xls", ".xlsm", ".csv", ".zip"}:
            return False

    # SBI factsheets should come from scheme-factsheets docs path.
    if adapter_key == "sbi" and document_type == "factsheet":
        if "scheme-factsheets" not in low and "factsheet" not in low:
            return False
    return True


def _discover_icici_documents(
    source: AMCDocumentSource,
    document_type: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    subcategory_internal_name = ICICI_SUBCATEGORY_BY_DOCUMENT_TYPE.get((document_type or "").strip().lower())
    if not subcategory_internal_name:
        return []

    try:
        session = requests.Session()
        session.headers.update(_icici_request_headers(user_agent))
        categories = _fetch_icici_categories(session=session, timeout_seconds=timeout_seconds)
        category_id, category_code = _resolve_icici_category_metadata(categories, subcategory_internal_name)
        if not category_id:
            logger.warning(
                "event=icici_subcategory_not_found subcategory=%s document_type=%s",
                subcategory_internal_name,
                document_type,
            )
            return []

        files: list[dict] = []
        for page in range(1, ICICI_MAX_PAGES + 1):
            page_files, has_next = _fetch_icici_files_page(
                session=session,
                timeout_seconds=timeout_seconds,
                category_id=category_id,
                category_code=category_code,
                page=page,
            )
            files.extend(page_files)
            if not has_next:
                break
    except Exception as exc:
        logger.exception("event=icici_discovery_failed reason=%s", exc)
        return []

    docs: list[DiscoveredDocument] = []
    doc_type = (document_type or "").strip().lower()
    for item in files:
        raw_url = str(item.get("url") or "").strip()
        if not raw_url:
            continue
        absolute_url = urljoin(ICICI_SITE_BASE_URL, raw_url)
        ext = Path(absolute_url.split("?", 1)[0]).suffix.lower() or _infer_file_ext_from_text(item.get("title"))
        if ext not in {".pdf", ".xls", ".xlsx", ".csv", ".zip"}:
            continue

        report_month = _icici_report_month(item)
        base_score = _icici_base_score(ext=ext, document_type=doc_type)
        recency_score = 0
        if report_month:
            recency_score = (report_month.year * 12 + report_month.month) * 10
        title = _icici_title(item) or Path(absolute_url).stem
        docs.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type=doc_type,
                title=title,
                url=absolute_url,
                discovery_page_url=source.factsheet_page_url or source.portfolio_disclosure_page_url or ICICI_SITE_BASE_URL,
                file_ext=ext,
                report_month=report_month,
                priority_score=base_score + recency_score,
            )
        )

    docs.sort(key=lambda item: item.priority_score, reverse=True)
    return docs


def _fetch_icici_categories(session: requests.Session, timeout_seconds: float) -> list[dict]:
    response = _request_with_retry(
        "GET",
        ICICI_CATEGORIES_ENDPOINT,
        timeout_seconds=timeout_seconds,
        session=session,
        params={"userType": ICICI_USER_TYPE},
    )
    payload = response.json()
    data = payload.get("success", {}).get("data", [])
    return data if isinstance(data, list) else []


def _resolve_icici_category_metadata(categories: list[dict], subcategory_internal_name: str) -> tuple[str | None, str]:
    for category in categories:
        subcategories = category.get("subCategory") or []
        for subcategory in subcategories:
            if str(subcategory.get("internalName") or "").strip().lower() != subcategory_internal_name:
                continue
            category_id = str(subcategory.get("id") or "").strip()
            category_code = (
                str((category.get("title") or {}).get("code") or "").strip()
                or str(category.get("internalName") or "").strip().upper().replace(" ", "_")
            )
            if category_id:
                return category_id, category_code
    return None, ""


def _fetch_icici_files_page(
    session: requests.Session,
    timeout_seconds: float,
    category_id: str,
    category_code: str,
    page: int,
) -> tuple[list[dict], bool]:
    payload = {
        "categoryId": category_id,
        "schemeCategory": "",
        "userType": ICICI_USER_TYPE,
        "fileType": "All",
        "page": str(page),
        "size": str(ICICI_PAGE_SIZE),
        "filter": [],
        "categoryName": category_code,
    }
    response = _request_with_retry(
        "POST",
        ICICI_FILES_ENDPOINT,
        timeout_seconds=timeout_seconds,
        session=session,
        json_payload=payload,
    )
    body = response.json()
    data = body.get("success", {}).get("data", {})
    files = data.get("files", []) if isinstance(data, dict) else []
    has_next = bool(data.get("isNext")) if isinstance(data, dict) else False
    if not isinstance(files, list):
        return [], False
    return files, has_next


def _icici_request_headers(user_agent: str) -> dict[str, str]:
    return {
        "User-Agent": user_agent,
        "Referer": ICICI_SITE_BASE_URL + "/",
        "Content-Type": "application/json",
        "env": "api",
        "requestApiId": str(uuid.uuid4()),
    }


def _icici_title(item: dict) -> str:
    title = item.get("title")
    if isinstance(title, dict):
        return str(title.get("text") or title.get("code") or "").strip()
    return str(title or "").strip()


def _icici_report_month(item: dict) -> date | None:
    for key in ("applicableMonth", "fileDate"):
        raw = item.get(key)
        if raw in (None, ""):
            continue
        try:
            millis = int(raw)
            return datetime.fromtimestamp(millis / 1000, UTC).date().replace(day=1)
        except (TypeError, ValueError, OSError):
            continue

    return _detect_report_month_from_text(_icici_title(item))


def _icici_base_score(ext: str, document_type: str) -> int:
    if document_type == "portfolio_disclosure":
        return {
            ".xlsx": 220,
            ".xls": 210,
            ".csv": 190,
            ".zip": 180,
            ".pdf": 120,
        }.get(ext, 90)

    return {
        ".pdf": 220,
        ".xlsx": 130,
        ".xls": 120,
        ".csv": 110,
        ".zip": 90,
    }.get(ext, 80)


def _generic_base_score(ext: str, document_type: str) -> int:
    if document_type == "portfolio_disclosure":
        return {
            ".xlsx": 220,
            ".xls": 210,
            ".xlsm": 205,
            ".csv": 190,
            ".zip": 180,
            ".pdf": 120,
        }.get(ext, 90)
    return {
        ".pdf": 220,
        ".html": 150,
        ".htm": 150,
        ".xlsx": 140,
        ".xls": 130,
        ".xlsm": 125,
        ".csv": 110,
        ".zip": 90,
    }.get(ext, 80)


def _detect_report_month_from_text(text: str) -> date | None:
    match = DAY_FIRST_MONTH_PATTERN.search(text or "")
    if not match:
        match = MONTH_PATTERN.search(text or "")
    if not match:
        return None
    month = datetime.strptime(match.group("month")[:3], "%b").month
    year = int(match.group("year"))
    return date(year, month, 1)


def _infer_file_ext_from_text(text: str) -> str:
    low = str(text or "").lower()
    if ".xlsx" in low:
        return ".xlsx"
    if ".xls" in low:
        return ".xls"
    if ".csv" in low:
        return ".csv"
    if ".zip" in low:
        return ".zip"
    if ".pdf" in low:
        return ".pdf"
    if ".html" in low:
        return ".html"
    if ".htm" in low:
        return ".htm"
    return ""


def _icici_download_url_candidates(original_url: str) -> list[str]:
    blob_url = _icici_blob_url(original_url)
    if blob_url and blob_url != original_url:
        return [blob_url, original_url]
    return [original_url]


def _icici_blob_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"}:
        return url
    if "icicipruamc.com" not in (parsed.netloc or "").lower():
        return url
    path = parsed.path or ""
    if path.startswith("/blob/"):
        return url
    if not path.startswith("/downloads/"):
        return url
    blob_path = "/blob" + path
    return urlunsplit((parsed.scheme, parsed.netloc, blob_path, parsed.query, parsed.fragment))


def _base_site_url(url: str) -> str:
    parsed = urlsplit(url)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}/"
    return url


class _HttpxResponseWrapper:
    def __init__(self, r):
        self.r = r
        self.status_code = r.status_code
        self.text = r.text
        self.content = r.content
        self.url = str(r.url)
        self.headers = {k.lower(): v for k, v in r.headers.items()}
    def raise_for_status(self):
        self.r.raise_for_status()

def _request_with_retry(
    method: str,
    url: str,
    *,
    timeout_seconds: float,
    headers: dict[str, str] | None = None,
    session: requests.Session | None = None,
    params: dict[str, object] | None = None,
    json_payload: dict[str, object] | None = None,
) -> requests.Response:
    method_upper = method.upper()
    last_exc: Exception | None = None
    for attempt in range(HTTP_MAX_RETRIES + 1):
        try:
            if session is not None:
                response = session.request(
                    method=method_upper,
                    url=url,
                    timeout=timeout_seconds,
                    headers=headers,
                    params=params,
                    json=json_payload,
                )
            elif method_upper == "GET":
                response = requests.get(
                    url,
                    timeout=timeout_seconds,
                    headers=headers,
                    params=params,
                )
            elif method_upper == "POST":
                response = requests.post(
                    url,
                    timeout=timeout_seconds,
                    headers=headers,
                    params=params,
                    json=json_payload,
                )
            else:
                response = requests.request(
                    method=method_upper,
                    url=url,
                    timeout=timeout_seconds,
                    headers=headers,
                    params=params,
                    json=json_payload,
                )

            # --- Cloudflare/WAF Bypass fallback ---
            if getattr(response, "status_code", 200) in {403, 406} and session is None and method_upper in {"GET", "POST"}:
                try:
                    import httpx
                    with httpx.Client(http2=True) as client:
                        h_resp = client.request(
                            method=method_upper,
                            url=url,
                            headers=headers,
                            params=params,
                            json=json_payload,
                            timeout=timeout_seconds,
                            follow_redirects=True,
                        )
                        if h_resp.status_code not in {403, 406}:
                            response = _HttpxResponseWrapper(h_resp) # type: ignore
                except Exception as httpx_exc:
                    logger.debug("httpx fallback failed: %s", httpx_exc)
            # --------------------------------------

            if getattr(response, "status_code", 200) in RETRYABLE_STATUS_CODES and attempt < HTTP_MAX_RETRIES:
                time.sleep(HTTP_BACKOFF_SECONDS * (2 ** attempt))
                continue
            response.raise_for_status()
            return response
        except Exception as exc:
            last_exc = exc
            if attempt < HTTP_MAX_RETRIES:
                time.sleep(HTTP_BACKOFF_SECONDS * (2 ** attempt))
                continue
            break
    raise RuntimeError(f"http_request_failed method={method_upper} url={url} reason={last_exc}")
