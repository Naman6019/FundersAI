from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument
from app.mf_ingestion.sources.registry import AMCDocumentSource


class BoundedLLMPageRecovery:
    """Suggest existing official-page links; it cannot fetch candidate URLs or persist data."""

    def __init__(self, *, enabled: bool, model: str, timeout_seconds: float = 30) -> None:
        self.enabled = enabled
        self.model = model.strip()
        self.timeout_seconds = timeout_seconds

    def __call__(self, source: AMCDocumentSource, document_type: str) -> list[DiscoveredDocument]:
        if not self.enabled or not self.model:
            return []
        page_url = source.factsheet_page_url if document_type == "factsheet" else source.portfolio_disclosure_page_url
        if not page_url:
            return []
        response = requests.get(
            page_url,
            headers={"User-Agent": os.getenv("MF_INGESTION_USER_AGENT", "FundersAIResearchBot/1.0")},
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        available = _page_links(page_url, response.text)
        if not available:
            return []
        selected_urls = _select_existing_links_with_llm(
            model=self.model,
            document_type=document_type,
            page_url=page_url,
            links=available,
        )
        return [
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type=document_type,
                title=available[url],
                url=url,
                discovery_page_url=page_url,
                file_ext=Path(urlsplit(url).path).suffix.lower(),
                report_month=None,
                priority_score=1,
            )
            for url in selected_urls
            if url in available
        ]


def _page_links(page_url: str, html: str) -> dict[str, str]:
    links: dict[str, str] = {}
    for anchor in BeautifulSoup(html, "html.parser").find_all("a", href=True):
        url = urljoin(page_url, str(anchor["href"]).strip())
        if urlsplit(url).scheme in {"http", "https"}:
            links[url] = anchor.get_text(" ", strip=True) or url
    return links


def _select_existing_links_with_llm(*, model: str, document_type: str, page_url: str, links: dict[str, str]) -> list[str]:
    api_key = os.getenv("OPENROUTER_API_KEY", "").strip() or os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
        return []
    base_url = os.getenv("OPENROUTER_BASE_URL", "").strip() or "https://api.openai.com/v1/chat/completions"
    response = requests.post(
        base_url,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        timeout=30,
        json={
            "model": model,
            "response_format": {"type": "json_object"},
            "max_tokens": 300,
            "messages": [
                {
                    "role": "system",
                    "content": "Select up to three listed official-page URLs for the requested document type. Return JSON only: {\"urls\":[...]}. Never invent a URL.",
                },
                {
                    "role": "user",
                    "content": json.dumps({"page_url": page_url, "document_type": document_type, "links": links}),
                },
            ],
        },
    )
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    urls = json.loads(content).get("urls") or []
    return [str(url).strip() for url in urls[:3] if str(url).strip() in links]
