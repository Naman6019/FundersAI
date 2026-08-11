"""Build a read-only Kotak monthly HTML factsheet to AMFI ISIN review report."""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.mf_ingestion.services.kotak_html_identity import (
    discover_kotak_factsheet_pages,
    inspect_kotak_factsheet_page,
    parse_amfi_navall_kotak_identities,
    resolve_kotak_page_identity,
)

AMFI_NAVALL_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
KOTAK_BROWSER_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/138.0.0.0 Safari/537.36"
)


def _require_kotak_host(url: str) -> None:
    host = (urlsplit(url).hostname or "").lower().rstrip(".")
    if host != "kotakmf.com" and not host.endswith(".kotakmf.com"):
        raise RuntimeError(f"kotak_archive_redirected_to_non_official_host:{host or 'missing'}")


class _KotakTextFetcher:
    def __init__(self, session: requests.Session, *, browser_fallback: bool) -> None:
        self.session = session
        self.browser_fallback = browser_fallback
        self._playwright = None
        self._browser = None
        self._page = None

    def get(self, url: str) -> tuple[str, str]:
        try:
            response = self.session.get(url, timeout=45)
            response.raise_for_status()
            _require_kotak_host(response.url)
            return response.url, response.text
        except Exception:
            if not self.browser_fallback:
                raise
        return self._get_with_browser(url)

    def close(self) -> None:
        if self._browser is not None:
            self._browser.close()
        if self._playwright is not None:
            self._playwright.stop()

    def _get_with_browser(self, url: str) -> tuple[str, str]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("kotak_browser_fallback_unavailable") from exc
        if self._page is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(headless=True)
            self._page = self._browser.new_page(user_agent=KOTAK_BROWSER_USER_AGENT)
        self._page.goto(url, wait_until="domcontentloaded", timeout=60_000)
        self._page.wait_for_timeout(1_000)
        final_url = self._page.url
        _require_kotak_host(final_url)
        return final_url, self._page.content()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only exact Kotak HTML factsheet to AMFI ISIN review inventory."
    )
    parser.add_argument("--archive-url", required=True)
    parser.add_argument("--expected-month", required=True, help="YYYY-MM")
    parser.add_argument("--output", required=True)
    parser.add_argument("--max-pages", type=int, default=500)
    parser.add_argument(
        "--browser-fallback",
        action="store_true",
        help="Use Kotak's approved bounded browser fallback after an official HTTP request fails.",
    )
    args = parser.parse_args()
    expected_month = date.fromisoformat(f"{args.expected_month}-01")

    session = requests.Session()
    session.headers.update({"User-Agent": KOTAK_BROWSER_USER_AGENT})
    fetcher = _KotakTextFetcher(session, browser_fallback=args.browser_fallback)
    try:
        archive_url, archive_html = fetcher.get(args.archive_url)
        pages = discover_kotak_factsheet_pages(archive_html, archive_url)

        navall = session.get(AMFI_NAVALL_URL, timeout=60)
        navall.raise_for_status()
        amfi_identities = parse_amfi_navall_kotak_identities(navall.text)

        results = []
        for page in pages[: max(args.max_pages, 0)]:
            _page_url, page_html = fetcher.get(page.url)
            inspection = inspect_kotak_factsheet_page(
                page,
                page_html,
                expected_month=expected_month,
            )
            resolution = resolve_kotak_page_identity(inspection, amfi_identities)
            results.append(asdict(resolution))
    finally:
        fetcher.close()

    payload = {
        "mode": "review_only",
        "archive_url": archive_url,
        "expected_month": expected_month.isoformat(),
        "amfi_navall_url": AMFI_NAVALL_URL,
        "amfi_identity_count": len(amfi_identities),
        "page_count": len(pages),
        "reviewed_page_count": len(results),
        "verified_count": sum(item["status"] == "verified" for item in results),
        "needs_review_count": sum(item["status"] != "verified" for item in results),
        "results": results,
    }
    Path(args.output).write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


if __name__ == "__main__":
    main()
