from __future__ import annotations

import logging
import random
import re
import time
from datetime import date, datetime
from urllib.parse import urljoin, urlparse

import pandas as pd
import requests
from bs4 import BeautifulSoup
from requests import Session
from requests.exceptions import ConnectionError, Timeout

from app.mf_ingestion.constants import AMC_PPFAS, PPFAS_FLEXI_CAP_SCHEME_CANONICAL
from app.mf_ingestion.downloaders.base_downloader import DiscoveredDocument
from app.mf_ingestion.normalizers.column_normalizer import normalize_column_name, normalize_columns
from app.mf_ingestion.normalizers.instrument_normalizer import normalize_instrument_name
from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument
from app.mf_ingestion.sources.registry import AMCDocumentSource

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "MarketMindResearchBot/1.0 contact: YOUR_EMAIL_HERE"
REQUEST_TIMEOUT_SECONDS = 30
MAX_NETWORK_RETRIES = 2

FACTSHEET_KEYWORDS = (
    "factsheet",
    "fact sheet",
    "fact-sheet",
    "monthly factsheet",
    "fund factsheet",
    "mf factsheet",
    "mf-factsheet",
)
PORTFOLIO_KEYWORDS = (
    "portfolio",
    "monthly portfolio",
    "monthly portfolio report",
    "portfolio report",
    "portfolio disclosure",
    "scheme portfolio",
    "monthly portfolio statement",
    "consolidated disclosure",
    "monthly disclosure",
)
TER_KEYWORDS = (
    "total expense ratio",
    "expense ratio",
    "ter",
)

FILE_PRIORITY = {
    ".xlsx": 400,
    ".xls": 300,
    ".csv": 200,
    ".pdf": 100,
}
DEFAULT_UNKNOWN_FILE_SCORE = 80
MAX_SECONDARY_PAGES = 10

MONTH_PATTERN = re.compile(
    r"(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*(?:[\s\-_]+(?P<day>\d{1,2}))?[\s\-_]+(?P<year>20\d{2})",
    re.IGNORECASE,
)
ISIN_PATTERN = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}\d\b")
SCHEME_PATTERN = re.compile(r"(Parag\s+Parikh[\w\s&\-/]+Fund)", re.IGNORECASE)
SUMMARY_ROW_MARKERS = (
    "sub total",
    "subtotal",
    "total",
    "grand total",
    "net current assets",
    "net receivables",
    "cash and cash equivalents",
    "cash & cash equivalents",
    "treps",
    "triparty repo",
    "reverse repo",
    "monthly portfolio statement",
    "name of the instrument",
    "equity & equity related",
    "debt instruments",
    "mutual fund units",
)


class PPFASAdapter(BaseAMCAdapter):
    amc_code = AMC_PPFAS
    adapter_key = "ppfas"

    def __init__(self, user_agent: str = DEFAULT_USER_AGENT, timeout_seconds: int = REQUEST_TIMEOUT_SECONDS) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds
        self._request_count = 0
        self.session = self.get_session()

    def get_session(self) -> Session:
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
        )
        return session

    def fetch_page(self, url: str) -> str:
        logger.info("event=ppfas_fetch_page url=%s", url)
        response = self._request("GET", url, session=self.session)
        return response.text

    def has_indian_citizen_confirmation(self, html: str) -> bool:
        if not html:
            return False
        soup = BeautifulSoup(html, "html.parser")
        text = " ".join(soup.stripped_strings).lower()
        markers = (
            "indian citizen",
            "citizen of india",
            "resident indian",
            "eligibility",
            "confirm",
        )
        return any(marker in text for marker in markers)

    def handle_confirmation(self, session: Session, url: str, html: str) -> str:
        soup = BeautifulSoup(html, "html.parser")
        form = soup.find("form")
        if form is None:
            raise RuntimeError(
                "PPFAS confirmation screen detected but no standard HTML form was found. Manual review required."
            )

        method = (form.get("method") or "GET").upper()
        action = form.get("action") or url
        action_url = urljoin(url, action)
        payload = build_confirmation_payload(form)

        logger.info("event=ppfas_confirmation_detected url=%s method=%s action=%s", url, method, action_url)
        if method == "POST":
            self._request("POST", action_url, session=session, data=payload)
        else:
            self._request("GET", action_url, session=session, params=payload)

        logger.info("event=ppfas_confirmation_submitted url=%s", url)
        refreshed = self._request("GET", url, session=session)
        return refreshed.text

    def discover_factsheet_documents(self, source: AMCDocumentSource) -> list[DiscoveredDocument]:
        if not source.factsheet_page_url:
            return []
        html = self.fetch_page(source.factsheet_page_url)
        if source.requires_confirmation and self.has_indian_citizen_confirmation(html):
            html = self.handle_confirmation(self.session, source.factsheet_page_url, html)

        links = extract_anchor_links(source.factsheet_page_url, html)
        logger.info("event=ppfas_links_found document_type=factsheet count=%s", len(links))
        docs = classify_documents(source, "factsheet", links, source.factsheet_page_url)
        if not docs:
            docs = self._discover_from_secondary_pages(
                source=source,
                document_type="factsheet",
                base_page_url=source.factsheet_page_url,
                parent_links=links,
            )
        docs.sort(key=lambda item: item.priority_score, reverse=True)
        if docs:
            logger.info("event=ppfas_selected_link document_type=factsheet url=%s", docs[0].url)
        return docs

    def discover_portfolio_disclosure_documents(self, source: AMCDocumentSource) -> list[DiscoveredDocument]:
        if not source.portfolio_disclosure_page_url:
            return []
        html = self.fetch_page(source.portfolio_disclosure_page_url)
        if source.requires_confirmation and self.has_indian_citizen_confirmation(html):
            html = self.handle_confirmation(self.session, source.portfolio_disclosure_page_url, html)

        links = extract_anchor_links(source.portfolio_disclosure_page_url, html)
        logger.info("event=ppfas_links_found document_type=portfolio_disclosure count=%s", len(links))
        docs = classify_documents(source, "portfolio_disclosure", links, source.portfolio_disclosure_page_url)
        if not docs:
            docs = self._discover_from_secondary_pages(
                source=source,
                document_type="portfolio_disclosure",
                base_page_url=source.portfolio_disclosure_page_url,
                parent_links=links,
            )
        docs.sort(key=lambda item: item.priority_score, reverse=True)
        if docs:
            logger.info("event=ppfas_selected_link document_type=portfolio_disclosure url=%s", docs[0].url)
        return docs

    def discover_documents(self, source: AMCDocumentSource, document_type: str) -> list[DiscoveredDocument]:
        doc_type = (document_type or "").strip().lower()
        if doc_type == "factsheet":
            return self.discover_factsheet_documents(source)
        if doc_type == "portfolio_disclosure":
            return self.discover_portfolio_disclosure_documents(source)
        raise ValueError(f"Unsupported document_type for PPFAS: {document_type}")

    def download_document(self, url: str) -> requests.Response:
        logger.info("event=ppfas_download_file url=%s", url)
        return self._request("GET", url, session=self.session)

    def _discover_from_secondary_pages(
        self,
        source: AMCDocumentSource,
        document_type: str,
        base_page_url: str,
        parent_links: list[dict[str, str]],
    ) -> list[DiscoveredDocument]:
        page_candidates = _select_secondary_page_candidates(base_page_url, parent_links, document_type)
        logger.info(
            "event=ppfas_secondary_discovery_start document_type=%s candidate_pages=%s",
            document_type,
            len(page_candidates),
        )

        docs: list[DiscoveredDocument] = []
        for page_url in page_candidates[:MAX_SECONDARY_PAGES]:
            try:
                child_html = self.fetch_page(page_url)
                child_links = extract_anchor_links(page_url, child_html)
                docs.extend(classify_documents(source, document_type, child_links, base_page_url))
            except Exception as exc:
                logger.warning(
                    "event=ppfas_secondary_discovery_failed document_type=%s page_url=%s reason=%s",
                    document_type,
                    page_url,
                    exc,
                )
                continue

        dedup: dict[str, DiscoveredDocument] = {}
        for doc in docs:
            if doc.url not in dedup or doc.priority_score > dedup[doc.url].priority_score:
                dedup[doc.url] = doc
        logger.info(
            "event=ppfas_secondary_discovery_complete document_type=%s discovered=%s",
            document_type,
            len(dedup),
        )
        return list(dedup.values())

    def _request(self, method: str, url: str, session: Session | None = None, **kwargs) -> requests.Response:
        if self._request_count > 0:
            time.sleep(random.uniform(1.0, 2.0))

        self._request_count += 1
        attempts = MAX_NETWORK_RETRIES + 1
        for attempt in range(1, attempts + 1):
            try:
                active_session = session or self.session
                response = active_session.request(method, url, timeout=self.timeout_seconds, allow_redirects=True, **kwargs)
                if response.status_code in (401, 403, 429):
                    raise RuntimeError(f"PPFAS request blocked with status {response.status_code}. Manual review required.")
                response.raise_for_status()
                return response
            except (Timeout, ConnectionError) as exc:
                if attempt >= attempts:
                    raise RuntimeError(f"PPFAS network request failed after retries: {exc}") from exc
            except requests.HTTPError as exc:
                raise RuntimeError(f"PPFAS HTTP request failed: {exc}") from exc

        raise RuntimeError("PPFAS request failed unexpectedly.")

    def parse_holdings(
        self,
        excel_frames: list[pd.DataFrame],
        pdf_table_frames: list[pd.DataFrame],
        pdf_text: str,
        context: ParseContext,
    ) -> ParsedDocument:
        candidates: list[dict] = []
        warnings: list[str] = []

        for frame in excel_frames:
            parsed = _parse_holdings_frame(frame, context)
            if parsed:
                candidates.append(parsed)

        for frame in pdf_table_frames:
            parsed = _parse_holdings_frame(frame, context)
            if parsed:
                candidates.append(parsed)

        if not candidates and pdf_text:
            parsed = _parse_holdings_text(pdf_text, context)
            if parsed:
                candidates.append(parsed)

        if not candidates:
            return ParsedDocument(
                scheme_name="",
                report_month=context.report_month,
                holdings=[],
                warnings=["ppfas_holdings_not_found_in_document"],
                confidence_score=0.0,
            )

        best = max(candidates, key=lambda item: item.get("selection_score", 0.0))
        if best.get("warnings"):
            warnings.extend(best["warnings"])

        return ParsedDocument(
            scheme_name=best.get("scheme_name") or PPFAS_FLEXI_CAP_SCHEME_CANONICAL,
            report_month=best.get("report_month") or context.report_month,
            holdings=best.get("holdings", []),
            metrics=best.get("metrics", {}),
            warnings=sorted(set(warnings)),
            confidence_score=float(best.get("confidence_score", 0.0)),
        )


def build_confirmation_payload(form) -> dict[str, str]:
    payload: dict[str, str] = {}
    for input_tag in form.find_all("input"):
        name = (input_tag.get("name") or "").strip()
        if not name:
            continue

        field_type = (input_tag.get("type") or "text").strip().lower()
        if field_type in {"checkbox", "radio"} and not input_tag.has_attr("checked"):
            continue

        payload[name] = input_tag.get("value") or ""
    return payload


def extract_anchor_links(base_url: str, html: str) -> list[dict[str, str]]:
    soup = BeautifulSoup(html, "html.parser")
    links: list[dict[str, str]] = []
    for anchor in soup.select("a[href]"):
        target = _extract_anchor_target(anchor, base_url)
        if not target:
            continue
        resolved = target
        parsed = urlparse(resolved)
        file_ext = detect_file_ext(parsed.path)
        title = " ".join(anchor.stripped_strings).strip() or parsed.path.rsplit("/", 1)[-1]
        context_text = " ".join(anchor.parent.stripped_strings).strip() if anchor.parent else title
        links.append(
            {
                "title": title,
                "href": (anchor.get("href") or "").strip(),
                "url": resolved,
                "file_ext": file_ext,
                "context_text": context_text,
            }
        )

    for option in soup.select("option[value]"):
        value = (option.get("value") or "").strip()
        if not value or value in {"#", "0", "-1"}:
            continue
        if not _looks_like_urlish_value(value):
            continue
        resolved = urljoin(base_url, value)
        parsed = urlparse(resolved)
        title = " ".join(option.stripped_strings).strip() or parsed.path.rsplit("/", 1)[-1]
        links.append(
            {
                "title": title,
                "href": value,
                "url": resolved,
                "file_ext": detect_file_ext(parsed.path),
                "context_text": title,
            }
        )
    return links


def classify_documents(
    source: AMCDocumentSource,
    document_type: str,
    links: list[dict[str, str]],
    discovery_page_url: str,
) -> list[DiscoveredDocument]:
    docs: list[DiscoveredDocument] = []
    allowed_file_exts = {".pdf", ".xls", ".xlsx", ".csv"}
    for link in links:
        title = link.get("title") or ""
        url = link.get("url") or ""
        context_text = link.get("context_text") or ""
        file_ext = (link.get("file_ext") or "").lower()
        combined = f"{title} {context_text} {url}".lower()
        if document_type == "factsheet" and not _looks_like_factsheet_link(combined, url):
            continue
        if document_type == "portfolio_disclosure" and not _looks_like_portfolio_link(combined, url):
            continue

        if not file_ext:
            file_ext = infer_file_ext_from_text(combined)
        if file_ext not in allowed_file_exts:
            continue
        report_month = detect_report_month(combined)
        base_score = FILE_PRIORITY.get(file_ext, DEFAULT_UNKNOWN_FILE_SCORE)
        month_score = 50 if report_month else 0
        recency_score = 0
        if report_month:
            recency_score = (report_month.year * 12 + report_month.month) * 10
        ter_penalty = -80 if any(keyword in combined for keyword in TER_KEYWORDS) else 0
        docs.append(
            DiscoveredDocument(
                amc_name=source.amc_name,
                amc_code=source.amc_code,
                document_type=document_type,
                title=title,
                url=url,
                discovery_page_url=discovery_page_url,
                file_ext=file_ext,
                report_month=report_month,
                priority_score=base_score + month_score + recency_score + ter_penalty,
            )
        )
    return docs


def _looks_like_factsheet_link(combined_text: str, url: str) -> bool:
    text = (combined_text or "").lower()
    link = (url or "").lower()
    if "/portfolio-disclosure/" in link:
        return False
    if "/factsheet/" in link:
        return True
    has_factsheet = any(keyword in text for keyword in FACTSHEET_KEYWORDS)
    has_portfolio = any(keyword in text for keyword in PORTFOLIO_KEYWORDS)
    return has_factsheet and not has_portfolio


def _looks_like_portfolio_link(combined_text: str, url: str) -> bool:
    text = (combined_text or "").lower()
    link = (url or "").lower()
    return any(keyword in text for keyword in PORTFOLIO_KEYWORDS) or "/portfolio-disclosure/" in link


def detect_file_ext(path: str) -> str:
    clean = path.split("?", 1)[0].strip().lower()
    if "." not in clean:
        return ""
    return "." + clean.rsplit(".", 1)[-1]


def infer_file_ext_from_text(text: str) -> str:
    low = (text or "").lower()
    for ext in (".xlsx", ".xls", ".csv", ".pdf"):
        if ext in low:
            return ext
    return ""


def _select_secondary_page_candidates(base_page_url: str, links: list[dict[str, str]], document_type: str) -> list[str]:
    candidates: list[str] = []
    base_host = urlparse(base_page_url).netloc.lower()
    keywords = FACTSHEET_KEYWORDS if document_type == "factsheet" else PORTFOLIO_KEYWORDS
    downloadable_exts = {".pdf", ".xls", ".xlsx", ".csv"}
    for link in links:
        url = link.get("url") or ""
        title = link.get("title") or ""
        context_text = link.get("context_text") or ""
        file_ext = (link.get("file_ext") or "").lower()
        if file_ext in downloadable_exts:
            continue
        parsed = urlparse(url)
        if parsed.netloc.lower() != base_host:
            continue
        combined = f"{title} {context_text} {url}".lower()
        if any(keyword in combined for keyword in keywords):
            if url not in candidates:
                candidates.append(url)
    return candidates


def _extract_anchor_target(anchor, base_url: str) -> str:
    href = (anchor.get("href") or "").strip()
    if _is_real_link_target(href):
        return urljoin(base_url, href)

    for attr_name in ("data-href", "data-url", "data-link"):
        value = (anchor.get(attr_name) or "").strip()
        if _is_real_link_target(value):
            return urljoin(base_url, value)

    onclick = (anchor.get("onclick") or "").strip()
    onclick_url = _extract_url_from_onclick(onclick)
    if onclick_url:
        return urljoin(base_url, onclick_url)
    return ""


def _extract_url_from_onclick(onclick: str) -> str:
    if not onclick:
        return ""
    patterns = [
        r"""window\.open\(\s*['"](?P<url>[^'"]+)['"]""",
        r"""location\.href\s*=\s*['"](?P<url>[^'"]+)['"]""",
        r"""['"](?P<url>(?:https?://|/|\.\./|\./)[^'"]+)['"]""",
    ]
    for pattern in patterns:
        match = re.search(pattern, onclick, flags=re.IGNORECASE)
        if match:
            return (match.group("url") or "").strip()
    return ""


def _is_real_link_target(value: str) -> bool:
    if not value:
        return False
    lowered = value.lower()
    if lowered in {"#", "javascript:void(0)", "javascript:void(0);", "javascript:;", "javascript:"}:
        return False
    return True


def _looks_like_urlish_value(value: str) -> bool:
    lowered = value.lower()
    return lowered.startswith(("http://", "https://", "/", "../", "./")) or any(
        ext in lowered for ext in (".pdf", ".xls", ".xlsx", ".csv", ".php")
    )


def detect_report_month(text: str) -> date | None:
    cleaned = re.sub(r"[,\u2013\u2014]", " ", text or "")
    match = MONTH_PATTERN.search(cleaned)
    if not match:
        return None
    month = datetime.strptime(match.group("month")[:3], "%b").month
    year = int(match.group("year"))
    return date(year, month, 1)


def _parse_holdings_frame(frame: pd.DataFrame, context: ParseContext) -> dict | None:
    if frame is None or frame.empty:
        return None

    raw_rows = frame.where(pd.notna(frame), None).values.tolist()
    if not raw_rows:
        return None

    columns = list(frame.columns)
    parsed_headers = normalize_columns(columns)
    uses_column_headers = "instrument_name" in parsed_headers and "percent_aum" in parsed_headers
    header_row_idx = -1

    if uses_column_headers:
        headers = parsed_headers
        data_rows = raw_rows
    else:
        header_row_idx, headers = _find_header_row(raw_rows)
        if header_row_idx is None:
            return None
        data_rows = raw_rows[header_row_idx + 1 :]

    scheme_name = _extract_scheme_name(columns, raw_rows)
    report_month = context.report_month or _detect_report_month_from_rows(raw_rows)
    holdings, total_percent = _extract_holdings_from_rows(data_rows, headers)
    if not holdings:
        return None

    warnings: list[str] = []
    if report_month is None:
        warnings.append("report_month_not_detected")
    if not scheme_name:
        warnings.append("scheme_name_not_detected")
    if not (90.0 <= total_percent <= 110.0):
        warnings.append("percent_aum_total_out_of_band")

    resolved_scheme = scheme_name or PPFAS_FLEXI_CAP_SCHEME_CANONICAL
    return {
        "scheme_name": resolved_scheme,
        "report_month": report_month,
        "holdings": holdings,
        "metrics": {"total_percent_aum": total_percent},
        "confidence_score": _compute_confidence(holdings, report_month, total_percent, resolved_scheme),
        "warnings": warnings,
        "selection_score": _compute_selection_score(resolved_scheme, len(holdings), total_percent),
        "header_row_idx": header_row_idx,
    }


def _parse_holdings_text(pdf_text: str, context: ParseContext) -> dict | None:
    if not pdf_text:
        return None

    report_month = context.report_month or detect_report_month(pdf_text)
    scheme_name = _extract_scheme_name_from_text(pdf_text) or PPFAS_FLEXI_CAP_SCHEME_CANONICAL
    components: list[dict] = []
    for line in pdf_text.splitlines():
        clean = " ".join(str(line or "").split())
        if not clean:
            continue
        match = re.search(
            r"^(?P<name>.+?)\s+(?P<isin>[A-Z]{2}[A-Z0-9]{9}\d)\s+(?P<pct>-?\d+(?:\.\d+)?%?)$",
            clean,
        )
        if match:
            instrument_name = normalize_instrument_name(match.group("name"))
            if _is_summary_row(instrument_name):
                continue
            percent_aum = _parse_percent(match.group("pct"))
            if percent_aum is None:
                continue
            components.append(
                {
                    "instrument_name": instrument_name,
                    "isin": match.group("isin"),
                    "sector": None,
                    "percent_aum": percent_aum,
                    "market_value": None,
                    "quantity": None,
                }
            )
        else:
            match_no_isin = re.search(
                r"^(?P<name>.+?)\s+(?P<pct>-?\d+(?:\.\d+)?%?)$",
                clean,
            )
            if match_no_isin:
                instrument_name = normalize_instrument_name(match_no_isin.group("name"))
                if _is_summary_row(instrument_name):
                    continue
                low_name = instrument_name.lower()
                cash_keywords = ("cash", "treps", "repo", "receivables", "net current assets", "nca", "clearing corporation", "current assets")
                if any(k in low_name for k in cash_keywords):
                    percent_aum = _parse_percent(match_no_isin.group("pct"))
                    if percent_aum is not None:
                        components.append(
                            {
                                "instrument_name": instrument_name,
                                "isin": None,
                                "sector": None,
                                "percent_aum": percent_aum,
                                "market_value": None,
                                "quantity": None,
                            }
                        )

    if not components:
        return None

    components = _scale_percent_aum_if_necessary(components)
    holdings = [row for row in components if row.get("isin")]
    total_percent = round(sum(float(row.get("percent_aum") or 0.0) for row in components), 6)
    warnings: list[str] = []
    if not (90.0 <= total_percent <= 110.0):
        warnings.append("percent_aum_total_out_of_band")
    if report_month is None:
        warnings.append("report_month_not_detected")

    return {
        "scheme_name": scheme_name,
        "report_month": report_month,
        "holdings": holdings,
        "metrics": {"total_percent_aum": total_percent},
        "confidence_score": _compute_confidence(holdings, report_month, total_percent, scheme_name),
        "warnings": warnings,
        "selection_score": _compute_selection_score(scheme_name, len(holdings), total_percent),
    }


def _find_header_row(rows: list[list[object]]) -> tuple[int | None, list[str]]:
    for idx, row in enumerate(rows[:40]):
        headers = [normalize_column_name(cell) for cell in row]
        if "instrument_name" in headers and "percent_aum" in headers:
            return idx, headers
    return None, []


def _scale_percent_aum_if_necessary(holdings: list[dict]) -> list[dict]:
    raw_total = sum(float(row.get("percent_aum") or 0.0) for row in holdings)
    if 0.0 < raw_total < 2.0:
        for row in holdings:
            if row.get("percent_aum") is not None:
                row["percent_aum"] = round(float(row["percent_aum"]) * 100.0, 6)
    return holdings


def _extract_holdings_from_rows(rows: list[list[object]], headers: list[str]) -> tuple[list[dict], float]:
    components: list[dict] = []
    for row in rows:
        instrument_name = normalize_instrument_name(_get_row_cell(row, headers, "instrument_name"))
        if _is_summary_row(instrument_name):
            continue

        percent_raw = _get_row_cell(row, headers, "percent_aum")
        percent_aum = _parse_percent(percent_raw)
        if percent_aum is None:
            continue

        isin_value = _normalize_isin(_get_row_cell(row, headers, "isin"))
        sector = normalize_instrument_name(_get_row_cell(row, headers, "sector")) or None
        quantity = _parse_number(_get_row_cell(row, headers, "quantity"))
        market_value = _parse_number(_get_row_cell(row, headers, "market_value"))

        components.append(
            {
                "instrument_name": instrument_name,
                "isin": isin_value,
                "sector": sector,
                "percent_aum": percent_aum,
                "quantity": quantity,
                "market_value": market_value,
            }
        )

    deduped: dict[str, dict] = {}
    for row in components:
        name_key = str(row.get("instrument_name") or "").strip().lower()
        isin_key = str(row.get("isin") or "").strip().upper()
        key = f"{name_key}|{isin_key}"
        if not key.strip("|"):
            continue
        existing = deduped.get(key)
        if not existing or float(row.get("percent_aum") or 0.0) > float(existing.get("percent_aum") or 0.0):
            deduped[key] = row

    unique_components = _scale_percent_aum_if_necessary(list(deduped.values()))
    holdings = [row for row in unique_components if row.get("isin")]
    total_percent = round(sum(float(row.get("percent_aum") or 0.0) for row in unique_components), 6)

    return holdings, total_percent


def _get_row_cell(row: list[object], headers: list[str], key: str) -> object:
    for idx, header in enumerate(headers):
        if header != key:
            continue
        if idx >= len(row):
            continue
        value = row[idx]
        if value is None:
            continue
        text = str(value).strip()
        if text:
            return value
    return None


def _extract_scheme_name(columns: list[object], rows: list[list[object]]) -> str:
    search_text_parts = [str(col) for col in columns if str(col).strip() and "Unnamed" not in str(col)]
    for row in rows[:8]:
        for cell in row:
            text = str(cell or "").strip()
            if text:
                search_text_parts.append(text)

    combined = " | ".join(search_text_parts)
    match = SCHEME_PATTERN.search(combined)
    if match:
        return re.sub(r"\s+", " ", match.group(1)).strip()

    for part in search_text_parts:
        if "parag parikh" in part.lower() and "fund" in part.lower():
            cleaned = re.sub(r"\(.*?\)", "", part)
            return re.sub(r"\s+", " ", cleaned).strip(" -")
    return ""


def _extract_scheme_name_from_text(text: str) -> str:
    match = SCHEME_PATTERN.search(text or "")
    if not match:
        return ""
    return re.sub(r"\s+", " ", match.group(1)).strip()


def _detect_report_month_from_rows(rows: list[list[object]]) -> date | None:
    for row in rows[:20]:
        for cell in row:
            parsed = detect_report_month(str(cell or ""))
            if parsed:
                return parsed
    return None


def _parse_percent(value: object) -> float | None:
    parsed = _parse_number(value)
    if parsed is None:
        return None
    return round(parsed, 6)


def _parse_number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "")
    text = text.replace("%", "")
    text = text.replace("₹", "")
    text = text.replace("Rs.", "")
    text = text.replace("Rs", "")
    text = text.replace("INR", "")
    text = text.strip()
    if text in {"-", "--", "na", "n/a", "nan"}:
        return None
    if text.startswith("(") and text.endswith(")"):
        text = f"-{text[1:-1]}"
    try:
        return float(text)
    except ValueError:
        return None


def _normalize_isin(value: object) -> str | None:
    text = str(value or "").strip().upper()
    if not text:
        return None
    if not ISIN_PATTERN.search(text):
        return None
    return text[:12]


def _is_summary_row(instrument_name: str) -> bool:
    low = re.sub(r"\s+", " ", str(instrument_name or "").strip().lower())
    if not low:
        return True
    if len(low) <= 2:
        return True
    return any(marker in low for marker in SUMMARY_ROW_MARKERS)


def _compute_confidence(holdings: list[dict], report_month: date | None, total_percent: float, scheme_name: str) -> float:
    if not holdings:
        return 0.0

    score = 50.0
    score += min(20.0, len(holdings) * 0.5)
    if report_month:
        score += 15.0
    if 90.0 <= total_percent <= 110.0:
        score += 10.0
    if "parag parikh" in (scheme_name or "").lower():
        score += 5.0
    return round(min(score, 99.0), 2)


def _compute_selection_score(scheme_name: str, row_count: int, total_percent: float) -> float:
    score = float(row_count)
    score += _scheme_preference_score(scheme_name)
    if 90.0 <= total_percent <= 110.0:
        score += 20.0
    return score


def _scheme_preference_score(scheme_name: str) -> float:
    if not scheme_name:
        return 0.0
    low = scheme_name.lower()
    if PPFAS_FLEXI_CAP_SCHEME_CANONICAL.lower() in low:
        return 200.0
    if "flexi cap" in low:
        return 120.0
    if "parag parikh" in low:
        return 60.0
    return float(_token_overlap_score(scheme_name, PPFAS_FLEXI_CAP_SCHEME_CANONICAL)) / 2.0


def _token_overlap_score(left: str, right: str) -> float:
    left_tokens = {token for token in re.split(r"[^a-z0-9]+", left.lower()) if token}
    right_tokens = {token for token in re.split(r"[^a-z0-9]+", right.lower()) if token}
    if not left_tokens or not right_tokens:
        return 0.0
    overlap = len(left_tokens & right_tokens)
    union = len(left_tokens | right_tokens)
    return (overlap / union) * 100.0
