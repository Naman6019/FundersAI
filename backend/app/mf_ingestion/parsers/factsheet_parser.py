from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from app.mf_ingestion.parsers.base_parser import ParseContext
from app.mf_ingestion.parsers.pdf_text_parser import PDFTextParser

SCHEME_NAME_PATTERN = re.compile(
    r"(?m)^(?:\((?:Formerly|Erstwhile)[^\n]*\)\s*)?(?P<name>(?:ICICI Prudential|Parag Parikh|HDFC|SBI|Mirae Asset)[^\n]{3,140}?(?:Fund|FOF|ETF))(?:\s*\([^\n]{1,60}\))?\s*$"
)
ANCHORED_SCHEME_PATTERN = re.compile(
    r"(?im)^Name\s+of\s+the\s+Fund\s*\n+\s*(?P<name>(?:ICICI Prudential|Parag Parikh|HDFC|SBI|Mirae Asset)[^\n]{3,160}?(?:Fund|FOF|ETF))(?:\s*\([^\n]{1,80}\))?\s*$"
)
MANAGER_NAME_PATTERN = re.compile(r"\b(?:Mr|Ms|Mrs)\.?\s+[A-Z][A-Za-z' -]{1,80}")


@dataclass
class FactsheetRecord:
    scheme_name: str
    report_month: date | None
    aum: float | None = None
    expense_ratio: float | None = None
    benchmark: str | None = None
    fund_manager: str | None = None
    risk_level: str | None = None
    confidence_score: float = 0.0


class FactsheetParser:
    def __init__(self) -> None:
        self.pdf_text_parser = PDFTextParser()

    def parse(self, file_path: str, context: ParseContext) -> list[FactsheetRecord]:
        text = self.pdf_text_parser.extract_text(file_path)
        return self.parse_text(text=text, report_month=context.report_month)

    def parse_text(self, text: str, report_month: date | None) -> list[FactsheetRecord]:
        cleaned_text = _preprocess_factsheet_text(text)
        has_anchored_sections = bool(ANCHORED_SCHEME_PATTERN.search(cleaned_text or ""))
        sections = _find_scheme_sections(cleaned_text)
        if not sections:
            return []

        risk_by_scheme = _extract_scheme_risk_levels(cleaned_text)
        best_by_scheme: dict[str, tuple[int, FactsheetRecord]] = {}
        for scheme_name, start, end in sections:
            chunk = str(cleaned_text[start:end])

            fields = _extract_fields(chunk)
            mapped_risk_level = risk_by_scheme.get(_scheme_key(scheme_name))
            if mapped_risk_level:
                fields["risk_level"] = mapped_risk_level
            score = _score_fields(fields)
            if score <= 0:
                continue

            record = FactsheetRecord(
                scheme_name=scheme_name,
                report_month=report_month,
                aum=fields.get("aum"),
                expense_ratio=fields.get("expense_ratio"),
                benchmark=fields.get("benchmark"),
                fund_manager=fields.get("fund_manager"),
                risk_level=fields.get("risk_level"),
                confidence_score=float(min(99.0, 60 + (score * 10))),
            )
            current = best_by_scheme.get(scheme_name)
            if not current or score > current[0]:
                best_by_scheme[scheme_name] = (score, record)

        records = [entry[1] for entry in sorted(best_by_scheme.values(), key=lambda value: value[1].scheme_name)]
        for record in records:
            if record.aum is None and not has_anchored_sections:
                record.aum = _extract_aum_from_scheme_occurrences(cleaned_text, record.scheme_name)
            if not record.risk_level:
                record.risk_level = risk_by_scheme.get(_scheme_key(record.scheme_name))
        return records


def _find_scheme_sections(cleaned_text: str) -> list[tuple[str, int, int]]:
    text = cleaned_text or ""
    anchored_matches = list(ANCHORED_SCHEME_PATTERN.finditer(text))
    if anchored_matches:
        return _sections_from_matches(text, anchored_matches, use_anchor_start=True)
    return _sections_from_matches(text, list(SCHEME_NAME_PATTERN.finditer(text)), use_anchor_start=False)


def _sections_from_matches(
    text: str,
    matches: list[re.Match[str]],
    *,
    use_anchor_start: bool,
) -> list[tuple[str, int, int]]:
    sections: list[tuple[str, int, int]] = []
    for index, match in enumerate(matches):
        start = match.start() if use_anchor_start else match.start()
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        end = min(len(text), max(start + 2500, next_start))
        sections.append((_clean_scheme_name(match.group("name")), start, end))
    return sections


def _preprocess_factsheet_text(text: str) -> str:
    if not text:
        return ""
    # Generalized line break fixes for scheme names
    text = re.sub(r"(?i)\n+\s*(Fund|FOF|ETF)\b", r" \1", text)
    text = re.sub(r"(?i)\b(ICICI Prudential|Parag Parikh|HDFC|SBI|Mirae Asset)\s*\n+\s*", r"\1 ", text)
    text = re.sub(r"(?i)\b(Large|Mid|Small|Flexi|Multi|Micro|Value|Focused|Active)\s*\n+\s*Cap\b", r"\1 Cap", text)
    text = re.sub(r"(?i)\b(Equity|Debt|Liquid|Hybrid|Index|Savings)\s*\n+\s*(Fund|FOF|ETF)\b", r"\1 \2", text)
    
    # Clean newlines in scheme names for PPFAS and other split scheme names
    text = re.sub(r"(?i)\bParag\s+Parikh\s*\n+\s*", "Parag Parikh ", text)
    text = re.sub(r"(?i)\bFlexi\s*\n+\s*Cap\b", "Flexi Cap", text)
    text = re.sub(r"(?i)\bTax\s*\n+\s*Saver\b", "Tax Saver", text)
    text = re.sub(r"(?i)\bHybrid\s*\n+\s*Fund\b", "Hybrid Fund", text)
    text = re.sub(r"(?i)\bAsset\s*\n+\s*Allocation\b", "Asset Allocation", text)
    return text


def _clean_scheme_name(raw: str) -> str:
    value = " ".join(str(raw or "").replace("\xa0", " ").split())
    value = re.sub(r"\s+\([^)]{1,40}\)\s*$", "", value)
    return value.strip()


def _extract_fields(chunk: str) -> dict[str, Any]:
    return {
        "aum": _extract_aum(chunk),
        "expense_ratio": _extract_expense_ratio(chunk),
        "benchmark": _extract_benchmark(chunk),
        "fund_manager": _extract_fund_manager(chunk),
        "risk_level": _extract_risk_level(chunk),
    }


def _score_fields(fields: dict[str, Any]) -> int:
    score = 0
    for key in ("aum", "expense_ratio", "benchmark", "fund_manager", "risk_level"):
        if fields.get(key) not in (None, ""):
            score += 1
    return score


RISK_LABELS = (
    "Low to Moderate",
    "Moderately High",
    "Very High",
    "Moderate",
    "High",
    "Low",
)


def _extract_risk_level(chunk: str) -> str | None:
    text = " ".join(str(chunk or "").replace("\xa0", " ").split())
    if not text:
        return None
    patterns = (
        r"(?i)\bRiskometer\s*[:\-]?\s*(Low\s+to\s+Moderate|Moderately\s+High|Very\s+High|Moderate|High|Low)\b",
        r"(?i)\bThe\s+risk\s+of\s+the\s+scheme\s+is\s+(Low\s+to\s+Moderate|Moderately\s+High|Very\s+High|Moderate|High|Low)\b",
        r"(?i)\bprincipal\s+will\s+be\s+at\s+(Low\s+to\s+Moderate|Moderately\s+High|Very\s+High|Moderate|High|Low)\s+risk\b",
        r"(?i)\bprincipal\s+at\s+(Low\s+to\s+Moderate|Moderately\s+High|Very\s+High|Moderate|High|Low)\s+risk\b",
    )
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return _normalize_risk_label(match.group(1))
    return None


def _extract_scheme_risk_levels(text: str) -> dict[str, str]:
    risk_by_scheme: dict[str, str] = {}
    risk_pattern = re.compile(
        r"(?i)\bThe\s+risk\s+of\s+the\s+scheme\s+is\s+"
        r"(Low\s+to\s+Moderate|Moderately\s+High|Very\s+High|Moderate|High|Low)\s+risk\b"
    )
    for risk_match in risk_pattern.finditer(text or ""):
        label = _normalize_risk_label(risk_match.group(1))
        if not label:
            continue

        preceding = text[max(0, risk_match.start() - 900): risk_match.start()]
        scheme_name = _last_scheme_name(preceding)
        if not scheme_name:
            following = text[risk_match.end(): min(len(text), risk_match.end() + 900)]
            scheme_name = _first_scheme_name(following)
        if scheme_name:
            risk_by_scheme[_scheme_key(scheme_name)] = label
    return risk_by_scheme


def _last_scheme_name(text: str) -> str | None:
    matches = list(SCHEME_NAME_PATTERN.finditer(text or ""))
    if not matches:
        return None
    return _clean_scheme_name(matches[-1].group("name"))


def _first_scheme_name(text: str) -> str | None:
    match = SCHEME_NAME_PATTERN.search(text or "")
    if not match:
        return None
    return _clean_scheme_name(match.group("name"))


def _scheme_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").lower())


def _normalize_risk_label(value: str) -> str | None:
    normalized = " ".join(str(value or "").split()).strip().lower()
    for label in RISK_LABELS:
        if normalized == label.lower():
            return label
    return None


def _extract_aum(chunk: str) -> float | None:
    patterns = (
        r"Assets\s+Under\s+Management[\s\S]{0,260}?(?:Rs\.?|`|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:crores?|cr)\b",
        r"Assets\s+Under\s+Management[\s\S]{0,260}?(?:crores?|cr)\s*\n\s*([0-9][0-9,]*(?:\.[0-9]+)?)\b",
        r"Closing\s+AUM[\s\S]{0,120}?:\s*(?:Rs\.?|`|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:crores?|cr)\b",
        r"Monthly\s+AAUM[\s\S]{0,120}?:\s*(?:Rs\.?|`|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:crores?|cr)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, chunk, flags=re.IGNORECASE)
        if not match:
            continue
        value = _parse_number(match.group(1))
        if value is not None:
            return value
    return None


def _extract_aum_from_scheme_occurrences(text: str, scheme_name: str) -> float | None:
    if not text or not scheme_name:
        return None
    pattern = re.compile(re.escape(scheme_name), flags=re.IGNORECASE)
    for match in pattern.finditer(text):
        start = max(0, match.start() - 400)
        end = min(len(text), match.start() + 7000)
        value = _extract_aum(text[start:end])
        if value is not None:
            return value
    return None


def _extract_expense_ratio(chunk: str) -> float | None:
    patterns = (
        r"Direct\s+Plan\s*:\s*(?:\*\s*)?([0-9]+(?:\.[0-9]+)?)\s*%\*?",
        r"Base\s+Expense\s+Ratio[\s\S]{0,220}?Direct(?:\s+Plan)?\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Base\s+Expense\s+Ratio[\s\S]{0,220}?Direct\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Expense\s+Ratio[\s\S]{0,100}?Direct(?:\s+Plan)?\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Expense\s+Ratio[\s\S]{0,200}?Direct[\sA-Za-z()\/-]{0,40}[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"TER[\s\S]{0,160}?Direct(?:\s+Plan)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Direct(?:\s+Plan)?[\s\S]{0,50}?Expense\s+Ratio[\s:=-]*([0-9]+(?:\.[0-9]+)?)\s*%",
    )
    for pattern in patterns:
        match = re.search(pattern, chunk, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            return float(match.group(1))
        except ValueError:
            continue
    # Fallback: look for the nearest percentage around the word "Direct" in expense-ratio-like sections.
    direct_hits = list(re.finditer(r"direct(?:\s+plan)?", chunk, flags=re.IGNORECASE))
    for hit in direct_hits[:6]:
        window = chunk[max(0, hit.start() - 160): min(len(chunk), hit.end() + 220)]
        if not re.search(r"expense\s+ratio|base\s+expense|ter", window, flags=re.IGNORECASE):
            continue
        pct = re.search(r"([0-9]+(?:\.[0-9]+)?)\s*%", window)
        if not pct:
            continue
        try:
            value = float(pct.group(1))
        except ValueError:
            continue
        if 0 < value < 8:
            return value
    return None


def _extract_benchmark(chunk: str) -> str | None:
    patterns = (
        r"AMFI\s+Tier\s+I\s+Benchmark\s+Index\s+([^\n]{3,90})",
        r"AMFI\s+Tier\s+I\s+Benchmark\s+Index\s*\n\s*([^\n]{3,90})",
        r"Benchmark\s*\n\s*([^\n]{3,90})",
        r"\(Benchmark\)\s*\n\s*([^\n]{3,90})",
    )
    for pattern in patterns:
        match = re.search(pattern, chunk, flags=re.IGNORECASE)
        if not match:
            continue
        value = _normalize_benchmark_candidate(match.group(1))
        if not value:
            continue
        if value.lower() in {"scheme", "benchmark"}:
            continue
        if len(value) < 4:
            continue
        if not _is_plausible_benchmark(value):
            continue
        return value
    return None


def _extract_fund_manager(chunk: str) -> str | None:
    block_patterns = (
        r"Name\s+of\s+the\s+Fund\s+Managers?\s*[\s:]*([\s\S]{0,700})",
        r"Fund\s+Managers?\s*:\s*([\s\S]{0,700})",
    )
    for pattern in block_patterns:
        match = re.search(pattern, chunk, flags=re.IGNORECASE)
        if not match:
            continue
        body = match.group(1)
        names = _extract_manager_names(body)
        if names:
            return "; ".join(names)
    return None


def _extract_manager_names(text: str) -> list[str]:
    names: list[str] = []
    for match in MANAGER_NAME_PATTERN.finditer(text or ""):
        name = " ".join(match.group(0).split())
        if name not in names:
            names.append(name)
    return names


def _parse_number(raw: str) -> float | None:
    clean = str(raw or "").replace(",", "").strip()
    if not clean:
        return None
    try:
        return float(clean)
    except ValueError:
        return None


def _is_plausible_benchmark(value: str) -> bool:
    clean = " ".join(str(value or "").split()).strip()
    if not clean:
        return False
    if len(clean) > 70:
        return False
    if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", clean):
        return False
    invalid_phrases = (
        "this product labelling is applicable only to the scheme",
        "investors should consult",
        "riskometer",
        "performance of the scheme",
        "returns",
        "the risk of",
        "notes",
    )
    lowered = clean.lower()
    if any(phrase in lowered for phrase in invalid_phrases):
        return False

    benchmark_tokens = ("TRI", "INDEX", "NIFTY", "BSE", "SENSEX", "CRISIL", "NSE", "S&P", "MSCI", "FTSE")
    if any(token in clean.upper() for token in benchmark_tokens):
        return True

    words = clean.split()
    return len(words) <= 4


def _normalize_benchmark_candidate(raw: str) -> str:
    text = " ".join(str(raw or "").split()).strip(" :;,-")
    if not text:
        return ""
    text = re.sub(r"(?i)^is\s+", "", text).strip()
    text = re.split(r"[.;]", text)[0].strip(" :;,-")
    if not text:
        return ""
    known_index = re.search(
        r"(?i)((?:nifty|bse|sensex|crisil|nse|s&p|msci|ftse)[^.;,\n]{0,60})",
        text,
    )
    if known_index:
        return " ".join(known_index.group(1).split()).strip(" :;,-")
    return text
