import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument
from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.sources.registry import AMCDocumentSource
from app.mf_ingestion.parsers.adapters.ppfas_adapter import classify_documents, detect_file_ext
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument

logger = logging.getLogger(__name__)

class AxisAdapter(BaseAMCAdapter):
    amc_code = "AXIS"
    adapter_key = "axis"

    def __init__(self, user_agent: str = "Mozilla/5.0", timeout_seconds: int = 30) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    def discover_documents(self, source: AMCDocumentSource, document_type: str) -> List[DiscoveredDocument]:
        return self.fetch_documents(source, document_type)

    def parse_holdings(self, excel_frames: list, pdf_table_frames: list, pdf_text: str, context: ParseContext) -> ParsedDocument:
        # TODO: Implement Axis specific parsing logic when available
        return ParsedDocument(
            scheme_name="",
            report_month=context.report_month,
            holdings=[],
            warnings=["axis_parsing_not_implemented"],
            confidence_score=0.0
        )

    def fetch_documents(self, source: AMCDocumentSource, document_type: str) -> List[DiscoveredDocument]:
        attempted_tiers: list[str] = []

        attempted_tiers.append("manual_env")
        env_docs = self._docs_from_env(source, document_type)
        if env_docs:
            logger.info("Axis: using %d document(s) from env var MF_AXIS_%s_DOCUMENT_URLS.",
                        len(env_docs),
                        "FACTSHEET" if document_type == "factsheet" else "PORTFOLIO")
            return env_docs

        attempted_tiers.append("axis_page")
        docs = self.fetch_from_axis_api_or_page(source, document_type)

        if not docs:
            logger.info("Axis API/Page fetch yielded no documents. Falling back to AMFI.")
            attempted_tiers.append("amfi")
            docs = self.fetch_from_amfi(source, document_type)

        if not docs:
            logger.info("AMFI fallback yielded no documents. Falling back to Playwright.")
            attempted_tiers.append("playwright")
            docs = self.fetch_with_playwright(source, document_type)

        if not docs:
            logger.warning(
                "axis:no_source_documents_found document_type=%s attempted_tiers=%s",
                document_type,
                ",".join(attempted_tiers),
            )
        return docs

    def _docs_from_env(self, source: AMCDocumentSource, document_type: str) -> List[DiscoveredDocument]:
        """Read comma-separated direct document URLs from MF_AXIS_FACTSHEET_DOCUMENT_URLS
        or MF_AXIS_PORTFOLIO_DOCUMENT_URLS, identical to the amc_downloader manual-URL pattern."""
        suffix = "FACTSHEET_DOCUMENT_URLS" if document_type == "factsheet" else "PORTFOLIO_DOCUMENT_URLS"
        env_name = f"MF_AXIS_{suffix}"
        raw = str(os.getenv(env_name, "") or "").strip()
        if not raw:
            return []

        listing_url = (
            source.factsheet_page_url if document_type == "factsheet"
            else source.portfolio_disclosure_page_url
        ) or "https://www.axismf.com/downloads"

        docs: List[DiscoveredDocument] = []
        seen: set = set()
        for token in raw.split(","):
            url = token.strip()
            if not url or url in seen:
                continue
            seen.add(url)
            ext = Path(urlsplit(url).path).suffix.lower() or (".pdf" if document_type == "factsheet" else ".xlsx")
            title = Path(urlsplit(url).path).name or "document"
            docs.append(DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type=document_type,
                title=title,
                url=url,
                discovery_page_url=listing_url,
                file_ext=ext,
                report_month=None,
                priority_score=9_000_000,
            ))
        return docs

    def fetch_from_axis_api_or_page(self, source: AMCDocumentSource, document_type: str) -> List[DiscoveredDocument]:
        """
        Attempt 1: Tries to fetch documents via standard HTTP request.
        If Axis exposes the links in raw HTML or we uncover their hidden API, this handles it.
        """
        page_url = source.factsheet_page_url if document_type == "factsheet" else source.portfolio_disclosure_page_url
        if not page_url:
            return []

        try:
            response = requests.get(
                page_url, 
                headers={"User-Agent": self.user_agent}, 
                timeout=self.timeout_seconds
            )
            response.raise_for_status()
            
            # Look for direct links in HTML
            soup = BeautifulSoup(response.text, "html.parser")
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ".pdf" in href.lower() or ".xlsx" in href.lower() or ".xls" in href.lower():
                    links.append({
                        "title": a.get_text(strip=True) or href.split("/")[-1],
                        "url": href if href.startswith("http") else f"https://www.axismf.com{href}",
                        "context_text": a.get_text(strip=True),
                        "file_ext": detect_file_ext(href)
                    })
                    
            docs = classify_documents(source, document_type, links, page_url)
            docs.sort(key=lambda d: d.priority_score, reverse=True)
            return docs
            
        except Exception as e:
            logger.warning(f"Error fetching from Axis API/Page: {e}")
            return []

    def fetch_from_amfi(self, source: AMCDocumentSource, document_type: str) -> List[DiscoveredDocument]:
        """
        Attempt 2: Fallback to AMFI if applicable.
        (Currently a stub as AMFI mostly provides NAVs rather than Factsheets/Portfolios).
        """
        # TODO: Implement AMFI specific document discovery if AMFI starts hosting them.
        return []

    def fetch_with_playwright(self, source: AMCDocumentSource, document_type: str) -> List[DiscoveredDocument]:
        """
        Attempt 3: Heavy Headless Browser fallback.
        Uses Playwright to render the SPA and extract the dynamically loaded document links.
        """
        try:
            from playwright.sync_api import sync_playwright
        except ImportError:
            logger.error("Playwright is not installed. Cannot use Playwright fallback for Axis.")
            return []

        page_url = source.factsheet_page_url if document_type == "factsheet" else source.portfolio_disclosure_page_url
        if not page_url:
            return []

        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(user_agent=self.user_agent)
                page = context.new_page()
                
                page.goto(page_url, wait_until="domcontentloaded", timeout=20000)
                try:
                    page.wait_for_load_state("load", timeout=10000)
                except Exception:
                    logger.info("Axis Playwright load wait timed out; parsing current DOM.")
                page.wait_for_timeout(3000)
                
                html = page.content()
                browser.close()
                
            links = _axis_download_links_from_html(html, page_url)
                    
            docs = classify_documents(source, document_type, links, page_url)
            docs.sort(key=lambda d: d.priority_score, reverse=True)
            return docs
            
        except Exception as e:
            logger.warning(f"Error fetching via Playwright fallback: {e}")
            return []


def _axis_download_links_from_html(html: str, page_url: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html or "", "html.parser")
    links: list[dict[str, str]] = []
    seen: set[str] = set()
    for anchor in soup.find_all("a", href=True):
        href = str(anchor.get("href") or "").strip()
        if not _axis_is_download_url(href):
            continue
        absolute_url = urljoin(page_url, href)
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        title = anchor.get_text(strip=True) or Path(urlsplit(absolute_url).path).name
        links.append(
            {
                "title": title,
                "url": absolute_url,
                "context_text": anchor.parent.get_text(" ", strip=True) if anchor.parent else title,
                "file_ext": detect_file_ext(absolute_url),
            }
        )
    for match in re.finditer(r"https?://[^\s\"'<>]+?\.(?:pdf|xlsx?|xlsm)(?:\?[^\s\"'<>]*)?", html or "", re.IGNORECASE):
        absolute_url = match.group(0)
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        links.append(
            {
                "title": Path(urlsplit(absolute_url).path).name,
                "url": absolute_url,
                "context_text": absolute_url,
                "file_ext": detect_file_ext(absolute_url),
            }
        )
    return links


def _axis_is_download_url(value: str) -> bool:
    return bool(re.search(r"\.(?:pdf|xlsx?|xlsm)(?:\?|$)", value or "", flags=re.IGNORECASE))
