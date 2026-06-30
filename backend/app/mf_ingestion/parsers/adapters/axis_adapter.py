import logging
import os
import re
from datetime import date, datetime, timezone
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
AXIS_PORTFOLIO_HEADER = "instrument type/issuer name"
AXIS_PERCENT_RE = re.compile(r"^-?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?%?$")
AXIS_SCHEME_RE = re.compile(
    r"\bAxis\s+[A-Za-z0-9&,'()/:.\- ]{2,140}?(?:Fund|ETF|FoF|FOF|Plan)\b",
    re.IGNORECASE,
)
AXIS_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
AXIS_HOLDING_STOP_MARKERS = {
    "grand total",
    "performance",
    "income distribution",
    "entry & exit load",
    "exit load",
}
AXIS_HOLDING_SKIP_LINES = {
    "instrument type/issuer name",
    "industry",
    "% of nav",
    "portfolio",
    "equity",
    "debt",
    "exchange traded fund",
    "mutual fund units",
    "debt, cash & other current assets",
    "domestic equities",
    "grand total",
}

class AxisAdapter(BaseAMCAdapter):
    amc_code = "AXIS"
    adapter_key = "axis"

    def __init__(self, user_agent: str = "Mozilla/5.0", timeout_seconds: int = 30) -> None:
        self.user_agent = user_agent
        self.timeout_seconds = timeout_seconds

    def discover_documents(self, source: AMCDocumentSource, document_type: str) -> List[DiscoveredDocument]:
        return self.fetch_documents(source, document_type)

    def parse_holdings(self, excel_frames: list, pdf_table_frames: list, pdf_text: str, context: ParseContext) -> ParsedDocument:
        parsed_documents = self.parse_pdf_text_many(pdf_text, context) if pdf_text else []
        if parsed_documents:
            return max(parsed_documents, key=lambda item: len(item.holdings))
        return ParsedDocument(
            scheme_name="",
            report_month=context.report_month,
            holdings=[],
            warnings=["axis_parsing_not_implemented"],
            confidence_score=0.0
        )

    def parse_pdf_file_many(self, file_path: str, context: ParseContext) -> list[ParsedDocument]:
        """Crop-based PDF extraction for Axis two-column factsheet layout.

        Axis factsheets have metadata on the left column and the portfolio table on
        the right column.  pdfplumber's full-page text extraction garbles both columns
        together.  We crop to the right ~55% of each page (where the portfolio table
        lives) to get clean instrument/sector/% rows.

        Page detection: pages that start with an UPPERCASE scheme name (e.g.
        'AXISLARGE CAP FUND') are fund pages.  We skip cover/TOC/disclaimer pages.
        """
        try:
            import pdfplumber
        except ImportError:
            logger.warning("pdfplumber not available; falling back to text-based Axis parsing")
            return []

        by_scheme: dict[str, ParsedDocument] = {}
        AXIS_FUND_PAGE_STOP_WORDS = {
            "i n d e x", "index", "tax reckoner", "how to read", "disclaimer",
            "equity outlook", "debt outlook", "market review",
        }

        try:
            with pdfplumber.open(file_path) as pdf:
                # First pass: find all pages that start a scheme
                scheme_starts: list[tuple[int, str]] = []
                for idx, page in enumerate(pdf.pages):
                    lines = (page.extract_text() or "").splitlines()
                    if not lines:
                        continue
                    for line in lines[:5]:
                        clean = _axis_clean_line(line)
                        normalized = re.sub(r"(?i)^Axis(?=[A-Z])", "Axis ", clean)
                        is_fund_page = (
                            bool(AXIS_SCHEME_RE.match(normalized) or AXIS_SCHEME_RE.match(clean))
                            and clean[:4].isupper()
                            and not re.search(r"\.{3,}|\s\d{1,3}$|%$", clean)
                            and clean.lower() not in AXIS_FUND_PAGE_STOP_WORDS
                        )
                        if is_fund_page:
                            scheme_name = _axis_extract_scheme_name(normalized)
                            if scheme_name:
                                scheme_starts.append((idx, scheme_name))
                                break

                # Second pass: extract holdings from each page block
                for i, (start_idx, scheme_name) in enumerate(scheme_starts):
                    end_idx = scheme_starts[i + 1][0] if i + 1 < len(scheme_starts) else len(pdf.pages)
                    
                    holdings = []
                    report_month = context.report_month
                    for page_idx in range(start_idx, end_idx):
                        page = pdf.pages[page_idx]
                        
                        # Check for page level stop words in full page text
                        page_text = page.extract_text() or ""
                        AXIS_PAGE_STOP_WORDS = {"performance", "sipperformance", "product labelling", "annexure", "expense ratio", "nav", "minimum investment", "fixed", "key highlights", "sip performance", "outlook", "market review"}
                        if page_idx > start_idx and any(stop in page_text.lower() for stop in AXIS_PAGE_STOP_WORDS):
                            continue
                            
                        w = page.width
                        h = page.height
                        
                        page_words = page.extract_words()
                        # Extract words with x0 >= 320 (right column)
                        right_words = [wd for wd in page_words if wd["x0"] >= 320]
                        
                        # Group by top coordinate (tolerance 2.5 points)
                        name_groups_dict = {}
                        sector_groups_dict = {}
                        pct_groups_dict = {}
                        
                        for wd in right_words:
                            x0 = wd["x0"]
                            top = wd["top"]
                            
                            # Determine column
                            if x0 < 435:
                                target_dict = name_groups_dict
                            elif x0 < 502:
                                target_dict = sector_groups_dict
                            else:
                                target_dict = pct_groups_dict
                                
                            found = False
                            for t_val in target_dict:
                                if abs(top - t_val) < 2.5:
                                    target_dict[t_val].append(wd)
                                    found = True
                                    break
                            if not found:
                                target_dict[top] = [wd]
                                
                        # Reconstruct segments sorted by top coordinate
                        name_segments = []
                        for t_val, wds in name_groups_dict.items():
                            wds_sorted = sorted(wds, key=lambda x: x["x0"])
                            name_segments.append((t_val, " ".join(w["text"] for w in wds_sorted)))
                        name_segments.sort(key=lambda x: x[0])
                        
                        sector_segments = []
                        for t_val, wds in sector_groups_dict.items():
                            wds_sorted = sorted(wds, key=lambda x: x["x0"])
                            sector_segments.append((t_val, "".join(w["text"] for w in wds_sorted)))
                        sector_segments.sort(key=lambda x: x[0])
                        
                        pct_segments = []
                        for t_val, wds in pct_groups_dict.items():
                            wds_sorted = sorted(wds, key=lambda x: x["x0"])
                            pct_segments.append((t_val, "".join(w["text"] for w in wds_sorted)))
                        pct_segments.sort(key=lambda x: x[0])
                        
                        # Parse report month from the page lines if possible
                        all_lines = [_axis_clean_line(ln) for ln in page_text.splitlines() if _axis_clean_line(ln)]
                        p_month = _axis_extract_report_month(all_lines)
                        if p_month:
                            report_month = p_month
                            
                        # Filter valid pcts
                        valid_pcts = []
                        for t_val, pct_str in pct_segments:
                            percent = _axis_percent_value(pct_str)
                            if percent is None:
                                match = re.search(r"(?P<pct>-?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?)%?$", pct_str)
                                if match:
                                    percent = _axis_percent_value(match.group("pct"))
                            if percent is not None and 0 < percent <= 100:
                                valid_pcts.append((t_val, percent))
                                
                        valid_pcts.sort(key=lambda x: x[0])
                        
                        # Align name/sector with each valid pct by vertical range
                        for j, (pct_top, percent) in enumerate(valid_pcts):
                            T_start = pct_top - 4.0
                            T_end = valid_pcts[j+1][0] - 4.0 if j + 1 < len(valid_pcts) else h
                            
                            name_parts = [name_str for (t_val, name_str) in name_segments if T_start <= t_val < T_end]
                            name_str = " ".join(name_parts).strip()
                            
                            sector_parts = [sec_str for (t_val, sec_str) in sector_segments if T_start <= t_val < T_end]
                            sector_str = "".join(sector_parts).strip()
                            
                            clean_name = _axis_clean_line(name_str).strip(" -")
                            if clean_name and not _axis_should_skip_holding_line(clean_name):
                                norm_sector = _axis_normalize_sector(sector_str)
                                holdings.append({
                                    "instrument_name": clean_name,
                                    "isin": None,
                                    "sector": norm_sector,
                                    "percent_aum": percent,
                                })
                                
                    holdings = _axis_dedupe_holdings(holdings)
                    if not holdings:
                        continue
                        
                    total_percent = sum(row["percent_aum"] for row in holdings)
                    warnings: list[str] = []
                    if total_percent and not (85.0 <= total_percent <= 115.0):
                        warnings.append("percent_aum_total_out_of_band")
                        
                    parsed = ParsedDocument(
                        scheme_name=scheme_name,
                        report_month=report_month,
                        holdings=holdings,
                        metrics={"total_percent_aum": round(total_percent, 6)},
                        warnings=warnings,
                        confidence_score=90.0,
                    )
                    key = _axis_scheme_key(scheme_name)
                    existing = by_scheme.get(key)
                    if not existing or len(parsed.holdings) > len(existing.holdings):
                        by_scheme[key] = parsed

        except Exception:
            logger.exception("axis:parse_pdf_file_many failed file=%s", file_path)
            return []

        return list(by_scheme.values())

    def parse_pdf_text_many(self, pdf_text: str, context: ParseContext) -> list[ParsedDocument]:
        lines = [_axis_clean_line(line) for line in (pdf_text or "").splitlines()]
        lines = [line for line in lines if line]
        blocks = _axis_portfolio_blocks(lines)
        by_scheme: dict[str, ParsedDocument] = {}

        for start, end in blocks:
            scheme_name = _axis_find_scheme_name(lines, start, end)
            if not scheme_name:
                continue
            block_lines = lines[start:end]
            holdings, total_percent = _axis_extract_holdings(block_lines)
            if not holdings:
                continue
            report_month = _axis_extract_report_month(lines[max(0, start - 40): min(len(lines), end + 20)]) or context.report_month
            warnings: list[str] = []
            if total_percent and not (85.0 <= total_percent <= 115.0):
                warnings.append("percent_aum_total_out_of_band")
            parsed = ParsedDocument(
                scheme_name=scheme_name,
                report_month=report_month,
                holdings=holdings,
                metrics={"total_percent_aum": round(total_percent, 6)},
                warnings=warnings,
                confidence_score=88.0,
            )
            key = _axis_scheme_key(scheme_name)
            existing = by_scheme.get(key)
            if not existing or len(parsed.holdings) > len(existing.holdings):
                by_scheme[key] = parsed

        return list(by_scheme.values())

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

        allow_factsheet_as_portfolio = str(
            os.getenv("MF_ALLOW_FACTSHEET_AS_PORTFOLIO", "")
            or os.getenv("MF_ALLOW_HDFC_FACTSHEET_AS_PORTFOLIO", "")
            or ""
        ).strip().lower() in {"1", "true", "yes", "on"}
        if document_type == "portfolio_disclosure" and allow_factsheet_as_portfolio and not raw:
            raw = str(os.getenv("MF_AXIS_FACTSHEET_DOCUMENT_URLS", "") or "").strip()

        if not raw:
            return []

        listing_url = (
            source.factsheet_page_url if document_type == "factsheet"
            else source.portfolio_disclosure_page_url
        ) or "https://www.axismf.com/cms/latestupdates"

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
            proxy_url = str(os.getenv("MF_HTTP_PROXY", "") or "").strip()
            proxies = None
            if proxy_url:
                proxies = {"http": proxy_url, "https": proxy_url}

            response = requests.get(
                page_url, 
                headers={"User-Agent": self.user_agent}, 
                timeout=self.timeout_seconds,
                proxies=proxies,
                verify=not bool(proxies)
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


def _axis_clean_line(value: object) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\xa0", " ")).strip()


def _axis_scheme_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _axis_portfolio_blocks(lines: list[str]) -> list[tuple[int, int]]:
    """Identify per-fund portfolio blocks from the PDF text.

    Primary: each fund page starts with a line matching AXIS_SCHEME_RE.
    Fallback: legacy AXIS_PORTFOLIO_HEADER line approach.
    """
    scheme_starts: list[int] = []
    for idx, line in enumerate(lines):
        text = _axis_clean_line(line)
        if not text:
            continue
        normalized = re.sub(r"(?i)^Axis(?=[A-Z])", "Axis ", text)
        if (AXIS_SCHEME_RE.match(normalized) or AXIS_SCHEME_RE.match(text)) and text[:4].isupper():
            # Reject TOC lines (dots), page-number-only endings, and inline holdings (% at end)
            if re.search(r"\.{3,}|\s\d{1,3}$|%$", text):
                continue
            scheme_starts.append(idx)
    if scheme_starts:
        blocks: list[tuple[int, int]] = []
        for i, start_idx in enumerate(scheme_starts):
            block_start = start_idx + 1
            block_end = scheme_starts[i + 1] if i + 1 < len(scheme_starts) else len(lines)
            block_lines = lines[block_start:block_end]
            if block_end > block_start and _axis_block_has_portfolio_content(block_lines):
                blocks.append((block_start, block_end))
        if blocks:
            return blocks

    blocks = []
    for index, line in enumerate(lines):
        if AXIS_PORTFOLIO_HEADER not in line.lower():
            continue
        start = index + 1
        while start < len(lines) and lines[start].lower() in {"industry", "% of nav"}:
            start += 1
        end = start
        while end < len(lines):
            low = lines[end].lower()
            if end > start and AXIS_PORTFOLIO_HEADER in low:
                break
            if any(low.startswith(marker) for marker in AXIS_HOLDING_STOP_MARKERS):
                end += 1
                if low.startswith("grand total") and end < len(lines) and _axis_percent_value(lines[end]) is not None:
                    end += 1
                break
            end += 1
        if end > start:
            blocks.append((start, end))
    return blocks


def _axis_find_scheme_name(lines: list[str], start: int, end: int) -> str:
    before = lines[max(0, start - 50):start]
    after = lines[end:min(len(lines), end + 20)]
    for line in reversed(before):
        name = _axis_extract_scheme_name(line)
        if name:
            return name
    for line in after:
        name = _axis_extract_scheme_name(line)
        if name:
            return name
    return ""


def _axis_block_has_portfolio_content(lines: list[str]) -> bool:
    for line in lines:
        low = _axis_clean_line(line).lower()
        if not low:
            continue
        if AXIS_PORTFOLIO_HEADER in low or low.startswith("portfolio snapshot"):
            return True
        if _axis_parse_inline_holding(line):
            return True
    return False


def _axis_extract_scheme_name(line: str) -> str:
    text = _axis_clean_line(line)
    if not text:
        return ""
    normalized = re.sub(r"(?i)^Axis(?=[A-Z])", "Axis ", text)
    match = AXIS_SCHEME_RE.search(normalized) or AXIS_SCHEME_RE.search(text)
    if not match:
        return ""
    name = match.group(0)
    name = re.sub(r"\s*\(.*?\)\s*", " ", name)
    name = re.sub(r"\s+an open.*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\s+fund manager.*$", "", name, flags=re.IGNORECASE)
    name = _axis_clean_line(name).strip(" -")
    if not name or name.lower().startswith("axis mutual fund"):
        return ""
    return _axis_title_scheme_name(name)


def _axis_title_scheme_name(name: str) -> str:
    titled = _axis_clean_line(name).title()
    replacements = {
        "Etf": "ETF",
        "Fof": "FoF",
        "Idcw": "IDCW",
        "Nifty": "Nifty",
        "Bse": "BSE",
    }
    for old, new in replacements.items():
        titled = re.sub(rf"\b{old}\b", new, titled)
    return titled


def _axis_extract_holdings(lines: list[str]) -> tuple[list[dict], float]:
    """Extract holdings from a per-fund block of PDF text lines.

    Axis PDFs use a two-column layout: left=fund stats, right=portfolio table.
    pdfplumber merges both columns into single lines, so each line may contain
    e.g. "BSE 100 TRI Beta ... Reliance Industries Petroleum Products 5.08%".
    We use _axis_parse_inline_holding to regex-extract the "Name Sector X.XX%"
    portion from anywhere in the line, regardless of leading metadata.
    """
    holdings: list[dict] = []
    index = 0
    while index < len(lines):
        line = _axis_clean_line(lines[index])
        low = line.lower()
        if not line:
            index += 1
            continue
        if any(low.startswith(marker) for marker in AXIS_HOLDING_STOP_MARKERS):
            break
        # Try to extract an inline holding from anywhere in the line
        inline = _axis_parse_inline_holding(line)
        if inline:
            holdings.append(inline)
            index += 1
            continue
        fund_unit = _axis_parse_fund_unit_holding(lines, index)
        if fund_unit:
            holding, next_index = fund_unit
            holdings.append(holding)
            index = next_index
            continue
        separated = _axis_parse_separated_holding(lines, index)
        if separated:
            holding, next_index = separated
            holdings.append(holding)
            index = next_index
            continue
        index += 1

    total_percent = sum(float(row.get("percent_aum") or 0.0) for row in holdings)
    return _axis_dedupe_holdings(holdings), total_percent


def _axis_parse_separated_holding(lines: list[str], index: int) -> tuple[dict, int] | None:
    name = _axis_clean_line(lines[index] if index < len(lines) else "")
    if not name or _axis_should_skip_holding_line(name) or _axis_percent_value(name) is not None:
        return None
    if index + 2 >= len(lines):
        return None

    sector = _axis_clean_line(lines[index + 1])
    percent = _axis_percent_value(lines[index + 2])
    if percent is None:
        return None
    if _axis_should_skip_holding_line(sector) or _axis_percent_value(sector) is not None:
        return None

    holding = _axis_build_holding(name=name, sector=sector, percent=percent)
    if not holding:
        return None
    return holding, index + 3


def _axis_parse_fund_unit_holding(lines: list[str], index: int) -> tuple[dict, int] | None:
    name = _axis_clean_line(lines[index] if index < len(lines) else "")
    if not name or _axis_should_skip_holding_line(name) or index + 1 >= len(lines):
        return None
    if not (AXIS_SCHEME_RE.search(name) or re.search(r"\bETF\b", name, flags=re.IGNORECASE)):
        return None
    percent = _axis_percent_value(lines[index + 1])
    if percent is None:
        return None
    holding = _axis_build_holding(name=name, sector="Mutual Fund Units", percent=percent)
    if not holding:
        return None
    return holding, index + 2


def _axis_parse_inline_holding(line: str) -> dict | None:
    """Try to extract a holding from a line that may contain both metadata and portfolio data.

    Returns a holding dict only when we can identify a known SEBI sector in the line,
    which acts as the delimiter between the instrument name and the percentage.
    Lines without a recognised sector are silently skipped to avoid false positives.
    """
    match = re.search(r"(?P<body>.+?)\s+(?P<pct>-?\d{1,3}(?:,\d{2,3})*(?:\.\d+)?)%?$", line)
    if not match:
        return None
    percent = _axis_percent_value(match.group("pct"))
    body = _axis_clean_line(match.group("body"))
    if percent is None or _axis_should_skip_holding_line(body):
        return None
    name, sector = _axis_split_inline_name_sector(body)
    # Only emit if we have a real sector split; otherwise too many false positives
    if not sector:
        return None
    return _axis_build_holding(name=name, sector=sector, percent=percent)


def _axis_split_inline_name_sector(body: str) -> tuple[str, str | None]:
    sector_markers = (
        "Banks",
        "Petroleum Products",
        "IT - Software",
        "IT -Software",
        "Telecom - Services",
        "Telecom -Services",
        "Construction",
        "Automobiles",
        "Finance",
        "Cement & Cement Products",
        "Cement",
        "Healthcare Services",
        "Retailing",
        "Consumer Durables",
        "Pharmaceuticals & Biotechnology",
        "Pharmaceuticals",
        "Biotechnology",
        "Power",
        "Transport Services",
        "Chemicals & Petrochemicals",
        "Chemicals",
        "Petrochemicals",
        "Aerospace & Defence",
        "Aerospace",
        "Defense",
        "Defence",
        "Electrical Equipment",
        "Food Products",
        "Insurance",
        "Capital Markets",
        "Agricultural Food & other Products",
        "Agricultural",
        "Leisure Services",
        "Metals & Mining",
        "Metals",
        "Mining",
        "Realty",
        "Textiles",
        "Gas",
        "Others",
        "Index",
    )
    for marker in sector_markers:
        marker_index = body.lower().rfind(marker.lower())
        if marker_index > 3:
            name = body[:marker_index].strip(" -")
            sector = body[marker_index:].strip(" -")
            if name:
                return name, sector
    return body, None
def _axis_build_holding(name: str, sector: str | None, percent: float | None) -> dict | None:
    clean_name = _axis_clean_line(name).strip(" -")
    if not clean_name or percent is None or _axis_should_skip_holding_line(clean_name):
        return None
    if percent <= 0 or percent > 100:
        return None
    return {
        "instrument_name": clean_name,
        "isin": None,
        "sector": _axis_clean_line(sector) if sector else None,
        "percent_aum": percent,
    }


def _axis_percent_value(line: str) -> float | None:
    text = _axis_clean_line(line).replace(",", "")
    if not AXIS_PERCENT_RE.match(text):
        return None
    try:
        return float(text.rstrip("%"))
    except ValueError:
        return None


def _axis_should_skip_holding_line(line: str) -> bool:
    low = _axis_clean_line(line).lower()
    if not low:
        return True
    if low in AXIS_HOLDING_SKIP_LINES:
        return True
    if any(low.startswith(marker) for marker in AXIS_HOLDING_STOP_MARKERS):
        return True
    if low.startswith("date of ") or low.startswith("benchmark") or low.startswith("fund manager"):
        return True
    if low.startswith("portfolio snapshot") or low.startswith("sector allocation"):
        return True
    return False


def _axis_dedupe_holdings(holdings: list[dict]) -> list[dict]:
    deduped: dict[str, dict] = {}
    for row in holdings:
        key = _axis_scheme_key(str(row.get("instrument_name") or ""))
        if not key:
            continue
        existing = deduped.get(key)
        if not existing or float(row.get("percent_aum") or 0.0) > float(existing.get("percent_aum") or 0.0):
            deduped[key] = row
    return list(deduped.values())


def _axis_extract_report_month(lines: list[str]) -> date | None:
    text = " ".join(lines)
    patterns = (
        r"\bas\s+on\s+\d{1,2}(?:st|nd|rd|th)?\s+(?P<month>[A-Za-z]+),?\s+(?P<year>20\d{2})\b",
        r"\bPortfolio\s+Snapshot\s+(?P<month>[A-Za-z]+)\s*(?P<year>20\d{2})\b",
        r"\b(?P<month>Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t|tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+(?P<year>20\d{2})\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        month_token = match.group("month").lower()
        month = AXIS_MONTHS.get(month_token[:3], AXIS_MONTHS.get(month_token))
        if not month:
            continue
        return date(int(match.group("year")), month, 1)
    return None


def _axis_normalize_sector(sector_str: str) -> str:
    if not sector_str:
        return "Others"
    clean = re.sub(r"[^a-z0-9]", "", sector_str.lower())
    mapping = {
        "banks": "Banks",
        "petroleumproducts": "Petroleum Products",
        "itsoftware": "IT - Software",
        "telecomservices": "Telecom - Services",
        "construction": "Construction",
        "automobiles": "Automobiles",
        "finance": "Finance",
        "cementcementproducts": "Cement & Cement Products",
        "cement": "Cement & Cement Products",
        "healthcareservices": "Healthcare Services",
        "healthcare": "Healthcare Services",
        "retailing": "Retailing",
        "consumerdurables": "Consumer Durables",
        "pharmaceuticalsbiotechnology": "Pharmaceuticals & Biotechnology",
        "pharmaceuticals": "Pharmaceuticals & Biotechnology",
        "biotechnology": "Pharmaceuticals & Biotechnology",
        "pharmabiotechnology": "Pharmaceuticals & Biotechnology",
        "phar": "Pharmaceuticals & Biotechnology",
        "power": "Power",
        "transportservices": "Transport Services",
        "transport": "Transport Services",
        "chemicalspetrochemicals": "Chemicals & Petrochemicals",
        "chemicals": "Chemicals & Petrochemicals",
        "petrochemicals": "Chemicals & Petrochemicals",
        "aerospacedefence": "Aerospace & Defence",
        "aerospace": "Aerospace & Defence",
        "defense": "Aerospace & Defence",
        "defence": "Aerospace & Defence",
        "aerospacedefense": "Aerospace & Defence",
        "electricalequipment": "Electrical Equipment",
        "foodproducts": "Food Products",
        "insurance": "Insurance",
        "capitalmarkets": "Capital Markets",
        "agriculturalfoodotherproducts": "Agricultural Food & other Products",
        "agricultural": "Agricultural Food & other Products",
        "agri": "Agricultural Food & other Products",
        "leisureservices": "Leisure Services",
        "metalsmining": "Metals & Mining",
        "metals": "Metals & Mining",
        "mining": "Metals & Mining",
        "realty": "Realty",
        "textiles": "Textiles",
        "gas": "Gas",
        "diversifiedmetals": "Diversified Metals",
        "nonferrous": "Non-Ferrous",
        "consumablefuels": "Consumable Fuels",
        "industrialproducts": "Industrial Products",
        "beverages": "Beverages",
        "financialservices": "Financial Services",
        "mutualfundunits": "Mutual Fund Units",
        "exchangetradedfunds": "Exchange Traded Funds",
        "governmentbond": "Sovereign",
        "sovereign": "Sovereign",
        "autocomponents": "Auto Components",
        "industrialmanufacturing": "Industrial Manufacturing",
        "itservices": "IT - Services",
        "householdproducts": "Household Products",
        "financialtechnologyfintech": "Financial Technology (Fintech)",
    }
    if clean in mapping:
        return mapping[clean]
    for key, val in mapping.items():
        if key in clean or clean in key:
            return val
    return "Others"
