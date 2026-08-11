from __future__ import annotations

import re
from typing import Any
import pandas as pd

from app.mf_ingestion.constants import AMC_HSBC
from app.mf_ingestion.normalizers.instrument_normalizer import normalize_instrument_name
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument

HOLDING_LINE_PATTERN = re.compile(
    r"^(?P<name>.+?)(?:\s+(?P<cap>Large Cap|Mid Cap|Small Cap|Unlisted))?\s+(?P<weight>\d+\.\d+)%\s*$",
    re.IGNORECASE
)

SECTOR_HEADER_PATTERN = re.compile(
    r"^(?P<sector>[A-Za-z0-9\s/&,-]+?)(?:\s+\d+\.\d+%\s*)?$"
)

EXCLUDED_HOLDING_KEYWORDS = (
    "nse ", "bse ", "msci", "s&p", "dow jones", "crude oil", "inr - usd",
    "market commentary", "fund positioning", "product suite", "riskometer",
    "suitable for", "index tr", "total net assets", "net current assets"
)


class HSBCAdapter(GenericPortfolioAdapter):
    amc_code = AMC_HSBC
    scheme_markers = ("hsbc ",)

    def parse_pdf_frame_many(self, frame: pd.DataFrame, context: ParseContext) -> list[ParsedDocument]:
        # First try parent generic table parsing
        generic_docs = super().parse_pdf_frame_many(frame, context)
        if generic_docs and any(doc.holdings for doc in generic_docs):
            return generic_docs

        # HSBC specific packed-cell text parsing
        scheme_name = str(frame.attrs.get("page_text_head") or "").strip()
        lines = [l.strip() for l in scheme_name.split("\n") if l.strip()]
        if lines:
            scheme_name = lines[0]
            if len(lines) > 1 and "HSBC" in lines[0]:
                scheme_name = lines[0]

        holdings: list[dict[str, Any]] = []
        current_sector = "Equity"

        # Walk through cells in the frame
        for _, row in frame.iterrows():
            row_str = "\n".join([str(val) for val in row if pd.notna(val) and str(val).strip()])
            for line in row_str.split("\n"):
                line = line.strip()
                line_lower = line.lower()
                if not line or any(kw in line_lower for kw in EXCLUDED_HOLDING_KEYWORDS):
                    continue

                match = HOLDING_LINE_PATTERN.match(line)
                if match:
                    name = match.group("name").strip()
                    try:
                        weight = float(match.group("weight"))
                    except ValueError:
                        continue

                    if "Total" in name or "Net Current" in name or "Risk" in name:
                        continue

                    normalized_name = normalize_instrument_name(name)
                    holdings.append(
                        {
                            "company_name": normalized_name,
                            "instrument_name": normalized_name,
                            "isin": None,
                            "rating": None,
                            "industry_or_rating": current_sector,
                            "sector": current_sector,
                            "quantity": None,
                            "market_value_lakhs": None,
                            "percent_aum": weight,
                            "percentage_to_aum": weight,
                        }
                    )
                else:
                    sec_match = SECTOR_HEADER_PATTERN.match(line)
                    if sec_match:
                        sec_name = sec_match.group("sector").strip()
                        if (
                            sec_name
                            and len(sec_name) > 2
                            and sec_name not in ("Large Cap", "Mid Cap", "Small Cap", "Total Net Assets")
                        ):
                            current_sector = sec_name

        if not holdings:
            return []

        return [
            ParsedDocument(
                scheme_name=scheme_name,
                report_month=context.report_month,
                holdings=holdings,
            )
        ]
