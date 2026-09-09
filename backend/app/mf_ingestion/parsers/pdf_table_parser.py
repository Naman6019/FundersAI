from __future__ import annotations

import os
import time
from dataclasses import dataclass, field

import pandas as pd
import pdfplumber

# This bound is a guard against a single pathological document, not a routine limit.
#
# The only other protection is `timeout 85m` wrapped around a batch of up to 900
# documents in sync-mf-disclosures.yml; when that fires the AMC is marked failed and
# every unprocessed document in the round is lost. Bounding one document contains the
# damage to that document, which then goes to review with a specific reason.
#
# It must sit clear of any legitimate parse. Pages are scanned in order, so cutting at
# page N drops every scheme on the pages after it -- and the documents that take longest
# are exactly the large multi-scheme ones where that loss costs the most. The slowest
# successful parse measured across R2 was 249.7s (LIC), so a 240s bound would have cut a
# document that was about to finish. There is deliberately no page cap: page count does
# not predict cost (measured 0.1s to 2.8s per page on the same corpus), so a page limit
# would bind on cheap documents while missing expensive ones.
#
# Note this bounds only the pdfplumber table fallback. The path that actually extracts
# many schemes from a large PDF is the text parse in combined_factsheet_portfolio.py,
# which is unbounded and far cheaper -- DSP's 170-page factsheet yields 84 schemes in
# under 4s -- and Excel/ZIP portfolios (ABSL, ICICI) never reach this module at all.
DEFAULT_MAX_SECONDS = 600.0


def _env_float(name: str, default: float) -> float:
    try:
        value = float(str(os.getenv(name, "")).strip())
    except (TypeError, ValueError):
        return default
    return value if value > 0 else default


@dataclass
class TableExtractionResult:
    frames: list[pd.DataFrame] = field(default_factory=list)
    truncated_reason: str | None = None
    pages_scanned: int = 0
    pages_total: int = 0

    @property
    def is_truncated(self) -> bool:
        return self.truncated_reason is not None


class PDFTableParser:
    def __init__(self, *, max_seconds: float | None = None) -> None:
        self.max_seconds = max_seconds if max_seconds and max_seconds > 0 else _env_float(
            "MF_PDF_TABLE_MAX_SECONDS", DEFAULT_MAX_SECONDS
        )

    def extract_tables(
        self,
        file_path: str,
        page_numbers: list[int] | set[int] | None = None,
    ) -> list[pd.DataFrame]:
        return self.extract_tables_with_status(file_path, page_numbers).frames

    def extract_tables_with_status(
        self,
        file_path: str,
        page_numbers: list[int] | set[int] | None = None,
    ) -> TableExtractionResult:
        result = TableExtractionResult()
        selected_pages = {int(page) for page in page_numbers} if page_numbers else None
        started_at = time.monotonic()

        import fitz
        fitz_doc = fitz.open(file_path)

        try:
            with pdfplumber.open(file_path) as pdf:
                result.pages_total = len(pdf.pages)
                for page_index, page in enumerate(pdf.pages):
                    if selected_pages is not None and int(page.page_number) not in selected_pages:
                        continue

                    # Checked before starting a page rather than after, so the budget is
                    # never overshot by more than one page's work.
                    elapsed = time.monotonic() - started_at
                    if elapsed >= self.max_seconds:
                        result.truncated_reason = (
                            f"time_limit_reached:{self.max_seconds:g}s"
                        )
                        break
                    result.pages_scanned += 1

                    fitz_page = fitz_doc[page_index]
                    page_text = fitz_page.get_text("text") or ""
                    page_text_head = "\n".join(page_text.splitlines()[:35])

                    page_words = page.extract_words(x_tolerance=1, y_tolerance=3) or []
                    tables = page.extract_tables() or []
                    if not tables:
                        df = pd.DataFrame()
                        df.attrs["page_number"] = page.page_number
                        df.attrs["page_text_head"] = page_text_head
                        df.attrs["page_text_full"] = page_text
                        df.attrs["page_words"] = page_words
                        result.frames.append(df)
                        continue

                    for table in tables:
                        if not table:
                            continue
                        df_raw = pd.DataFrame(table)
                        if df_raw.empty:
                            continue
                        header = df_raw.iloc[0].tolist()
                        df = df_raw.iloc[1:].copy()
                        df.columns = [str(c) if c is not None else "" for c in header]
                        df = df.dropna(how="all")
                        if not df.empty:
                            df.attrs["page_number"] = page.page_number
                            df.attrs["page_text_head"] = page_text_head
                            df.attrs["page_text_full"] = page_text
                            df.attrs["page_words"] = page_words
                            result.frames.append(df)
        finally:
            fitz_doc.close()

        return result
