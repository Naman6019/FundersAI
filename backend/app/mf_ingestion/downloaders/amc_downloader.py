from __future__ import annotations

import json
import base64
import hashlib
import hmac
import logging
import os
import re
import time
import uuid
from dataclasses import replace
from html import unescape
from datetime import UTC, date, datetime
from calendar import monthrange
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from app.mf_ingestion.downloaders.base_downloader import (
    BaseDownloader,
    DiscoveredDocument,
    DownloadedDocument,
    local_file_sources_allowed,
)
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
MIRAE_DOWNLOADS_ENDPOINT = "https://www.miraeassetmf.co.in/AjaxService/GetDownloadsData"
MIRAE_MODULE_BY_DOCUMENT_TYPE = {
    "factsheet": "Factsheet",
    "portfolio_disclosure": "portfolio_tab1",
}
DSP_DOWNLOADS_ENDPOINT = "https://www.dspim.com/downloads.json"
MOTILAL_SITE_BASE_URL = "https://www.motilaloswalmf.com"
MOTILAL_DOCUMENTS_ENDPOINT = (
    f"{MOTILAL_SITE_BASE_URL}/content/aem-cloud-dept-backend-motilal-oswal/api/search-documents.json"
)
MOTILAL_CATEGORY_BY_DOCUMENT_TYPE = {
    "factsheet": "factsheet",
    "portfolio_disclosure": "month end portfolio",
}
MOTILAL_DISCOVERY_LOOKBACK_MONTHS = 6
EDELWEISS_API_BASE_URL = "https://api.edelweissmf.com/edelweissmf/api/v1"
EDELWEISS_ENCRYPTION_KEY_URL = (
    "https://api.edelweissmf.com/virat_eks_api/api/v1/auth/encryption-key"
)
EDELWEISS_STATUTORY_MENU_URL = f"{EDELWEISS_API_BASE_URL}/mf/statutory-menus/single"
EDELWEISS_IPIFY_URL = "https://api.ipify.org/?format=json"
EDELWEISS_STATIC_IP = "103.0.123.175"
EDELWEISS_OFFICIAL_PORTFOLIO_FALLBACKS = (
    (
        "Monthly Portfolio - July 31, 2026",
        "https://www.edelweissmf.com/Files/MF/Statutory/Portfolio_of_schemes/"
        "Monthly_Portfolio_and_RiskoMeter/EDEL_Portfolio_Monthly_Notes_31Jul2026_17082026124432.xlsx",
    ),
)
EDELWEISS_OFFICIAL_FACTSHEET_FALLBACKS = (
    (
        "Factsheet - August 2026",
        "https://www.edelweissmf.com/Files/MF/Downloads/FACTSHEETS/FACTSHEETS/"
        "Edelweiss_Factsheet_August__2026_10082026160011.pdf",
    ),
)
HDFC_PUBLIC_DOWNLOAD_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)
HDFC_MONTHLY_PORTFOLIO_INVENTORY_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "hdfc_monthly_portfolios.json"
)
UTI_ENDPOINT_BY_DOCUMENT_TYPE = {
    "factsheet": "https://www.utimf.com/api/get-fact-sheet",
    "portfolio_disclosure": "https://www.utimf.com/api/get-consolidate-portfolio-disclosure",
}
ABSL_RESOURCES_ENDPOINT = (
    "https://mutualfund.adityabirlacapital.com/"
    "postlogin/CustomApi/Resources/FactsheetAccordionById"
)
ABSL_PORTFOLIO_RESOURCE_ID = "3ccab227-9de5-4494-b78d-2b4f7c0c054a"
ABSL_INDIVIDUAL_CUSTOMER_TYPE = (
    "/sitecore/content/Root/BSL/Library/Lists/FAQ/Customer Types/Individual"
)
MONTH_PATTERN = re.compile(
    r"(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(?:[\s\-_]+(?P<day>\d{1,2}))?[\s\-_\,]+(?P<year>20\d{2})",
    re.IGNORECASE,
)
NUMERIC_DATE_PATTERN = re.compile(
    r"\b(?P<day>\d{1,2})[/-](?P<month>\d{1,2})[/-](?P<year>20\d{2})\b"
)
DAY_FIRST_MONTH_PATTERN = re.compile(
    r"\b\d{1,2}(?:st|nd|rd|th)?[\s\-_]+(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-_\,]+(?P<year>20\d{2})",
    re.IGNORECASE,
)
SUPPORTED_FILE_EXTENSIONS = {".pdf", ".xls", ".xlsx", ".xlsm", ".csv", ".zip", ".html", ".htm"}
KOTAK_DOWNLOAD_PATH_MARKERS = (
    "/reportupload/download/",
)
GENERIC_KEYWORDS = {
    "factsheet": ("factsheet", "fact sheet", "fund sheet", "monthly factsheet"),
    "portfolio_disclosure": ("portfolio", "disclosure", "holdings", "statutory", "monthly portfolio"),
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
        if not self.source.discovery_enabled:
            raise PermissionError(f"discovery_disabled:{self.source.adapter_key}")
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
        if adapter_key == "mirae":
            docs = _discover_mirae_documents(
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
        if adapter_key == "uti":
            docs = _discover_uti_documents(
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
        if adapter_key == "tata":
            docs = _discover_tata_documents(
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
        if adapter_key == "bandhan":
            docs = _discover_bandhan_documents(
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
        if adapter_key == "edelweiss":
            docs = _discover_edelweiss_documents(
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
        if adapter_key == "dsp":
            if (document_type or "").strip().lower() == "factsheet":
                docs = _discover_dsp_factsheet_documents(
                    self.source,
                    timeout_seconds=self.timeout_seconds,
                    user_agent=self.user_agent,
                )
            else:
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
        if adapter_key == "motilal":
            docs = _discover_motilal_documents(
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
        if adapter_key in {
            "aditya_birla",
            "hdfc",
            "kotak",
            "nippon",
            "sbi",
            "edelweiss",
            "invesco",
            "hsbc",
            "quant",
            "canara_robeco",
            "groww",
            "zerodha",
            "baroda_bnp",
            "lic",
            "sundaram",
            "pgim",
            "quantum",
            "bajaj_finserv",
            "capitalmind",
            "abakkus",
            "unifi",
            "shriram",
            "helios",
            "nj",
            "old_bridge",
            "360_one",
            "navi",
            "taurus",
            "angel_one",
            "boi",
            "choice",
            "wealth_company",
            "jio_blackrock",
        }:
            if adapter_key == "invesco":
                docs = _discover_invesco_documents(
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
            if adapter_key == "hsbc":
                docs = _discover_hsbc_documents(
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
            if adapter_key == "aditya_birla" and (
                document_type or ""
            ).strip().lower() == "portfolio_disclosure":
                docs = _discover_absl_portfolio_documents(
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
            if (
                adapter_key == "kotak"
                and (document_type or "").strip().lower()
                == "portfolio_disclosure"
                and not docs
                and _browser_fallback_allowed_for_source(self.source)
            ):
                docs = _discover_kotak_browser_documents(
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

    def download(
        self,
        discovered: DiscoveredDocument,
        *,
        conditional_headers: dict[str, str] | None = None,
    ) -> DownloadedDocument:
        if not self.source.acquisition_enabled:
            raise PermissionError(f"acquisition_disabled:{self.source.adapter_key}")
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
                            **(conditional_headers or {}),
                        },
                    )
                    break
                except Exception:
                    response = None

            if not response:
                raise RuntimeError(f"icici_download_failed urls={attempted_urls}")

            source_url = response.url or discovered.url
            file_name = _derive_file_name(source_url, discovered.title)
            file_ext = _normalize_download_file_ext(discovered.file_ext, response.content)
            return DownloadedDocument(
                amc_name=discovered.amc_name,
                amc_code=discovered.amc_code,
                document_type=discovered.document_type,
                source_url=source_url,
                discovery_page_url=discovered.discovery_page_url,
                file_name=file_name,
                file_ext=file_ext,
                report_month=discovered.report_month,
                content_type=response.headers.get("Content-Type"),
                file_size_bytes=len(response.content),
                file_bytes=response.content,
                etag=response.headers.get("ETag") or response.headers.get("etag"),
                last_modified=response.headers.get("Last-Modified") or response.headers.get("last-modified"),
                not_modified=response.status_code == 304,
            )

        if adapter_key == "ppfas":
            adapter = PPFASAdapter(user_agent=self.user_agent, timeout_seconds=int(self.timeout_seconds))
            response = adapter.download_document(discovered.url)
            source_url = getattr(response, "url", None) or discovered.url
            file_name = _derive_file_name(source_url, discovered.title)
            file_ext = _normalize_download_file_ext(discovered.file_ext, response.content)
            return DownloadedDocument(
                amc_name=discovered.amc_name,
                amc_code=discovered.amc_code,
                document_type=discovered.document_type,
                source_url=source_url,
                discovery_page_url=discovered.discovery_page_url,
                file_name=file_name,
                file_ext=file_ext,
                report_month=discovered.report_month,
                content_type=response.headers.get("Content-Type"),
                file_size_bytes=len(response.content),
                file_bytes=response.content,
                etag=response.headers.get("ETag") or response.headers.get("etag"),
                last_modified=response.headers.get("Last-Modified") or response.headers.get("last-modified"),
            )

        referer = discovered.discovery_page_url or _base_site_url(discovered.url)
        try:
            response = _request_with_retry(
                "GET",
                discovered.url,
                timeout_seconds=self.timeout_seconds,
                headers={
                    "User-Agent": _download_user_agent(self.source, self.user_agent),
                    "Referer": referer,
                    **(conditional_headers or {}),
                },
            )
        except Exception:
            if not (
                adapter_key == "edelweiss"
                and (discovered.document_type or "").strip().lower() == "factsheet"
                and _browser_fallback_allowed_for_source(self.source)
            ):
                raise
            logger.warning(
                "edelweiss:browser_download_fallback url=%s",
                discovered.url,
            )
            return _download_edelweiss_document_with_browser(
                self.source,
                discovered,
                timeout_seconds=self.timeout_seconds,
                user_agent=self.user_agent,
            )
        if response.status_code == 304:
            return DownloadedDocument(
                amc_name=discovered.amc_name,
                amc_code=discovered.amc_code,
                document_type=discovered.document_type,
                source_url=response.url or discovered.url,
                discovery_page_url=discovered.discovery_page_url,
                file_name=_derive_file_name(discovered.url, discovered.title),
                file_ext=discovered.file_ext,
                report_month=discovered.report_month,
                content_type=response.headers.get("Content-Type"),
                file_size_bytes=0,
                file_bytes=b"",
                etag=response.headers.get("ETag") or response.headers.get("etag"),
                last_modified=response.headers.get("Last-Modified") or response.headers.get("last-modified"),
                not_modified=True,
            )
        _validate_generic_download_response(self.source, discovered, response)
        source_url = response.url or discovered.url
        file_name = _derive_file_name(source_url, discovered.title)
        file_ext = _normalize_download_file_ext(discovered.file_ext, response.content)
        return DownloadedDocument(
            amc_name=discovered.amc_name,
            amc_code=discovered.amc_code,
            document_type=discovered.document_type,
            source_url=source_url,
            discovery_page_url=discovered.discovery_page_url,
            file_name=file_name,
            file_ext=file_ext,
            report_month=discovered.report_month,
            content_type=response.headers.get("Content-Type"),
            file_size_bytes=len(response.content),
            file_bytes=response.content,
            etag=response.headers.get("ETag") or response.headers.get("etag"),
            last_modified=response.headers.get("Last-Modified") or response.headers.get("last-modified"),
        )

    def probe_download(self, discovered: DiscoveredDocument, *, max_bytes: int = 65536) -> DownloadedDocument:
        """Use a ranged GET to validate a candidate before a full smoke-test download."""
        if (self.source.adapter_key or "").lower() in {"icici", "ppfas"}:
            # These AMCs require their existing session/URL recovery download paths.
            return self.download(discovered)
        referer = discovered.discovery_page_url or _base_site_url(discovered.url)
        base_headers = {
            "User-Agent": _download_user_agent(self.source, self.user_agent),
            "Referer": referer,
            "Accept": "application/pdf,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,*/*;q=0.8",
        }
        try:
            response = _request_with_retry(
                "GET",
                discovered.url,
                timeout_seconds=self.timeout_seconds,
                headers={
                    **base_headers,
                    "Range": f"bytes=0-{max(int(max_bytes), 1024) - 1}",
                },
            )
        except RuntimeError as exc:
            # Some AMC CDNs (observed: sbimf.com) reject byte-range requests with
            # 416 Requested Range Not Satisfiable instead of serving a partial or
            # full response. Fall back to an unranged GET and slice client-side.
            if "reason=416" not in str(exc):
                raise
            response = _request_with_retry(
                "GET",
                discovered.url,
                timeout_seconds=self.timeout_seconds,
                headers=base_headers,
            )
        body = response.content[:max(int(max_bytes), 1024)]
        source_url = response.url or discovered.url
        file_ext = _normalize_download_file_ext(discovered.file_ext, body)
        return DownloadedDocument(
            amc_name=discovered.amc_name,
            amc_code=discovered.amc_code,
            document_type=discovered.document_type,
            source_url=source_url,
            discovery_page_url=discovered.discovery_page_url,
            file_name=_derive_file_name(source_url, discovered.title),
            file_ext=file_ext,
            report_month=discovered.report_month,
            content_type=response.headers.get("Content-Type"),
            file_size_bytes=len(body),
            file_bytes=body,
        )


def _download_user_agent(source: AMCDocumentSource, configured_user_agent: str) -> str:
    if (source.adapter_key or "").strip().lower() in {"hdfc", "edelweiss"}:
        return HDFC_PUBLIC_DOWNLOAD_USER_AGENT
    return configured_user_agent


def _derive_file_name(url: str, fallback_title: str) -> str:
    path = Path(url.split("?", 1)[0])
    name = path.name.strip()
    if name:
        return name

    safe = "_".join((fallback_title or "document").split())
    return safe or "document"


def _normalize_download_file_ext(declared_ext: str, body: bytes) -> str:
    normalized = str(declared_ext or "").strip().lower()
    if normalized == ".xls" and bytes(body or b"").startswith(b"PK\x03\x04"):
        return ".xlsx"
    return normalized


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
    adapter_key = (source.adapter_key or "").strip().lower()

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
        if adapter_key == "hdfc":
            for document in _load_hdfc_reviewed_monthly_portfolios(source, doc_type):
                if document.url in seen_urls:
                    continue
                seen_urls.add(document.url)
                docs.append(document)
            if not docs:
                docs.extend(
                    document
                    for document in _guess_hdfc_combined_factsheets(
                        source,
                        doc_type,
                        now_utc=datetime.now(UTC),
                    )
                    if document.url not in seen_urls
                )
        return docs

    soup = BeautifulSoup(response.text or "", "html.parser")
    keywords = GENERIC_KEYWORDS.get(doc_type, ())
    required_keywords = _required_keywords_for_generic_source(source, doc_type)
    for anchor in soup.find_all("a"):
        href = str(anchor.get("href") or "").strip()
        if not href or href.startswith("#") or href.lower().startswith("javascript:") or href.lower().startswith("mailto:"):
            continue

        url = urljoin(response.url or listing_url, href)
        if url in seen_urls:
            continue
        seen_urls.add(url)

        anchor_title = _clean_discovery_text(anchor.get_text(" ", strip=True))
        container = anchor.find_parent(["li", "tr", "p"])
        context_text = (
            _clean_discovery_text(container.get_text(" ", strip=True))
            if container is not None
            else anchor_title
        )
        title = anchor_title or Path(url.split("?", 1)[0]).name
        if title.lower().strip() in {"download", "click here"} and context_text:
            title = context_text
        combined = f"{title} {context_text} {url}".lower()
        ext = Path(urlsplit(url).path).suffix.lower() or _infer_file_ext_from_text(combined)
        if ext in {".html", ".htm"}:
            # Listing/inner pages are discovery inputs, not ingestible documents.
            continue
        if ext not in SUPPORTED_FILE_EXTENSIONS:
            continue
        if not _generic_candidate_allowed(source, combined, doc_type, ext, required_keywords):
            continue

        report_month = _detect_report_month_from_text(combined)
        if adapter_key in {"nippon", "uti"} and doc_type == "factsheet" and report_month:
            # Nippon and UTI label factsheets by publication month; scheme
            # data is for the preceding month (for example, July => June).
            report_month = _previous_month(report_month)
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
        for document in _load_hdfc_reviewed_monthly_portfolios(source, doc_type):
            if document.url in seen_urls:
                continue
            seen_urls.add(document.url)
            docs.append(document)
        if not docs:
            for document in _guess_hdfc_combined_factsheets(
                source,
                doc_type,
                now_utc=datetime.now(UTC),
            ):
                if document.url in seen_urls:
                    continue
                seen_urls.add(document.url)
                docs.append(document)

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


def _browser_fallback_allowed_for_source(source: AMCDocumentSource) -> bool:
    if not source.browser_recovery_allowed:
        return False
    enabled = str(
        os.getenv("MF_DISCOVERY_BROWSER_ENABLED", "false") or ""
    ).strip().lower()
    if enabled not in {"1", "true", "yes", "on"}:
        return False
    approved = {
        item.strip().lower()
        for item in str(
            os.getenv("MF_DISCOVERY_BROWSER_AMCS", "") or ""
        ).split(",")
        if item.strip()
    }
    return source.adapter_key.strip().lower() in approved


def _discover_edelweiss_documents(
    source: AMCDocumentSource,
    document_type: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    """Discover Edelweiss's official monthly holdings workbook.

    The statutory page renders weekly, fortnightly, and monthly document tabs in
    the browser. The monthly tab exposes one complete XLSX portfolio workbook;
    generic anchor extraction only sees the page shell.
    """
    doc_type = (document_type or "").strip().lower()
    if doc_type != "portfolio_disclosure":
        if doc_type == "factsheet":
            api_documents = _discover_edelweiss_factsheets_from_api(
                source,
                listing_url=source.factsheet_page_url or source.portfolio_disclosure_page_url or "",
                timeout_seconds=timeout_seconds,
                user_agent=user_agent,
            )
            if api_documents:
                return api_documents

        documents = _discover_generic_anchor_documents(
            source,
            document_type=doc_type,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )
        # Edelweiss publishes the factsheet in the following calendar month.
        # The official PDF body, not its publication filename, confirms its
        # reporting month before it can be persisted.
        if doc_type == "factsheet":
            documents = [replace(document, report_month=None) for document in documents]
            if documents:
                return documents
            if _browser_fallback_allowed_for_source(source):
                browser_documents = _discover_edelweiss_factsheets_with_browser(
                    source,
                    listing_url=source.factsheet_page_url or source.portfolio_disclosure_page_url or "",
                    timeout_seconds=timeout_seconds,
                    user_agent=user_agent,
                )
                if browser_documents:
                    return browser_documents
            fallback_documents = _edelweiss_factsheet_documents_from_candidates(
                source,
                listing_url=source.factsheet_page_url or source.portfolio_disclosure_page_url or "",
                candidates=list(EDELWEISS_OFFICIAL_FACTSHEET_FALLBACKS),
            )
            if fallback_documents:
                logger.warning(
                    "edelweiss:using_official_factsheet_direct_fallback count=%s",
                    len(fallback_documents),
                )
            return fallback_documents
        return documents

    listing_url = source.portfolio_disclosure_page_url or source.factsheet_page_url
    if not listing_url:
        return []

    generic_documents = _discover_generic_anchor_documents(
        source,
        document_type=doc_type,
        timeout_seconds=timeout_seconds,
        user_agent=user_agent,
    )
    monthly_documents = [
        document
        for document in generic_documents
        if _is_edelweiss_monthly_portfolio_document(document.title, document.url)
    ]
    if monthly_documents:
        return sorted(monthly_documents, key=lambda item: item.priority_score, reverse=True)
    if not _browser_fallback_allowed_for_source(source):
        return []
    browser_documents = _discover_edelweiss_monthly_portfolios_with_browser(
        source,
        listing_url=listing_url,
        timeout_seconds=timeout_seconds,
        user_agent=user_agent,
    )
    if browser_documents:
        return browser_documents

    # The official Edelweiss origins currently return 403 to GitHub-hosted
    # discovery, but direct files remain publicly downloadable. Keep the
    # user-verified July disclosure as a bounded last-resort candidate; it is
    # still filtered by the requested reporting month before persistence.
    fallback_documents = _edelweiss_monthly_portfolio_documents_from_candidates(
        source,
        listing_url=listing_url,
        candidates=list(EDELWEISS_OFFICIAL_PORTFOLIO_FALLBACKS),
    )
    if fallback_documents:
        logger.warning(
            "edelweiss:using_official_direct_fallback count=%s",
            len(fallback_documents),
        )
    return fallback_documents


def _discover_edelweiss_monthly_portfolios_with_browser(
    source: AMCDocumentSource,
    *,
    listing_url: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    api_documents = _discover_edelweiss_monthly_portfolios_from_api(
        source,
        listing_url=listing_url,
        timeout_seconds=timeout_seconds,
        user_agent=user_agent,
    )
    if api_documents:
        return api_documents

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("edelweiss:playwright_not_installed")
        return []

    candidates: list[tuple[str, str]] = []
    # The Angular disclosure tabs can arrive well after the initial document
    # response. Keep this bounded, but allow the public page its observed
    # hydration time on a clean GitHub Actions browser.
    timeout_ms = max(60_000, int(timeout_seconds * 1_000))
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                # Use Playwright's native browser identity. The public page's
                # API is protected by browser-level delivery rules.
                context = browser.new_context()
                page = context.new_page()
                page.goto(listing_url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_function(
                    "typeof window.webpackChunkapp !== 'undefined'",
                    timeout=timeout_ms,
                )
                api_candidates = _edelweiss_api_candidates_in_browser(page)
                if api_candidates:
                    context.close()
                    return _edelweiss_monthly_portfolio_documents_from_candidates(
                        source,
                        listing_url=listing_url,
                        candidates=api_candidates,
                    )
                # The statutory page first defaults to "Financials & Portfolios".
                # Select the public portfolio section before its monthly sub-tab.
                portfolio_tab = page.get_by_text("Portfolio of scheme(s)", exact=True)
                portfolio_tab.first.wait_for(state="visible", timeout=timeout_ms)
                portfolio_tab.first.click(timeout=timeout_ms)
                monthly_tab = page.get_by_text("Monthly Portfolio and Risk-o-Meter", exact=True)
                monthly_tab.first.wait_for(state="visible", timeout=timeout_ms)
                monthly_tab.first.click(timeout=timeout_ms)
                monthly_links = page.locator(
                    "a[href*='/Monthly_Portfolio_and_RiskoMeter/']"
                )
                monthly_links.first.wait_for(timeout=timeout_ms)
                for index in range(monthly_links.count()):
                    link = monthly_links.nth(index)
                    url = str(link.get_attribute("href") or "").strip()
                    title = " ".join(link.inner_text().split())
                    if url:
                        candidates.append((title, url))
                context.close()
            finally:
                browser.close()
    except Exception as exc:
        logger.warning("edelweiss:browser_discovery_failed error=%s", exc)
        return []

    return _edelweiss_monthly_portfolio_documents_from_candidates(
        source,
        listing_url=listing_url,
        candidates=candidates,
    )


def _discover_edelweiss_factsheets_with_browser(
    source: AMCDocumentSource,
    *,
    listing_url: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("edelweiss:playwright_not_installed")
        return []

    timeout_ms = max(60_000, int(timeout_seconds * 1_000))
    candidates: list[tuple[str, str]] = []
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            try:
                context = browser.new_context()
                page = context.new_page()
                page.goto(listing_url, wait_until="domcontentloaded", timeout=timeout_ms)
                page.wait_for_function(
                    "typeof window.webpackChunkapp !== 'undefined'",
                    timeout=timeout_ms,
                )
                candidates = _edelweiss_factsheet_api_candidates_in_browser(page)
                context.close()
            finally:
                browser.close()
    except Exception as exc:
        logger.warning("edelweiss:factsheet_browser_discovery_failed error=%s", exc)
        return []

    return _edelweiss_factsheet_documents_from_candidates(
        source,
        listing_url=listing_url,
        candidates=candidates,
    )


def _edelweiss_factsheet_api_candidates_in_browser(page) -> list[tuple[str, str]]:
    try:
        return list(
            page.evaluate(
                """
                async () => {
                  const findCrypto = () => {
                    let req;
                    if (window.__fundersaiWebpackRequire) req = window.__fundersaiWebpackRequire;
                    else if (window.webpackChunkapp) {
                      window.webpackChunkapp.push([[Date.now()], {}, candidate => { req = candidate; }]);
                      window.__fundersaiWebpackRequire = req;
                    }
                    if (!req || !req.m) return null;
                    for (const id of Object.keys(req.m)) {
                      try {
                        const candidate = req(id);
                        if (candidate?.AES?.decrypt && candidate?.HmacSHA256 && candidate?.enc?.Utf8) return candidate;
                      } catch (_) {}
                    }
                    return null;
                  };
                  const cryptoJs = findCrypto();
                  if (!cryptoJs) return [];
                  const staticIp = "103.0.123.175";
                  let ip = staticIp;
                  try { ip = String((await (await fetch("https://api.ipify.org/?format=json")).json()).ip || staticIp); } catch (_) {}
                  const keyTimestamp = String(Date.now());
                  const keyResponse = await fetch("https://api.edelweissmf.com/virat_eks_api/api/v1/auth/encryption-key", {
                    headers: {"accept":"application/json, text/plain, */*", "init":"true", "x-timestamp":keyTimestamp, "x-ip-address":staticIp}
                  });
                  if (!keyResponse.ok) return [];
                  const keyData = JSON.parse((await keyResponse.json()).body);
                  const secret = String(keyData.PRE_LOGIN.SECRET);
                  const hashKey = String(keyData.PRE_LOGIN.HASHKEY);
                  const timestamp = String(Date.now());
                  const requestKey = cryptoJs.HmacSHA256(secret + ip + timestamp, hashKey).toString(cryptoJs.enc.Hex);
                  const response = await fetch("https://api.edelweissmf.com/edelweissmf/api/v1/mf/statutory-menus/single?type=Downloads&fundType=MF&menuName=FACTSHEETS", {
                    headers: {"accept":"application/json, text/plain, */*", "x-timestamp":timestamp, "x-ip-address":ip}
                  });
                  if (!response.ok) return [];
                  const encrypted = (await response.json()).body;
                  const payload = JSON.parse(cryptoJs.AES.decrypt(encrypted, requestKey).toString(cryptoJs.enc.Utf8));
                  return (payload.files || [])
                    .filter(item => String(item.subMenuName || "").trim().toLowerCase() === "factsheets")
                    .map(item => [
                      String(item.fileTitle || item.systemFileName || ""),
                      String(item.filePath || item.downloadFile || "")
                    ])
                    .filter(item => item[1]);
                }
                """
            )
            or []
        )
    except Exception as exc:
        logger.warning("edelweiss:factsheet_browser_api_discovery_failed error=%s", exc)
        return []


def _discover_edelweiss_factsheets_from_api(
    source: AMCDocumentSource,
    *,
    listing_url: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    timeout = max(10.0, min(float(timeout_seconds), 30.0))
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.edelweissmf.com/",
        "User-Agent": user_agent or HDFC_PUBLIC_DOWNLOAD_USER_AGENT,
    }
    try:
        with requests.Session() as session:
            session.headers.update(headers)
            try:
                ip_response = session.get(EDELWEISS_IPIFY_URL, timeout=timeout)
                ip_response.raise_for_status()
                ip_address = str(ip_response.json().get("ip") or EDELWEISS_STATIC_IP)
            except Exception:
                ip_address = EDELWEISS_STATIC_IP

            key_timestamp = str(int(time.time() * 1_000))
            key_response = session.get(
                EDELWEISS_ENCRYPTION_KEY_URL,
                headers={
                    "init": "true",
                    "x-timestamp": key_timestamp,
                    "x-ip-address": EDELWEISS_STATIC_IP,
                },
                timeout=timeout,
            )
            key_response.raise_for_status()
            key_data = json.loads(key_response.json()["body"])
            secret = str(key_data["PRE_LOGIN"]["SECRET"])
            hash_key = str(key_data["PRE_LOGIN"]["HASHKEY"])
            timestamp = str(int(time.time() * 1_000))
            request_key = hmac.new(
                hash_key.encode("utf-8"),
                f"{secret}{ip_address}{timestamp}".encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            response = session.get(
                EDELWEISS_STATUTORY_MENU_URL,
                params={"type": "Downloads", "fundType": "MF", "menuName": "FACTSHEETS"},
                headers={"x-timestamp": timestamp, "x-ip-address": ip_address},
                timeout=timeout,
            )
            response.raise_for_status()
            payload = _decrypt_edelweiss_api_body(str(response.json()["body"]), request_key)
            candidates = [
                (
                    str(item.get("fileTitle") or item.get("systemFileName") or ""),
                    urljoin(listing_url, str(item.get("filePath") or item.get("downloadFile") or "")),
                )
                for item in (payload.get("files") or [])
                if isinstance(item, dict)
                and str(item.get("subMenuName") or "").strip().lower() == "factsheets"
            ]
            documents = _edelweiss_factsheet_documents_from_candidates(
                source,
                listing_url=listing_url,
                candidates=candidates,
            )
            logger.info(
                "edelweiss:official_api_discovery document_type=factsheet count=%s",
                len(documents),
            )
            return documents
    except Exception as exc:
        logger.warning("edelweiss:official_factsheet_api_discovery_failed error=%s", exc)
        return []


def _edelweiss_factsheet_documents_from_candidates(
    source: AMCDocumentSource,
    *,
    listing_url: str,
    candidates: list[tuple[str, str]],
) -> list[DiscoveredDocument]:
    documents: list[DiscoveredDocument] = []
    seen_urls: set[str] = set()
    required_keywords = _required_keywords_for_generic_source(source, "factsheet")
    for raw_title, raw_url in candidates:
        url = urljoin(listing_url, str(raw_url or "").strip())
        title = _clean_discovery_text(raw_title) or _human_title_from_url(url)
        if not url or url in seen_urls:
            continue
        combined = f"{title} {url}".lower()
        ext = Path(urlsplit(url).path).suffix.lower()
        if ext not in {".pdf", ".xls", ".xlsx", ".xlsm"}:
            continue
        if not _generic_candidate_allowed(
            source,
            combined,
            "factsheet",
            ext,
            required_keywords,
        ):
            continue
        seen_urls.add(url)
        publication_month = _detect_report_month_from_text(combined)
        recency_score = (
            (publication_month.year * 12 + publication_month.month) * 10
            if publication_month
            else 0
        )
        documents.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type="factsheet",
                title=title,
                url=url,
                discovery_page_url=listing_url,
                file_ext=ext,
                # Edelweiss publishes the reporting month in the following
                # calendar month. The PDF body confirms the actual month.
                report_month=None,
                priority_score=_generic_base_score(ext, "factsheet") + recency_score + 50,
            )
        )
    return sorted(documents, key=lambda item: item.priority_score, reverse=True)


def _download_edelweiss_document_with_browser(
    source: AMCDocumentSource,
    discovered: DiscoveredDocument,
    *,
    timeout_seconds: float,
    user_agent: str,
) -> DownloadedDocument:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError("edelweiss_browser_download_requires_playwright") from exc

    timeout_ms = max(60_000, int(float(timeout_seconds) * 1_000))
    referer = discovered.discovery_page_url or _base_site_url(discovered.url)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            context = browser.new_context(
                user_agent=user_agent or HDFC_PUBLIC_DOWNLOAD_USER_AGENT,
            )
            page = context.new_page()
            page.goto(referer, wait_until="domcontentloaded", timeout=timeout_ms)
            response = context.request.get(
                discovered.url,
                headers={
                    "Accept": "application/pdf,*/*;q=0.8",
                    "Referer": referer,
                },
                timeout=timeout_ms,
            )
            if not response.ok:
                raise RuntimeError(
                    f"edelweiss_browser_download_http_{response.status}"
                )
            body = response.body()
            source_url = str(response.url or discovered.url)
            return DownloadedDocument(
                amc_name=discovered.amc_name,
                amc_code=discovered.amc_code,
                document_type=discovered.document_type,
                source_url=source_url,
                discovery_page_url=discovered.discovery_page_url,
                file_name=_derive_file_name(source_url, discovered.title),
                file_ext=_normalize_download_file_ext(discovered.file_ext, body),
                report_month=discovered.report_month,
                content_type=response.headers.get("content-type"),
                file_size_bytes=len(body),
                file_bytes=body,
                etag=response.headers.get("etag"),
                last_modified=response.headers.get("last-modified"),
            )
        finally:
            browser.close()


def _edelweiss_api_candidates_in_browser(page) -> list[tuple[str, str]]:
    try:
        return list(
            page.evaluate(
                """
                async () => {
                  const keyUrl = "https://api.edelweissmf.com/virat_eks_api/api/v1/auth/encryption-key";
                  const menuUrl = "https://api.edelweissmf.com/edelweissmf/api/v1/mf/statutory-menus/single";
                  const staticIp = "103.0.123.175";
                  const findCrypto = () => {
                    let req;
                    if (window.__fundersaiWebpackRequire) {
                      req = window.__fundersaiWebpackRequire;
                    } else if (window.webpackChunkapp) {
                      window.webpackChunkapp.push([[Date.now()], {}, candidate => { req = candidate; }]);
                      window.__fundersaiWebpackRequire = req;
                    }
                    if (!req || !req.m) return null;
                    for (const id of Object.keys(req.m)) {
                      try {
                        const candidate = req(id);
                        if (candidate?.AES?.decrypt && candidate?.HmacSHA256 && candidate?.enc?.Utf8) {
                          return candidate;
                        }
                      } catch (_) {}
                    }
                    return null;
                  };
                  const cryptoJs = findCrypto();
                  if (!cryptoJs) return [];
                  let ip = staticIp;
                  try {
                    ip = String((await (await fetch("https://api.ipify.org/?format=json")).json()).ip || staticIp);
                  } catch (_) {}
                  const keyTimestamp = String(Date.now());
                  const keyResponse = await fetch(keyUrl, {
                    headers: {
                      "accept": "application/json, text/plain, */*",
                      "init": "true",
                      "x-timestamp": keyTimestamp,
                      "x-ip-address": staticIp,
                    },
                  });
                  if (!keyResponse.ok) return [];
                  const keyEnvelope = await keyResponse.json();
                  const keyData = JSON.parse(keyEnvelope.body);
                  const secret = String(keyData.PRE_LOGIN.SECRET);
                  const hashKey = String(keyData.PRE_LOGIN.HASHKEY);
                  const timestamp = String(Date.now());
                  const requestKey = cryptoJs.HmacSHA256(secret + ip + timestamp, hashKey).toString(cryptoJs.enc.Hex);
                  const menuResponse = await fetch(menuUrl + "?type=Statutory&fundType=MF&menuName=Portfolio%20of%20scheme(s)", {
                    headers: {
                      "accept": "application/json, text/plain, */*",
                      "x-timestamp": timestamp,
                      "x-ip-address": ip,
                    },
                  });
                  if (!menuResponse.ok) return [];
                  const encrypted = (await menuResponse.json()).body;
                  const payload = JSON.parse(cryptoJs.AES.decrypt(encrypted, requestKey).toString(cryptoJs.enc.Utf8));
                  return (payload.files || [])
                    .filter(item => String(item.subMenuName || "").trim().toLowerCase() === "monthly portfolio and risk-o-meter")
                    .map(item => ({
                      title: String(item.fileTitle || item.systemFileName || ""),
                      url: String(item.filePath || item.downloadFile || ""),
                    }))
                    .filter(item => item.url);
                }
                """
            )
            or []
        )
    except Exception as exc:
        logger.warning("edelweiss:browser_api_discovery_failed error=%s", exc)
        return []


def _discover_edelweiss_monthly_portfolios_from_api(
    source: AMCDocumentSource,
    *,
    listing_url: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    """Read the same official statutory-menu API used by Edelweiss's page.

    The public page can hide its Angular tabs from hosted crawlers, while this
    API remains the page's source of truth for its official file inventory.
    """
    timeout = max(10.0, min(float(timeout_seconds), 30.0))
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": "https://www.edelweissmf.com/",
        "User-Agent": user_agent or HDFC_PUBLIC_DOWNLOAD_USER_AGENT,
    }
    try:
        with requests.Session() as session:
            session.headers.update(headers)
            try:
                ip_response = session.get(EDELWEISS_IPIFY_URL, timeout=timeout)
                ip_response.raise_for_status()
                ip_address = str(ip_response.json().get("ip") or EDELWEISS_STATIC_IP)
            except Exception:
                ip_address = EDELWEISS_STATIC_IP

            timestamp = str(int(time.time() * 1_000))
            key_response = session.get(
                EDELWEISS_ENCRYPTION_KEY_URL,
                headers={
                    "init": "true",
                    "x-timestamp": timestamp,
                    # Edelweiss's Angular client uses its static bootstrap IP
                    # for this first public-key request.
                    "x-ip-address": EDELWEISS_STATIC_IP,
                },
                timeout=timeout,
            )
            key_response.raise_for_status()
            key_envelope = key_response.json()
            key_data = json.loads(key_envelope["body"])
            secret = str(key_data["PRE_LOGIN"]["SECRET"])
            hash_key = str(key_data["PRE_LOGIN"]["HASHKEY"])

            timestamp = str(int(time.time() * 1_000))
            request_key = hmac.new(
                hash_key.encode("utf-8"),
                f"{secret}{ip_address}{timestamp}".encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            response = session.get(
                EDELWEISS_STATUTORY_MENU_URL,
                params={
                    "type": "Statutory",
                    "fundType": "MF",
                    "menuName": "Portfolio of scheme(s)",
                },
                headers={
                    "x-timestamp": timestamp,
                    "x-ip-address": ip_address,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            encrypted_body = str(response.json()["body"])
            payload = _decrypt_edelweiss_api_body(encrypted_body, request_key)
            files = payload.get("files") if isinstance(payload, dict) else None
            if not isinstance(files, list):
                raise ValueError("statutory API response has no files list")

            candidates: list[tuple[str, str]] = []
            for item in files:
                if not isinstance(item, dict):
                    continue
                if (
                    str(item.get("subMenuName") or "").strip().lower()
                    != "monthly portfolio and risk-o-meter"
                ):
                    continue
                file_path = str(item.get("filePath") or item.get("downloadFile") or "").strip()
                title = str(item.get("fileTitle") or item.get("systemFileName") or "").strip()
                if file_path:
                    candidates.append((title, urljoin(listing_url, file_path)))
            documents = _edelweiss_monthly_portfolio_documents_from_candidates(
                source,
                listing_url=listing_url,
                candidates=candidates,
            )
            logger.info(
                "edelweiss:official_api_discovery document_type=portfolio_disclosure count=%s",
                len(documents),
            )
            return documents
    except Exception as exc:
        logger.warning("edelweiss:official_api_discovery_failed error=%s", exc)
        return []


def _decrypt_edelweiss_api_body(encrypted_body: str, passphrase: str) -> dict:
    raw = base64.b64decode(encrypted_body)
    if raw[:8] != b"Salted__":
        raise ValueError("unexpected Edelweiss encrypted response format")
    salt = raw[8:16]
    derived = b""
    previous = b""
    passphrase_bytes = passphrase.encode("utf-8")
    while len(derived) < 48:
        previous = hashlib.md5(previous + passphrase_bytes + salt).digest()
        derived += previous
    decryptor = Cipher(
        algorithms.AES(derived[:32]),
        modes.CBC(derived[32:48]),
    ).decryptor()
    padded = decryptor.update(raw[16:]) + decryptor.finalize()
    padding_length = padded[-1]
    if not 1 <= padding_length <= 16 or padded[-padding_length:] != bytes([padding_length]) * padding_length:
        raise ValueError("invalid Edelweiss response padding")
    return json.loads(padded[:-padding_length].decode("utf-8"))


def _edelweiss_monthly_portfolio_documents_from_candidates(
    source: AMCDocumentSource,
    *,
    listing_url: str,
    candidates: list[tuple[str, str]],
) -> list[DiscoveredDocument]:
    documents: list[DiscoveredDocument] = []
    seen_urls: set[str] = set()
    required_keywords = _required_keywords_for_generic_source(
        source,
        "portfolio_disclosure",
    )
    for raw_title, raw_url in candidates:
        url = urljoin(listing_url, str(raw_url or "").strip())
        title = _clean_discovery_text(raw_title) or _human_title_from_url(url)
        if not url or url in seen_urls or not _is_edelweiss_monthly_portfolio_document(title, url):
            continue
        seen_urls.add(url)
        combined = f"{title} {url}".lower()
        ext = Path(urlsplit(url).path).suffix.lower()
        if not _generic_candidate_allowed(
            source,
            combined,
            "portfolio_disclosure",
            ext,
            required_keywords,
        ):
            continue
        report_month = _detect_report_month_from_text(combined)
        recency_score = (report_month.year * 12 + report_month.month) * 10 if report_month else 0
        documents.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type="portfolio_disclosure",
                title=title,
                url=url,
                discovery_page_url=listing_url,
                file_ext=ext,
                report_month=report_month,
                priority_score=_generic_base_score(ext, "portfolio_disclosure") + recency_score + 50,
            )
        )
    return sorted(documents, key=lambda item: item.priority_score, reverse=True)


def _is_edelweiss_monthly_portfolio_document(title: str, url: str) -> bool:
    combined = f"{title} {url}".lower()
    return (
        "monthly portfolio" in combined
        and "monthly_portfolio_and_riskometer" in combined
        and "weekly" not in combined
        and "fortnightly" not in combined
    )


def _discover_tata_documents(
    source: AMCDocumentSource,
    document_type: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    """Read Tata's server-rendered document cards instead of relying on anchors.

    Tata exposes the monthly portfolio files in the public Next.js response as escaped
    ``field_document_title``/``field_media_document`` pairs. They are not HTML anchor
    tags, so generic anchor discovery never sees the official July workbook.
    """
    doc_type = (document_type or "").strip().lower()
    if doc_type == "factsheet":
        return _discover_tata_factsheet_documents(
            source,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )
    listing_url = (
        source.factsheet_page_url
        if doc_type == "factsheet"
        else source.portfolio_disclosure_page_url
    )
    if not listing_url:
        return []
    try:
        response = _request_with_retry(
            "GET",
            listing_url,
            timeout_seconds=timeout_seconds,
            headers={"User-Agent": user_agent, "Referer": _base_site_url(listing_url)},
        )
    except Exception as exc:
        logger.warning("tata:listing_request_failed document_type=%s error=%s", doc_type, exc)
        return []

    required_keywords = _required_keywords_for_generic_source(source, doc_type)
    allowed_extensions = (
        source.factsheet_extensions
        if doc_type == "factsheet"
        else source.portfolio_extensions
    )
    documents: list[DiscoveredDocument] = []
    seen_urls: set[str] = set()
    # The JSON is embedded as an escaped Next.js flight payload, not anchor tags.
    listing_text = (response.text or "").replace(chr(92) + '"', '"')
    pattern = re.compile(
        r'field_document_title":"(?P<title>.*?)".*?'
        r'field_media_document":"(?P<url>https:[^"]+)',
        re.DOTALL,
    )
    for match in pattern.finditer(listing_text):
        title = _decode_tata_listing_value(match.group("title"))
        url = _decode_tata_listing_value(match.group("url"))
        if not title or not url or url in seen_urls:
            continue
        seen_urls.add(url)
        combined = f"{title} {url}"
        ext = Path(urlsplit(url).path).suffix.lower() or _infer_file_ext_from_text(combined)
        if ext not in allowed_extensions or not _generic_candidate_allowed(
            source, combined, doc_type, ext, required_keywords
        ):
            continue
        report_month = _detect_report_month_from_text(combined)
        recency_score = (report_month.year * 12 + report_month.month) * 10 if report_month else 0
        documents.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type=doc_type,
                title=title,
                url=url,
                discovery_page_url=response.url or listing_url,
                file_ext=ext,
                report_month=report_month,
                priority_score=_generic_base_score(ext=ext, document_type=doc_type) + recency_score,
            )
        )
    documents.sort(key=lambda item: item.priority_score, reverse=True)
    return documents


def _decode_tata_listing_value(value: str) -> str:
    return unescape(str(value or "").replace("\\/", "/").replace("\\u0026", "&")).strip()


def _discover_tata_factsheet_documents(
    source: AMCDocumentSource,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    """Discover the per-scheme PDFs on Tata's public scheme-factsheet page."""
    listing_url = source.factsheet_page_url
    if not listing_url:
        return []
    try:
        response = _request_with_retry(
            "GET",
            listing_url,
            timeout_seconds=timeout_seconds,
            headers={"User-Agent": user_agent, "Referer": _base_site_url(listing_url)},
        )
    except Exception as exc:
        logger.warning("tata:factsheet_listing_request_failed error=%s", exc)
        return []

    documents: list[DiscoveredDocument] = []
    seen_urls: set[str] = set()
    for anchor in BeautifulSoup(response.text or "", "html.parser").find_all("a"):
        href = str(anchor.get("href") or "").strip()
        url = urljoin(response.url or listing_url, href)
        if not href or url in seen_urls:
            continue
        seen_urls.add(url)
        ext = Path(urlsplit(url).path).suffix.lower()
        if ext != ".pdf":
            continue
        title = _clean_discovery_text(anchor.get("aria-label") or anchor.get_text(" ", strip=True))
        if not title:
            title = _human_title_from_url(url)
        combined = f"Scheme Factsheet {title} {url}"
        if "tata" not in combined.lower() or not _generic_candidate_allowed(
            source,
            combined,
            "factsheet",
            ext,
            _required_keywords_for_generic_source(source, "factsheet"),
        ):
            continue
        documents.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type="factsheet",
                title=title,
                url=url,
                discovery_page_url=response.url or listing_url,
                file_ext=ext,
                report_month=None,
                priority_score=_generic_base_score(ext=ext, document_type="factsheet"),
            )
        )
    return documents


def _discover_bandhan_documents(
    source: AMCDocumentSource,
    document_type: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    """Use Bandhan's ordinary public download control, never its encrypted CMS API."""
    if not _browser_fallback_allowed_for_source(source):
        return _discover_generic_anchor_documents(
            source,
            document_type=document_type,
            timeout_seconds=timeout_seconds,
            user_agent=user_agent,
        )
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("bandhan:playwright_not_installed")
        return []

    doc_type = (document_type or "").strip().lower()
    listing_url = (
        source.factsheet_page_url
        if doc_type == "factsheet"
        else source.portfolio_disclosure_page_url
    )
    if not listing_url:
        return []
    timeout_ms = max(5_000, min(int(timeout_seconds * 1_000), 90_000))
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(user_agent=user_agent, accept_downloads=True)
            page = context.new_page()
            page.goto(listing_url, wait_until="networkidle", timeout=timeout_ms)
            download_button = page.locator('button:has(svg[viewBox="0 0 16 20"])').last
            if not download_button.count():
                browser.close()
                return []
            with page.expect_download(timeout=timeout_ms) as event:
                download_button.click(timeout=timeout_ms)
            download = event.value
            url = str(download.url or "").strip()
            title = str(download.suggested_filename or "").strip() or _human_title_from_url(url)
            browser.close()
    except Exception as exc:
        logger.warning("bandhan:browser_discovery_failed document_type=%s error=%s", doc_type, exc)
        return []

    combined = f"{unquote(url)} {title}"
    ext = Path(urlsplit(url).path).suffix.lower() or _infer_file_ext_from_text(combined)
    required_keywords = _required_keywords_for_generic_source(source, doc_type)
    if not url or not _generic_candidate_allowed(source, combined, doc_type, ext, required_keywords):
        return []
    report_month = _bandhan_report_month_from_download(url) or _detect_report_month_from_text(combined)
    recency_score = (report_month.year * 12 + report_month.month) * 10 if report_month else 0
    return [
        DiscoveredDocument(
            amc_name=source.amc_name,
            amc_code=source.amc_code,
            document_type=doc_type,
            title=title,
            url=url,
            discovery_page_url=listing_url,
            file_ext=ext,
            report_month=report_month,
            priority_score=_generic_base_score(ext=ext, document_type=doc_type) + recency_score,
        )
    ]


def _bandhan_report_month_from_download(download_url: str) -> date | None:
    """Prefer Bandhan's official source filename over its publication-month folder.

    The public download endpoint wraps the original filename in a ``filepath`` query
    parameter. Its storage path can say ``2026/08`` while the actual factsheet is
    ``...july-2026.pdf``. The filename is the disclosure period; the storage folder is
    only the publication date.
    """
    query = parse_qs(urlsplit(str(download_url or "")).query)
    source_paths = [*query.get("filepath", ()), str(download_url or "")]
    for source_path in source_paths:
        file_name = Path(urlsplit(unquote(source_path)).path).name
        report_month = _detect_report_month_from_text(file_name)
        if report_month:
            return report_month
    return None


def _discover_kotak_browser_documents(
    source: AMCDocumentSource,
    document_type: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("kotak:playwright_not_installed")
        return []

    listing_url = (
        source.portfolio_disclosure_page_url
        or source.factsheet_page_url
    )
    if not listing_url:
        return []

    candidates: list[dict[str, str]] = []
    timeout_ms = max(5_000, min(int(timeout_seconds * 1_000), 30_000))
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(user_agent=user_agent)
            page = context.new_page()

            def capture_response(response) -> None:
                response_url = str(response.url or "")
                content_disposition = str(
                    response.headers.get("content-disposition") or ""
                )
                response_text = f"{response_url} {content_disposition}".lower()
                if _looks_like_kotak_document_url(response_url):
                    candidates.append(
                        {
                            "title": content_disposition or _human_title_from_url(
                                response_url
                            ),
                            "context_text": content_disposition,
                            "url": response_url,
                        }
                    )
                if "application/json" not in str(
                    response.headers.get("content-type") or ""
                ).lower():
                    return
                try:
                    candidates.extend(
                        _kotak_candidates_from_payload(
                            response.json(),
                            response.url or listing_url,
                        )
                    )
                except Exception:
                    logger.debug(
                        "kotak:browser_json_response_unavailable url=%s",
                        response.url,
                    )

            page.on("response", capture_response)
            page.goto(
                listing_url,
                wait_until="domcontentloaded",
                timeout=timeout_ms,
            )
            page.wait_for_timeout(4_000)
            candidates.extend(_kotak_candidates_from_page(page))
            _activate_kotak_portfolio_controls(page)
            page.wait_for_timeout(3_000)
            candidates.extend(_kotak_candidates_from_page(page))
            candidates.extend(
                _kotak_candidates_from_html(page.content(), listing_url)
            )
            browser.close()
    except Exception as exc:
        logger.warning("kotak:browser_discovery_failed error=%s", exc)
        return []

    return _kotak_documents_from_candidates(
        source,
        document_type,
        listing_url,
        candidates,
    )


_discover_kotak_combined_factsheets = _discover_kotak_browser_documents


def _activate_kotak_portfolio_controls(page) -> None:
    for selector in (
        "text=/^Portfolios?$/i",
        "text=/^Monthly Portfolios?$/i",
    ):
        locator = page.locator(selector)
        for index in range(min(locator.count(), 3)):
            try:
                locator.nth(index).click(timeout=3_000)
            except Exception:
                continue

    for index in range(min(page.locator("select").count(), 10)):
        select = page.locator("select").nth(index)
        try:
            options = select.locator("option").evaluate_all(
                """options => options.map(option => ({
                    label: option.textContent || "",
                    value: option.value || ""
                }))"""
            )
        except Exception:
            continue
        portfolio_option = next(
            (
                option
                for option in options
                if "portfolio" in str(option.get("label") or "").lower()
            ),
            None,
        )
        if not portfolio_option:
            continue
        try:
            select.select_option(
                value=str(portfolio_option.get("value") or ""),
                timeout=3_000,
            )
        except Exception:
            continue


def _kotak_candidates_from_page(page) -> list[dict[str, str]]:
    try:
        return page.locator("a[href]").evaluate_all(
            """anchors => anchors.slice(0, 500).map(anchor => ({
                title: (anchor.textContent || "").trim(),
                context_text: (
                    anchor.closest("li, tr, article, section, div")?.textContent
                    || anchor.textContent
                    || ""
                ).trim().slice(0, 800),
                url: anchor.href || ""
            }))"""
        )
    except Exception:
        return []


def _kotak_candidates_from_html(
    html: str,
    listing_url: str,
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    for url in _extract_embedded_file_urls(
        html,
        listing_url,
        extensions=(".xlsx", ".xlsm", ".xls", ".csv", ".zip"),
    ):
        candidates.append(
            {
                "title": _human_title_from_url(url),
                "context_text": "portfolio",
                "url": url,
            }
        )
    return candidates


def _kotak_candidates_from_payload(
    payload: object,
    base_url: str,
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []

    def visit(value: object, context_text: str = "") -> None:
        if isinstance(value, dict):
            local_context = " ".join(
                str(item)
                for item in value.values()
                if isinstance(item, (str, int, float))
                and not _looks_like_kotak_document_url(str(item))
            )
            combined_context = _clean_discovery_text(
                f"{context_text} {local_context}"
            )[:1_200]
            for item in value.values():
                visit(item, combined_context)
            return
        if isinstance(value, list):
            for item in value[:500]:
                visit(item, context_text)
            return
        if not isinstance(value, str) or not _looks_like_kotak_document_url(
            value
        ):
            return
        absolute_url = urljoin(base_url, value)
        candidates.append(
            {
                "title": context_text or _human_title_from_url(absolute_url),
                "context_text": context_text,
                "url": absolute_url,
            }
        )

    visit(payload)
    return candidates


def _looks_like_kotak_document_url(value: str) -> bool:
    low = str(value or "").strip().lower()
    if not low:
        return False
    path = urlsplit(low).path
    return (
        Path(path).suffix.lower()
        in {".pdf", ".xls", ".xlsx", ".xlsm", ".csv", ".zip"}
        or any(marker in path for marker in KOTAK_DOWNLOAD_PATH_MARKERS)
    )


def _kotak_documents_from_candidates(
    source: AMCDocumentSource,
    document_type: str,
    listing_url: str,
    candidates: list[dict[str, str]],
) -> list[DiscoveredDocument]:
    doc_type = (document_type or "").strip().lower()
    required_keywords = _required_keywords_for_generic_source(
        source,
        doc_type,
    )
    allowed_suffixes = {
        suffix.strip().lower().rstrip(".")
        for suffix in (*source.allowed_host_suffixes, "kotakmf.com")
        if suffix
    }
    documents: list[DiscoveredDocument] = []
    seen: set[str] = set()
    for candidate in candidates[:1_000]:
        url = urljoin(listing_url, str(candidate.get("url") or "").strip())
        if not url or url in seen:
            continue
        parsed_url = urlsplit(url)
        host = str(parsed_url.hostname or "").lower().rstrip(".")
        if not any(
            host == suffix or host.endswith(f".{suffix}")
            for suffix in allowed_suffixes
        ):
            continue
        title = _clean_discovery_text(
            candidate.get("title") or _human_title_from_url(url)
        )
        context_text = _clean_discovery_text(
            candidate.get("context_text") or ""
        )
        combined = f"{title} {context_text} {url}".lower()
        ext = (
            Path(parsed_url.path).suffix.lower()
            or _infer_file_ext_from_text(combined)
        )
        if (
            not ext
            and doc_type == "portfolio_disclosure"
            and any(
                marker in parsed_url.path.lower()
                for marker in KOTAK_DOWNLOAD_PATH_MARKERS
            )
        ):
            ext = ".xlsx"
        if not _generic_candidate_allowed(
            source,
            combined,
            doc_type,
            ext,
            required_keywords,
        ):
            continue
        report_month = _detect_report_month_from_text(combined)
        base_score = _generic_base_score(
            ext=ext,
            document_type=doc_type,
        )
        recency_score = (
            (report_month.year * 12 + report_month.month) * 10
            if report_month
            else 0
        )
        seen.add(url)
        documents.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type=doc_type,
                title=title or _human_title_from_url(url),
                url=url,
                discovery_page_url=listing_url,
                file_ext=ext,
                report_month=report_month,
                priority_score=base_score + recency_score + 50,
            )
        )
    documents.sort(key=lambda item: item.priority_score, reverse=True)
    return documents


def _clean_discovery_text(value: object) -> str:
    text = re.sub(r"[\u200b-\u200f\u2060\ufeff]", "", str(value or ""))
    return " ".join(text.split())


def _previous_month(value: date) -> date:
    if value.month == 1:
        return date(value.year - 1, 12, 1)
    return date(value.year, value.month - 1, 1)


def _guess_hdfc_combined_factsheets(
    source: AMCDocumentSource,
    document_type: str,
    *,
    now_utc: datetime,
) -> list[DiscoveredDocument]:
    doc_type = str(document_type or "").strip().lower()
    if doc_type not in {"factsheet", "portfolio_disclosure"}:
        return []
    if doc_type == "portfolio_disclosure" and not source.factsheet_contains_holdings:
        return []

    current_month = now_utc.date().replace(day=1)
    previous_month = current_month.fromordinal(current_month.toordinal() - 1)
    report_months = _recent_month_starts(previous_month, count=6)
    documents: list[DiscoveredDocument] = []
    for report_month in report_months:
        if report_month.month == 12:
            publication_month = date(report_month.year + 1, 1, 1)
        else:
            publication_month = date(report_month.year, report_month.month + 1, 1)
        recency_score = (report_month.year * 12 + report_month.month) * 10
        base_file_names = (
            f"HDFC MF Factsheet - {report_month.strftime('%B %Y')}",
            f"HDFC MF Index Solutions Factsheet - {report_month.strftime('%B %Y')}",
        )
        # HDFC may publish a corrected monthly revision with an `_1` suffix.
        # Validate the revision first, then retain the original as a fallback.
        file_names = tuple(
            f"{base_name}{suffix}.pdf"
            for suffix in ("_1", "")
            for base_name in base_file_names
        )
        for revision_rank, file_name in enumerate(file_names):
            url = (
                "https://files.hdfcfund.com/s3fs-public/"
                f"{publication_month:%Y-%m}/{quote(file_name)}"
            )
            documents.append(
                DiscoveredDocument(
                    amc_name=source.amc_name,
                    amc_code=source.amc_code,
                    document_type=doc_type,
                    title=file_name,
                    url=url,
                    discovery_page_url=(
                        source.factsheet_page_url
                        if doc_type == "factsheet"
                        else source.portfolio_disclosure_page_url
                    )
                    or "https://www.hdfcfund.com/",
                    file_ext=".pdf",
                    report_month=report_month,
                    # Preserve deterministic order within the same report month:
                    # `_1` revisions must outrank the original upload.
                    priority_score=_generic_base_score(ext=".pdf", document_type=doc_type)
                    + recency_score
                    + 60
                    - revision_rank,
                )
            )
    return documents


def _load_hdfc_reviewed_monthly_portfolios(
    source: AMCDocumentSource,
    document_type: str,
) -> list[DiscoveredDocument]:
    if str(document_type or "").strip().lower() != "portfolio_disclosure":
        return []
    try:
        payload = json.loads(
            HDFC_MONTHLY_PORTFOLIO_INVENTORY_PATH.read_text(encoding="utf-8")
        )
        report_month = date.fromisoformat(str(payload["report_month"]))
        publication_path = str(payload["publication_path"]).strip().strip("/")
        portfolio_date = str(payload["portfolio_date"]).strip()
        discovery_page_url = str(
            payload.get("source_page")
            or source.portfolio_disclosure_page_url
            or "https://www.hdfcfund.com/"
        ).strip()
        scheme_names = payload.get("scheme_names")
        if not isinstance(scheme_names, list):
            raise ValueError("scheme_names must be a list")
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        logger.error("event=hdfc_reviewed_portfolio_inventory_invalid reason=%s", exc)
        return []

    documents: list[DiscoveredDocument] = []
    seen_names: set[str] = set()
    for index, raw_name in enumerate(scheme_names):
        scheme_name = str(raw_name or "").strip()
        if not scheme_name or scheme_name in seen_names:
            continue
        seen_names.add(scheme_name)
        file_name = f"Monthly {scheme_name} - {portfolio_date}.xlsx"
        documents.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type="portfolio_disclosure",
                title=file_name,
                url=(
                    "https://files.hdfcfund.com/s3fs-public/"
                    f"{publication_path}/{quote(file_name)}"
                ),
                discovery_page_url=discovery_page_url,
                file_ext=".xlsx",
                report_month=report_month,
                priority_score=8_500_000 - index,
            )
        )
    return documents


def _discover_motilal_documents(
    source: AMCDocumentSource,
    document_type: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    doc_type = (document_type or "").strip().lower()
    category = MOTILAL_CATEGORY_BY_DOCUMENT_TYPE.get(doc_type)
    if not category:
        return []

    listing_url = source.factsheet_page_url if doc_type == "factsheet" else source.portfolio_disclosure_page_url
    listing_url = listing_url or source.factsheet_page_url or source.portfolio_disclosure_page_url or MOTILAL_SITE_BASE_URL
    docs = _manual_discovered_documents_for_source(source, doc_type, listing_url)
    seen_urls = {item.url for item in docs}

    # Motilal's page loads current documents with blank year/month filters.
    # Its abbreviated month-filter API can return empty current-month buckets.
    buckets: list[tuple[int | None, int | None]] = [
        (None, None),
        *_recent_month_buckets(
            datetime.now(UTC).date(),
            MOTILAL_DISCOVERY_LOOKBACK_MONTHS,
        ),
    ]
    for year, month in buckets:
        params = {
            "year": year or "",
            "category": category,
            "month": (
                datetime(year, month, 1, tzinfo=UTC).strftime("%b").lower()
                if year and month
                else ""
            ),
            "type": "mf",
        }
        try:
            response = _request_with_retry(
                "GET",
                MOTILAL_DOCUMENTS_ENDPOINT,
                timeout_seconds=timeout_seconds,
                headers={"User-Agent": user_agent, "Referer": listing_url},
                params=params,
            )
            payload = response.json()
        except Exception as exc:
            logger.warning(
                "event=motilal_discovery_bucket_failed document_type=%s year=%s month=%s reason=%s",
                doc_type,
                year or "",
                month or "",
                exc,
            )
            continue

        results = payload.get("results") if isinstance(payload, dict) else []
        if not isinstance(results, list):
            continue
        for item in results:
            if not isinstance(item, dict):
                continue
            raw_path = str(item.get("path") or "").strip()
            if not raw_path:
                continue
            url = urljoin(MOTILAL_SITE_BASE_URL, raw_path)
            if url in seen_urls:
                continue
            title = str(item.get("title") or "").strip() or Path(urlsplit(url).path).stem
            combined = f"{title} {raw_path}"
            ext = Path(urlsplit(url).path).suffix.lower() or _motilal_extension_from_mime_type(item.get("mimeType"))
            required_keywords = _required_keywords_for_generic_source(source, doc_type)
            if ext not in SUPPORTED_FILE_EXTENSIONS:
                continue
            if not _generic_candidate_allowed(source, combined, doc_type, ext, required_keywords):
                continue

            seen_urls.add(url)
            report_month = _detect_report_month_from_text(combined)
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
                    discovery_page_url=listing_url,
                    file_ext=ext,
                    report_month=report_month,
                    priority_score=_generic_base_score(ext=ext, document_type=doc_type) + recency_score,
                )
            )

    docs.sort(key=lambda item: item.priority_score, reverse=True)
    return docs


def _discover_absl_portfolio_documents(
    source: AMCDocumentSource,
    *,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    listing_url = (
        source.portfolio_disclosure_page_url
        or source.factsheet_page_url
        or "https://mutualfund.adityabirlacapital.com/forms-and-downloads/portfolio"
    )
    try:
        response = _request_with_retry(
            "GET",
            ABSL_RESOURCES_ENDPOINT,
            timeout_seconds=timeout_seconds,
            headers={"User-Agent": user_agent, "Referer": listing_url},
            params={
                "id": ABSL_PORTFOLIO_RESOURCE_ID,
                "ctype": ABSL_INDIVIDUAL_CUSTOMER_TYPE,
                "month": " ",
                "year": 0,
            },
        )
        payload = response.json()
    except Exception as exc:
        logger.warning(
            "event=absl_portfolio_api_failed amc_code=%s reason=%s",
            source.amc_code,
            exc,
        )
        return []

    rows = payload.get("AccordionList") if isinstance(payload, dict) else []
    if not isinstance(rows, list):
        return []

    docs: list[DiscoveredDocument] = []
    seen_urls: set[str] = set()
    required_keywords = _required_keywords_for_generic_source(
        source,
        "portfolio_disclosure",
    )
    for row in rows:
        if not isinstance(row, dict):
            continue
        title = _clean_discovery_text(row.get("ResourceLink"))
        raw_url = str(row.get("pdfUrl") or "").strip()
        url = _absl_official_download_url(raw_url, listing_url)
        if not url or url in seen_urls:
            continue
        combined = f"{title} {url}".lower()
        ext = Path(urlsplit(url).path).suffix.lower() or _infer_file_ext_from_text(combined)
        if ext not in SUPPORTED_FILE_EXTENSIONS:
            continue
        if not _generic_candidate_allowed(
            source,
            combined,
            "portfolio_disclosure",
            ext,
            required_keywords,
        ):
            continue

        seen_urls.add(url)
        report_month = _detect_report_month_from_text(combined)
        recency_score = (
            (report_month.year * 12 + report_month.month) * 10
            if report_month
            else 0
        )
        docs.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type="portfolio_disclosure",
                title=title or _human_title_from_url(url),
                url=url,
                discovery_page_url=listing_url,
                file_ext=ext,
                report_month=report_month,
                priority_score=_generic_base_score(
                    ext=ext,
                    document_type="portfolio_disclosure",
                )
                + recency_score,
            )
        )

    docs.sort(key=lambda item: item.priority_score, reverse=True)
    return docs


def _absl_official_download_url(raw_url: str, listing_url: str) -> str:
    parsed = urlsplit(str(raw_url or "").strip())
    if not parsed.path:
        return ""
    if parsed.hostname and parsed.hostname.lower() == "abcscprod.azureedge.net":
        listing = urlsplit(listing_url)
        return urlunsplit(
            (
                listing.scheme or "https",
                listing.netloc or "mutualfund.adityabirlacapital.com",
                parsed.path,
                parsed.query,
                "",
            )
        )
    return urljoin(listing_url, raw_url)


def _motilal_extension_from_mime_type(value: object) -> str:
    mime_type = str(value or "").strip().lower()
    return {
        "application/pdf": ".pdf",
        "application/vnd.ms-excel": ".xls",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
        "application/zip": ".zip",
        "text/csv": ".csv",
    }.get(mime_type, "")


def _recent_month_buckets(today: date, count: int) -> list[tuple[int, int]]:
    year = today.year
    month = today.month
    buckets: list[tuple[int, int]] = []
    for _ in range(max(count, 1)):
        buckets.append((year, month))
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    return buckets


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
        all_schemes_boost = 120 if "all sbimf schemes" in combined or "all schemes" in combined else 0
        passive_penalty = -30 if "passive" in combined or "index etf fof" in combined else 0
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
                priority_score=(
                    _generic_base_score(ext=ext, document_type="factsheet")
                    + recency_score
                    + all_schemes_boost
                    + passive_penalty
                ),
            )
        )
    docs.sort(key=lambda item: item.priority_score, reverse=True)
    return docs


def _discover_mirae_documents(
    source: AMCDocumentSource,
    document_type: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    doc_type = (document_type or "").strip().lower()
    module_name = MIRAE_MODULE_BY_DOCUMENT_TYPE.get(doc_type)
    if not module_name:
        return []

    listing_url = (
        source.factsheet_page_url
        if doc_type == "factsheet"
        else source.portfolio_disclosure_page_url
    ) or "https://www.miraeassetmf.co.in/downloads"
    try:
        response = _request_with_retry(
            "POST",
            MIRAE_DOWNLOADS_ENDPOINT,
            timeout_seconds=timeout_seconds,
            headers={
                "User-Agent": user_agent,
                "Referer": listing_url,
                "Content-Type": "application/json;charset=utf-8",
            },
            json_payload={
                "request": {
                    "modulename": module_name,
                    "pgno": 1,
                    "pgsize": 100 if doc_type == "portfolio_disclosure" else 20,
                }
            },
        )
        payload = response.json()
    except Exception as exc:
        logger.exception("event=mirae_discovery_failed document_type=%s reason=%s", doc_type, exc)
        return []

    if str(payload.get("ReturnCode", "")) != "0":
        logger.warning("event=mirae_discovery_rejected return_code=%s", payload.get("ReturnCode"))
        return []

    items = payload.get("Data") or []
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except json.JSONDecodeError:
            return []
    if isinstance(items, dict):
        items = items.get("Items") or items.get("data") or []
    if not isinstance(items, list):
        return []

    docs: list[DiscoveredDocument] = []
    seen_urls: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        title = str(item.get("Title") or "").strip()
        raw_url = str(item.get("URL") or "").strip()
        combined = f"{title} {raw_url}".lower()
        if not raw_url or "how_to" in combined or "how to read" in combined:
            continue
        url = urljoin("https://www.miraeassetmf.co.in", raw_url)
        if url in seen_urls:
            continue
        ext = Path(urlsplit(url).path).suffix.lower()
        if doc_type == "factsheet" and ext != ".pdf":
            continue
        if doc_type == "portfolio_disclosure" and ext not in {".xls", ".xlsx", ".xlsm", ".csv", ".zip"}:
            continue
        report_month = _detect_report_month_from_text(combined)
        recency_score = (report_month.year * 12 + report_month.month) * 10 if report_month else 0
        active_boost = 10 if doc_type == "factsheet" and "active" in combined else 0
        seen_urls.add(url)
        docs.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type=doc_type,
                title=title or _human_title_from_url(url),
                url=url,
                discovery_page_url=listing_url,
                file_ext=ext,
                report_month=report_month,
                priority_score=_generic_base_score(ext=ext, document_type=doc_type) + recency_score + active_boost,
            )
        )

    docs.sort(key=lambda item: item.priority_score, reverse=True)
    return docs


def _discover_dsp_factsheet_documents(
    source: AMCDocumentSource,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    listing_url = source.factsheet_page_url or "https://www.dspim.com/downloads"
    try:
        response = _request_with_retry(
            "GET",
            DSP_DOWNLOADS_ENDPOINT,
            timeout_seconds=timeout_seconds,
            headers={"User-Agent": user_agent, "Referer": listing_url},
            params={
                "page": 1,
                "per_page": 20,
                "category": "Information Documents",
                "sub_category": "Factsheets",
            },
        )
        rows = response.json().get("data", [])
    except Exception as exc:
        logger.exception("event=dsp_factsheet_discovery_failed reason=%s", exc)
        return []

    docs: list[DiscoveredDocument] = []
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict) or row.get("is_file") is False:
            continue
        title = str(row.get("title") or "").strip()
        raw_url = str(row.get("pdf_url") or "").strip()
        combined = f"{title} {raw_url}".lower()
        if not raw_url or "factsheet" not in combined:
            continue
        url = urljoin("https://www.dspim.com", raw_url)
        ext = Path(urlsplit(url).path).suffix.lower()
        if ext != ".pdf":
            continue
        report_month = _detect_report_month_from_text(combined)
        recency_score = (report_month.year * 12 + report_month.month) * 10 if report_month else 0
        docs.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type="factsheet",
                title=title or _human_title_from_url(url),
                url=url,
                discovery_page_url=listing_url,
                file_ext=ext,
                report_month=report_month,
                priority_score=_generic_base_score(ext=ext, document_type="factsheet") + recency_score,
            )
        )
    docs.sort(key=lambda item: item.priority_score, reverse=True)
    return docs


def _discover_uti_documents(
    source: AMCDocumentSource,
    document_type: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    doc_type = (document_type or "").strip().lower()
    endpoint = UTI_ENDPOINT_BY_DOCUMENT_TYPE.get(doc_type)
    if not endpoint:
        return []
    listing_url = (
        source.factsheet_page_url
        if doc_type == "factsheet"
        else source.portfolio_disclosure_page_url
    ) or "https://www.utimf.com/downloads"

    rows: list[dict] = []
    for target_month in _recent_month_starts(datetime.now(UTC).date(), count=6):
        try:
            response = _request_with_retry(
                "GET",
                endpoint,
                timeout_seconds=timeout_seconds,
                headers={"User-Agent": user_agent, "Referer": listing_url},
                params={"year": target_month.year, "month": target_month.strftime("%B")},
            )
            payload_rows = response.json().get("rows", [])
        except Exception as exc:
            logger.warning(
                "event=uti_discovery_month_failed document_type=%s month=%s reason=%s",
                doc_type,
                target_month.isoformat(),
                exc,
            )
            continue
        if isinstance(payload_rows, list):
            rows.extend(row for row in payload_rows if isinstance(row, dict))

    docs: list[DiscoveredDocument] = []
    seen_urls: set[str] = set()
    for row in rows:
        title = str(row.get("name") or "").strip()
        raw_url = str(row.get("doc") or row.get("url") or "").strip()
        if not raw_url or raw_url in seen_urls:
            continue
        seen_urls.add(raw_url)
        ext = Path(urlsplit(raw_url).path).suffix.lower()
        low = f"{title} {row.get('category', '')} {raw_url}".lower()
        if doc_type == "factsheet" and ext != ".pdf":
            continue
        if doc_type == "portfolio_disclosure" and ext not in {".xls", ".xlsx", ".xlsm", ".csv", ".zip"}:
            continue
        # The UTI portfolio endpoint also lists riskometer and distribution ZIPs.
        # Only its named portfolio disclosure is valid holdings input.
        if doc_type == "portfolio_disclosure" and "portfolio" not in low:
            continue
        # UTI publishes translated Fund Watch files beside the English pair. The
        # parser and operational-candidate gate intentionally use English Active
        # and Passive factsheets only, so do not let Hindi PDFs enter the queue.
        if doc_type == "factsheet" and "hindi" in low:
            continue
        report_month = _detect_report_month_from_text(
            f"{title} {row.get('month', '')} {row.get('year', '')} {raw_url}"
        )
        if doc_type == "factsheet" and report_month:
            # UTI's Fund Watch publication month trails the contained data month.
            report_month = _previous_month(report_month)
        recency_score = (report_month.year * 12 + report_month.month) * 10 if report_month else 0
        active_boost = 10 if "active" in low else 0
        docs.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type=doc_type,
                title=title or _human_title_from_url(raw_url),
                url=raw_url,
                discovery_page_url=listing_url,
                file_ext=ext,
                report_month=report_month,
                priority_score=(
                    _generic_base_score(ext=ext, document_type=doc_type)
                    + recency_score
                    + active_boost
                ),
            )
        )
    docs.sort(key=lambda item: item.priority_score, reverse=True)
    return docs


def _recent_month_starts(start: date, *, count: int) -> list[date]:
    current = start.replace(day=1)
    months: list[date] = []
    for _ in range(max(count, 1)):
        months.append(current)
        previous_day = current.fromordinal(current.toordinal() - 1)
        current = previous_day.replace(day=1)
    return months


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

    allow_factsheet_portfolio = str(
        os.getenv("MF_ALLOW_FACTSHEET_AS_PORTFOLIO", "")
        or os.getenv("MF_ALLOW_HDFC_FACTSHEET_AS_PORTFOLIO", "")
        or ""
    ).strip().lower() in {"1", "true", "yes", "on"}
    if document_type == "portfolio_disclosure" and allow_factsheet_portfolio and not raw.strip():
        raw = str(os.getenv(f"MF_{amc}_FACTSHEET_DOCUMENT_URLS", "") or "")

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
    keywords = (
        source.factsheet_required_keywords
        if document_type == "factsheet"
        else source.portfolio_required_keywords
    )
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
    if any(blocked in low for blocked in (*GENERIC_EXCLUDE_KEYWORDS, *source.excluded_keywords)):
        return False
    allowed_extensions = (
        source.factsheet_extensions
        if document_type == "factsheet"
        else source.portfolio_extensions
    )
    if allowed_extensions and file_ext not in allowed_extensions:
        return False

    # Require direct signal to avoid picking random legal/compliance PDFs.
    if required_keywords and not any(token in low for token in required_keywords):
        return False

    # Portfolio ingestion should avoid non-portfolio disclosures.
    if document_type == "portfolio_disclosure" and "portfolio" not in low and "holding" not in low:
        if not (
            (adapter_key == "hdfc" and "monthly hdfc" in low)
            or (adapter_key == "hsbc" and "the asset" in low)
        ):
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
    title_month = _detect_report_month_from_text(_icici_title(item))
    if title_month:
        return title_month

    for key in ("applicableMonth", "fileDate"):
        raw = item.get(key)
        if raw in (None, ""):
            continue
        try:
            millis = int(raw)
            return datetime.fromtimestamp(millis / 1000, UTC).date().replace(day=1)
        except (TypeError, ValueError, OSError):
            continue

    return None


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
    today = datetime.now(UTC).date()
    limit_date = date(today.year, today.month, 1)
    for match in NUMERIC_DATE_PATTERN.finditer(text or ""):
        try:
            parsed_dt = date(int(match.group("year")), int(match.group("month")), 1)
        except ValueError:
            continue
        if 2000 <= parsed_dt.year and parsed_dt <= limit_date:
            return parsed_dt
    # Try day-first matches first
    for match in DAY_FIRST_MONTH_PATTERN.finditer(text or ""):
        month = datetime.strptime(match.group("month")[:3], "%b").month
        year = int(match.group("year"))
        parsed_dt = date(year, month, 1)
        if 2000 <= year and parsed_dt <= limit_date:
            return parsed_dt

    # Try month-first/month-only matches
    for match in MONTH_PATTERN.finditer(text or ""):
        month = datetime.strptime(match.group("month")[:3], "%b").month
        year = int(match.group("year"))
        parsed_dt = date(year, month, 1)
        if 2000 <= year and parsed_dt <= limit_date:
            return parsed_dt

    return None


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
    if str(url).startswith("file://"):
        if not local_file_sources_allowed():
            raise PermissionError("local_file_source_not_allowed")
        file_path = Path(urlsplit(url).path.lstrip("/\\"))
        if not file_path.is_file():
            file_path = Path(str(url).replace("file:///", "").replace("file://", ""))
        if file_path.is_file():
            content = file_path.read_bytes()
            resp = requests.Response()
            resp.status_code = 200
            resp._content = content
            resp.url = url
            resp.headers["Content-Type"] = "application/pdf"
            return resp

    method_upper = method.upper()
    last_exc: Exception | None = None
    
    proxy_url = str(os.getenv("MF_HTTP_PROXY", "") or "").strip()
    proxies = None
    if proxy_url:
        proxies = {"http": proxy_url, "https": proxy_url}

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
                    proxies=proxies,
                    verify=not bool(proxies),
                )
            elif method_upper == "GET":
                response = requests.get(
                    url,
                    timeout=timeout_seconds,
                    headers=headers,
                    params=params,
                    proxies=proxies,
                    verify=not bool(proxies),
                )
            elif method_upper == "POST":
                response = requests.post(
                    url,
                    timeout=timeout_seconds,
                    headers=headers,
                    params=params,
                    json=json_payload,
                    proxies=proxies,
                    verify=not bool(proxies),
                )
            else:
                response = requests.request(
                    method=method_upper,
                    url=url,
                    timeout=timeout_seconds,
                    headers=headers,
                    params=params,
                    json=json_payload,
                    proxies=proxies,
                    verify=not bool(proxies),
                )

            # --- Cloudflare/WAF Bypass fallback ---
            if getattr(response, "status_code", 200) in {403, 406} and session is None and method_upper in {"GET", "POST"}:
                try:
                    import httpx
                    client_kwargs = {"http2": True, "verify": not bool(proxies)}
                    if proxies:
                        client_kwargs["proxy"] = proxy_url
                    with httpx.Client(**client_kwargs) as client:
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


def _discover_invesco_documents(
    source: AMCDocumentSource,
    document_type: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    """Invesco serves factsheets from a predictable /docs/default-source/factsheet/ path.

    An earlier revision appended a single hardcoded June-2026 URL at priority 100 with
    `report_month` asserted rather than detected, whenever anchor discovery came back
    empty. That is a point-in-time value: from July onward it would keep injecting a
    stale June document at maximum priority, bypassing the stale-candidate protections
    in `_filter_expected_month_documents`/`_rank_discovered_documents` that exist
    precisely to stop that. Discovery stays live-only; a known-exact official URL for a
    specific month belongs in the reviewed source manifest instead.
    """
    documents = _discover_generic_anchor_documents(
        source,
        document_type=document_type,
        timeout_seconds=timeout_seconds,
        user_agent=user_agent,
    )
    if documents or not _browser_fallback_allowed_for_source(source):
        return documents
    return _discover_invesco_browser_documents(
        source,
        document_type=document_type,
        timeout_seconds=timeout_seconds,
        user_agent=user_agent,
    )


def _discover_invesco_browser_documents(
    source: AMCDocumentSource,
    document_type: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    """Read document links rendered by Invesco's public literature page."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        logger.error("invesco:playwright_not_installed")
        return []

    doc_type = (document_type or "").strip().lower()
    listing_url = (
        source.factsheet_page_url
        if doc_type == "factsheet"
        else source.portfolio_disclosure_page_url
    )
    if not listing_url:
        return []
    timeout_ms = max(5_000, min(int(timeout_seconds * 1_000), 90_000))
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(user_agent=user_agent)
            page = context.new_page()
            page.goto(listing_url, wait_until="networkidle", timeout=timeout_ms)
            candidates = page.locator("a[href]").evaluate_all(
                """anchors => anchors.slice(0, 500).map(anchor => ({
                    title: (anchor.textContent || "").trim(),
                    href: anchor.href || "",
                    context: (anchor.closest("li, article, section, div")?.textContent || "").trim().slice(0, 800)
                }))"""
            )
            browser.close()
    except Exception as exc:
        logger.warning("invesco:browser_discovery_failed document_type=%s error=%s", doc_type, exc)
        return []

    required_keywords = _required_keywords_for_generic_source(source, doc_type)
    allowed_extensions = (
        source.factsheet_extensions
        if doc_type == "factsheet"
        else source.portfolio_extensions
    )
    documents: list[DiscoveredDocument] = []
    seen_urls: set[str] = set()
    for candidate in candidates:
        url = str(candidate.get("href") or "").strip()
        if not url or url in seen_urls:
            continue
        seen_urls.add(url)
        title = _clean_discovery_text(candidate.get("title") or "") or _human_title_from_url(url)
        context_text = _clean_discovery_text(candidate.get("context") or "")
        combined = f"{title} {context_text} {url}"
        ext = Path(urlsplit(url).path).suffix.lower() or _infer_file_ext_from_text(combined)
        if ext not in allowed_extensions or not _generic_candidate_allowed(
            source, combined, doc_type, ext, required_keywords
        ):
            continue
        report_month = _detect_report_month_from_text(combined)
        recency_score = (report_month.year * 12 + report_month.month) * 10 if report_month else 0
        documents.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type=doc_type,
                title=title,
                url=url,
                discovery_page_url=listing_url,
                file_ext=ext,
                report_month=report_month,
                priority_score=_generic_base_score(ext=ext, document_type=doc_type) + recency_score,
            )
        )
    documents.sort(key=lambda item: item.priority_score, reverse=True)
    return documents


def _discover_hsbc_documents(
    source: AMCDocumentSource,
    document_type: str,
    timeout_seconds: float,
    user_agent: str,
) -> list[DiscoveredDocument]:
    """HSBC publishes its monthly factsheet as "The Asset" on assetmanagement.hsbc.co.in.

    An earlier revision of this function returned a single hardcoded absolute path on
    one developer's Downloads folder. That silently returned zero documents in any
    hosted run -- indistinguishable from "the AMC has not published yet" -- and produced
    a document with no official host and no reproducible provenance. Discovery must go
    through the official page; a known-exact official URL belongs in the reviewed source
    manifest (`backend/config/mf_document_sources.json`, loaded via
    MF_SOURCE_MANIFEST_PATH), which is the sanctioned mechanism for that, and local PDFs
    belong in `scripts/smoke_parse_mf_raw_documents.py --download-only`.
    """
    documents = _discover_generic_anchor_documents(
        source,
        document_type=document_type,
        timeout_seconds=timeout_seconds,
        user_agent=user_agent,
    )
    normalized: list[DiscoveredDocument] = []
    for document in documents:
        # HSBC's URL slug is the stable reporting-month signal. The listing title can
        # contain a publication date or stale CMS text, so URL evidence wins here.
        report_month = (
            _detect_report_month_from_text(document.url)
            or _detect_report_month_from_text(document.title)
            or document.report_month
        )
        if report_month and report_month != document.report_month:
            document = replace(
                document,
                report_month=report_month,
                priority_score=(
                    _generic_base_score(
                        ext=document.file_ext,
                        document_type=document_type,
                    )
                    + (report_month.year * 12 + report_month.month) * 10
                    + 60
                ),
            )
        normalized.append(document)
    return sorted(
        normalized,
        key=lambda item: (
            item.report_month is not None,
            item.report_month or date.min,
            item.priority_score,
        ),
        reverse=True,
    )
