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
        # Tier 0: Env-injected URLs (highest priority, used when site blocks CI runners)
        env_docs = self._docs_from_env(source, document_type)
        if env_docs:
            logger.info("Axis: using %d document(s) from env var MF_AXIS_%s_DOCUMENT_URLS.",
                        len(env_docs),
                        "FACTSHEET" if document_type == "factsheet" else "PORTFOLIO")
            return env_docs

        # Tier 1: Static HTML / known API endpoint
        docs = self.fetch_from_axis_api_or_page(source, document_type)

        if not docs:
            logger.info("Axis API/Page fetch yielded no documents. Falling back to AMFI.")
            docs = self.fetch_from_amfi(source, document_type)

        if not docs:
            logger.info("AMFI fallback yielded no documents. Falling back to Playwright.")
            docs = self.fetch_with_playwright(source, document_type)

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
                
                # Navigate and wait for SPA to load
                page.goto(page_url, wait_until="networkidle", timeout=20000)
                
                # We wait a bit extra for React components to finish rendering their tables
                page.wait_for_timeout(3000)
                
                html = page.content()
                browser.close()
                
            # Now parse the fully rendered HTML
            soup = BeautifulSoup(html, "html.parser")
            links = []
            for a in soup.find_all("a", href=True):
                href = a["href"]
                if ".pdf" in href.lower() or ".xlsx" in href.lower() or ".xls" in href.lower():
                    links.append({
                        "title": a.get_text(strip=True) or href.split("/")[-1],
                        "url": href if href.startswith("http") else f"https://www.axismf.com{href}",
                        "context_text": a.parent.get_text(strip=True) if a.parent else a.get_text(strip=True),
                        "file_ext": detect_file_ext(href)
                    })
                    
            docs = classify_documents(source, document_type, links, page_url)
            docs.sort(key=lambda d: d.priority_score, reverse=True)
            return docs
            
        except Exception as e:
            logger.warning(f"Error fetching via Playwright fallback: {e}")
            return []
