from __future__ import annotations

import re
from math import atan2, degrees
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import fitz
from bs4 import BeautifulSoup

from app.mf_ingestion.parsers.base_parser import ParseContext
from app.mf_ingestion.parsers.pdf_text_parser import PDFTextParser

AMC_SCHEME_PREFIX_PATTERN = (
    r"(?:ICICI Prudential|Parag Parikh|HDFC|SBI|Mirae Asset|Axis|Motilal Oswal|"
    r"Nippon India|UTI(?:\s*-\s*)?|DSP|Kotak|Aditya Birla Sun Life|"
    r"Invesco|Edelweiss|HSBC|Tata|Bandhan)"
)
SCHEME_NAME_PATTERN = re.compile(
    rf"(?im)^(?:\((?:Formerly|Erstwhile)[^\n]*\)\s*)?(?P<name>{AMC_SCHEME_PREFIX_PATTERN}[^\n]{{3,140}}?(?:Fund|FOF|ETF))(?:\s*\([^\n]{{1,60}}\))?(?:\s*[\*\^$#@~§]+)?\s*$"
)
PRODUCT_SUITABILITY_SCHEME_PATTERN = re.compile(
    rf"(?im)^(?P<name>{AMC_SCHEME_PREFIX_PATTERN}[^\n]{{3,140}}?(?:Fund|FOF|ETF))\b[^\n]*$"
)
ANCHORED_SCHEME_PATTERN = re.compile(
    rf"(?im)^Name\s+of\s+the\s+Fund\s*\n+\s*(?P<name>{AMC_SCHEME_PREFIX_PATTERN}[^\n]{{3,160}}?(?:Fund|FOF|ETF))(?:\s*\([^\n]{{1,80}}\))?\s*$"
)
PAGE_NUMBERED_SCHEME_PATTERN = re.compile(
    rf"(?im)^\s*\d{{1,3}}\s*\n+\s*(?P<name>{AMC_SCHEME_PREFIX_PATTERN}[^\n]{{3,160}}?(?:Fund|FOF|ETF))"
    rf"(?:\s*\([^\n]{{1,120}}\)?)?(?:\s*[\*\^$#@~§]+)?\s*$"
)
MANAGER_NAME_PATTERN = re.compile(
    r"\b(?:Mr|Ms|Mrs)\.?[ \t]+[A-Z][A-Za-z.'-]*"
    r"(?:[ \t]+[A-Za-z][A-Za-z.'-]*){1,5}"
)
FACTSHEET_AMC_NAME_PREFIXES: dict[str, tuple[str, ...]] = {
    "hdfc": ("hdfc",),
    "sbi": ("sbi",),
    "icici": ("icici prudential",),
    "axis": ("axis",),
    "ppfas": ("parag parikh",),
    "nippon": ("nippon india",),
    "motilal": ("motilal oswal",),
    "mirae": ("mirae asset",),
    "uti": ("uti ",),
    "dsp": ("dsp ",),
    "kotak": ("kotak ",),
    "absl": ("aditya birla sun life",),
    "invesco": ("invesco",),
    "edelweiss": ("edelweiss",),
    "hsbc": ("hsbc",),
    "tata": ("tata",),
    "bandhan": ("bandhan",),
}
FACTSHEET_AMC_ALIASES = {
    "aditya_birla": "absl",
    "icici_prudential": "icici",
    "nippon_india": "nippon",
    "motilal_oswal": "motilal",
    "mirae_asset": "mirae",
}


@dataclass
class FactsheetRecord:
    scheme_name: str
    report_month: date | None
    aum: float | None = None
    expense_ratio: float | None = None
    benchmark: str | None = None
    fund_manager: str | None = None
    risk_level: str | None = None
    scheme_isin: str | None = None
    confidence_score: float = 0.0


class FactsheetParser:
    def __init__(self) -> None:
        self.pdf_text_parser = PDFTextParser()

    def parse(self, file_path: str, context: ParseContext) -> list[FactsheetRecord]:
        extension = Path(file_path).suffix.lower()
        if extension in {".html", ".htm"}:
            text = _extract_html_text(file_path)
            pages = None
        else:
            pages = self.pdf_text_parser.extract_pages(file_path)
            text = "\n".join(pages)
        records = self.parse_text(text=text, report_month=context.report_month, page_texts=pages)
        if extension == ".pdf":
            uti_records = _extract_uti_pdf_records(file_path, context.report_month)
            if uti_records:
                records_by_scheme = {
                    _scheme_key(record.scheme_name): record
                    for record in records
                }
                for record in uti_records:
                    key = _scheme_key(record.scheme_name)
                    current = records_by_scheme.get(key)
                    records_by_scheme[key] = (
                        _merge_factsheet_records(record, current)
                        if current
                        else record
                    )
                records = sorted(
                    records_by_scheme.values(),
                    key=lambda value: value.scheme_name,
                )
            vector_risks = _extract_vector_riskometer_levels(
                file_path,
                allowed_scheme_names=[record.scheme_name for record in records],
            )
            for record in records:
                vector_risk = vector_risks.get(
                    _scheme_key(record.scheme_name)
                ) or vector_risks.get(_uti_alias_key(record.scheme_name))
                if vector_risk:
                    record.risk_level = vector_risk
                    record.confidence_score = float(min(99.0, 60 + (_record_score(record) * 10)))
        return records

    def detect_report_month(self, file_path: str) -> date | None:
        extension = Path(file_path).suffix.lower()
        if extension in {".html", ".htm"}:
            text = _extract_html_text(file_path)
        else:
            text = self.pdf_text_parser.extract_text(file_path)
        return detect_dominant_factsheet_month(text)

    def parse_text(
        self,
        text: str,
        report_month: date | None,
        page_texts: list[str] | None = None,
    ) -> list[FactsheetRecord]:
        cleaned_text = _preprocess_factsheet_text(text)
        has_anchored_sections = bool(ANCHORED_SCHEME_PATTERN.search(cleaned_text or ""))
        sections = _find_scheme_sections(cleaned_text)
        if not sections:
            return []

        risk_by_scheme = _extract_scheme_risk_levels(cleaned_text)
        if page_texts:
            risk_by_scheme.update(_extract_page_aligned_risk_levels(page_texts))
            risk_by_scheme.update(_extract_product_suitability_risk_levels(page_texts))
        axis_ter_by_scheme = _extract_axis_ter_ratios(cleaned_text)
        axis_manager_by_scheme = _extract_axis_manager_map(cleaned_text)
        best_by_scheme: dict[str, FactsheetRecord] = {}
        for scheme_name, start, end in sections:
            chunk = str(cleaned_text[start:end])

            fields = _extract_fields(chunk)
            scheme_key = _scheme_key(scheme_name)
            mapped_risk_level = risk_by_scheme.get(scheme_key)
            if mapped_risk_level:
                fields["risk_level"] = mapped_risk_level
            mapped_ter = axis_ter_by_scheme.get(scheme_key)
            if mapped_ter is not None:
                fields["expense_ratio"] = mapped_ter
            mapped_manager = axis_manager_by_scheme.get(scheme_key)
            if mapped_manager:
                fields["fund_manager"] = mapped_manager
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
                scheme_isin=_extract_labeled_scheme_isin(chunk),
                confidence_score=float(min(99.0, 60 + (score * 10))),
            )
            current = best_by_scheme.get(scheme_key)
            best_by_scheme[scheme_key] = _merge_factsheet_records(current, record) if current else record

        records = sorted(best_by_scheme.values(), key=lambda value: value.scheme_name)
        page_aligned_expense_ratios = _extract_page_aligned_expense_ratios(
            page_texts or [],
            [record.scheme_name for record in records],
        )
        for record in records:
            if record.aum is None and not has_anchored_sections:
                record.aum = _extract_aum_from_scheme_occurrences(cleaned_text, record.scheme_name)
            if not record.risk_level:
                record.risk_level = risk_by_scheme.get(_scheme_key(record.scheme_name))
            if record.expense_ratio is None:
                record.expense_ratio = page_aligned_expense_ratios.get(_scheme_key(record.scheme_name))
            mapped_ter = axis_ter_by_scheme.get(_scheme_key(record.scheme_name))
            if mapped_ter is not None:
                record.expense_ratio = mapped_ter
            mapped_manager = axis_manager_by_scheme.get(_scheme_key(record.scheme_name))
            if mapped_manager:
                record.fund_manager = mapped_manager
            record.confidence_score = float(min(99.0, 60 + (_record_score(record) * 10)))
        return records


def _extract_uti_pdf_records(
    file_path: str,
    report_month: date | None,
) -> list[FactsheetRecord]:
    records: list[FactsheetRecord] = []
    document_texts: list[str] = []
    with fitz.open(file_path) as document:
        for page in document:
            text = page.get_text("text")
            document_texts.append(text)
            if "Fund Size Monthly Average" not in text:
                continue
            scheme_name = _extract_uti_page_scheme_name(text)
            if not scheme_name:
                continue
            fields = {
                "aum": _extract_pdf_label_numeric_value(page, "Closing AUM"),
                "expense_ratio": _extract_uti_expense_ratio(text),
                "benchmark": _extract_uti_benchmark(text),
                "fund_manager": _extract_uti_managers(text),
                "risk_level": _extract_risk_level(text),
            }
            score = _score_fields(fields)
            if score <= 0:
                continue
            records.append(
                FactsheetRecord(
                    scheme_name=scheme_name,
                    report_month=report_month,
                    aum=fields["aum"],
                    expense_ratio=fields["expense_ratio"],
                    benchmark=fields["benchmark"],
                    fund_manager=fields["fund_manager"],
                    risk_level=fields["risk_level"],
                    confidence_score=float(min(99.0, 60 + (score * 10))),
                )
            )
    ter_by_scheme = _extract_uti_ter_map("\n".join(document_texts))
    for record in records:
        mapped_ter = ter_by_scheme.get(_uti_alias_key(record.scheme_name))
        if mapped_ter is not None:
            record.expense_ratio = mapped_ter
            record.confidence_score = float(
                min(99.0, 60 + (_record_score(record) * 10))
            )
    return records


def _extract_uti_page_scheme_name(page_text: str) -> str | None:
    for raw_line in reversed(str(page_text or "").splitlines()):
        line = _clean_line(raw_line)
        if not line.upper().startswith("UTI ") or "UTI MUTUAL FUND" in line.upper():
            continue
        candidate = re.split(
            r"(?i)\s+\((?:Erstwhile|An\s+open)",
            line,
            maxsplit=1,
        )[0].strip()
        letters = re.sub(r"[^A-Za-z]+", "", candidate)
        if (
            5 <= len(candidate) <= 180
            and (" FUND" in candidate.upper() or candidate.upper().endswith(" ETF"))
            and letters
            and letters == letters.upper()
        ):
            return candidate
    return None


def _extract_pdf_label_numeric_value(page: Any, label: str) -> float | None:
    label_rects = page.search_for(label)
    if not label_rects:
        return None
    label_rect = label_rects[0]
    candidates: list[tuple[float, float]] = []
    for block in page.get_text("dict").get("blocks", []):
        if block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                bbox = span.get("bbox") or ()
                if len(bbox) != 4:
                    continue
                x0, y0, x1, y1 = (float(value) for value in bbox)
                if x0 <= float(label_rect.x1) or x0 > float(label_rect.x1) + 140.0:
                    continue
                if abs(((y0 + y1) / 2.0) - ((float(label_rect.y0) + float(label_rect.y1)) / 2.0)) > 4.0:
                    continue
                value = _parse_number(str(span.get("text") or "").replace("₹", "").replace("`", ""))
                if value is not None and value > 0:
                    candidates.append((x0, value))
    return min(candidates, key=lambda item: item[0])[1] if candidates else None


def _extract_uti_expense_ratio(page_text: str) -> float | None:
    match = re.search(
        r"(?im)^Regular\s*$\s*:?\s*([0-9]+(?:\.[0-9]+)?)\s*"
        r"^Direct\s*$\s*:?\s*([0-9]+(?:\.[0-9]+)?)\b",
        page_text or "",
    )
    if not match:
        match = re.search(
            r"(?i)\bRegular\s*:?\s*([0-9]+(?:\.[0-9]+)?)\s+"
            r"Direct\s*:?\s*([0-9]+(?:\.[0-9]+)?)\b",
            page_text or "",
        )
    if not match:
        return None
    direct_ratio = _parse_number(match.group(2))
    return direct_ratio if _valid_expense_ratio(direct_ratio) else None


def _extract_uti_ter_map(document_text: str) -> dict[str, float]:
    marker = re.search(r"(?i)YTD\s+TER\s+AS\s+ON", document_text or "")
    if not marker:
        return {}
    lines = [
        _clean_line(line)
        for line in document_text[marker.start():].splitlines()
        if _clean_line(line)
    ]
    ratios: dict[str, float] = {}
    index = 0
    while index < len(lines):
        if not re.fullmatch(r"\d{1,3}", lines[index]):
            index += 1
            continue
        name_lines: list[str] = []
        cursor = index + 1
        while cursor < len(lines) and len(name_lines) < 4:
            if re.fullmatch(r"[0-9]+(?:\.[0-9]+)?|-", lines[cursor]):
                break
            if re.fullmatch(r"\d{1,3}", lines[cursor]):
                break
            name_lines.append(lines[cursor])
            cursor += 1
        if (
            not name_lines
            or cursor + 1 >= len(lines)
            or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?", lines[cursor])
            or not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?|-", lines[cursor + 1])
        ):
            index += 1
            continue
        scheme_name = " ".join(name_lines)
        regular_ratio = _parse_number(lines[cursor])
        direct_ratio = _parse_number(lines[cursor + 1])
        selected_ratio = direct_ratio if _valid_expense_ratio(direct_ratio) else regular_ratio
        if scheme_name.upper().startswith("UTI ") and _valid_expense_ratio(selected_ratio):
            ratios[_uti_alias_key(scheme_name)] = float(selected_ratio)
        index = cursor + 2
    return ratios


def _uti_alias_key(value: str) -> str:
    normalized = str(value or "").lower()
    normalized = re.sub(r"\bexchange\s+traded\s+fund\b", "etf", normalized)
    normalized = re.sub(r"\bunit\s+scheme\b", "fund", normalized)
    normalized = re.sub(r"\s+", " ", normalized)
    return _scheme_key(normalized)


def _extract_uti_benchmark(page_text: str) -> str | None:
    text = str(page_text or "")
    labels = re.search(
        r"(?im)^Investment\s+Objective\s*$\s*^Date\s+of\s+inception/allotment\s*$",
        text,
    )
    prefix = text[:labels.start()] if labels else text[:5000]
    manager = re.search(r"(?im)^(?:Mr|Ms|Mrs)\.?\s+", prefix)
    if not manager:
        return None
    before_manager = prefix[:manager.start()]
    dates = list(
        re.finditer(
            r"(?im)^\s*\d{1,2}(?:st|nd|rd|th)?\s+"
            r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
            r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
            r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s*,?\s*\d{4}\s*$",
            before_manager,
        )
    )
    if not dates:
        return None
    candidate = " ".join(
        line.strip()
        for line in before_manager[dates[-1].end():].splitlines()
        if line.strip()
    )
    candidate = _normalize_benchmark_candidate(candidate)
    return candidate if candidate and _is_plausible_benchmark(candidate) else None


def _extract_uti_managers(page_text: str) -> str | None:
    text = str(page_text or "")
    labels = re.search(
        r"(?im)^Investment\s+Objective\s*$\s*^Date\s+of\s+inception/allotment\s*$",
        text,
    )
    prefix = text[:labels.start()] if labels else text[:5000]
    names = _extract_manager_names(prefix)
    return "; ".join(names) if names else None


def filter_factsheet_records_for_amc(
    records: list[FactsheetRecord],
    amc_code: str,
) -> list[FactsheetRecord]:
    normalized_code = str(amc_code or "").strip().lower()
    normalized_code = FACTSHEET_AMC_ALIASES.get(normalized_code, normalized_code)
    prefixes = FACTSHEET_AMC_NAME_PREFIXES.get(normalized_code)
    if not prefixes:
        return []
    kept: list[FactsheetRecord] = []
    for record in records:
        normalized_name = " ".join(
            str(record.scheme_name or "").lower().replace("-", " ").split()
        )
        if any(normalized_name.startswith(prefix) for prefix in prefixes):
            kept.append(record)
    return kept


def _find_scheme_sections(cleaned_text: str) -> list[tuple[str, int, int]]:
    text = cleaned_text or ""
    anchored_matches = list(ANCHORED_SCHEME_PATTERN.finditer(text))
    if anchored_matches:
        return _sections_from_matches(text, anchored_matches, use_anchor_start=True)
    page_numbered_matches = list(PAGE_NUMBERED_SCHEME_PATTERN.finditer(text))
    if len(page_numbered_matches) >= 5:
        page_numbered_sections = _sections_from_matches(
            text,
            page_numbered_matches,
            use_anchor_start=True,
        )
        informative_sections = sum(
            _score_fields(_extract_fields(text[start:end])) >= 2
            for _, start, end in page_numbered_sections
        )
        if page_numbered_sections and informative_sections / len(page_numbered_sections) >= 0.5:
            return page_numbered_sections
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
        end = min(len(text), next_start, start + 12000)
        scheme_name = _clean_scheme_name(match.group("name"))
        if _is_generic_amc_heading(scheme_name):
            continue
        sections.append((scheme_name, start, end))
    return sections


def _preprocess_factsheet_text(text: str) -> str:
    if not text:
        return ""
    # Generalized line break fixes for scheme names
    text = re.sub(
        r"(?i)\n+\s*(Fund|FOF|ETF)(?=\s*(?:\([^)\n]*\))?\s*(?:\n|$))",
        r" \1",
        text,
    )
    text = re.sub(
        rf"(?i)\b({AMC_SCHEME_PREFIX_PATTERN})\s*\n+\s*",
        r"\1 ",
        text,
    )
    text = re.sub(
        rf"(?im)^({AMC_SCHEME_PREFIX_PATTERN}(?![^\n]*\b(?:Fund|FOF|ETF)\b)[^\n]{{3,120}})\n+\s*"
        r"((?:[A-Za-z0-9&+/:.,'-]+\s+){0,5}(?:Fund|FOF|ETF)"
        r"(?:\s*[\*\^$#@~]+)?)\s*$",
        r"\1 \2",
        text,
    )
    text = re.sub(r"(?i)\b(Large|Mid|Small|Flexi|Multi|Micro|Value|Focused|Active)\s*\n+\s*Cap\b", r"\1 Cap", text)
    text = re.sub(r"(?i)\b(Equity|Debt|Liquid|Hybrid|Index|Savings)\s*\n+\s*(Fund|FOF|ETF)\b", r"\1 \2", text)
    
    # Clean newlines in scheme names for PPFAS and other split scheme names
    text = re.sub(r"(?i)\bParag\s+Parikh\s*\n+\s*", "Parag Parikh ", text)
    text = re.sub(r"(?i)\bFlexi\s*\n+\s*Cap\b", "Flexi Cap", text)
    text = re.sub(r"(?i)\bTax\s*\n+\s*Saver\b", "Tax Saver", text)
    text = re.sub(r"(?i)\bHybrid\s*\n+\s*Fund\b", "Hybrid Fund", text)
    text = re.sub(r"(?i)\bAsset\s*\n+\s*Allocation\b", "Asset Allocation", text)
    return text


def detect_dominant_factsheet_month(text: str) -> date | None:
    anchors = re.compile(
        r"(?i)\b(?:fund\s+details|details|closing\s+aum|month\s+end\s+aum|"
        r"fund\s+aum(?:\s*/\s*folio)?|aum|data|total\s+net\s+assets|total\s+value)"
        r"\s+as\s+on\s+([^\n:]{4,36})"
    )
    counts: dict[date, int] = {}
    strong_counts: dict[date, int] = {}
    for match in anchors.finditer(text or ""):
        parsed = _month_from_date_text(match.group(1))
        if parsed:
            counts[parsed] = counts.get(parsed, 0) + 1
            if re.match(r"(?i)\s*(?:total\s+value|total\s+net\s+assets)", match.group(0)):
                strong_counts[parsed] = strong_counts.get(parsed, 0) + 1
    if not counts:
        return None
    dominant, count = max(counts.items(), key=lambda item: (item[1], item[0]))
    total = sum(counts.values())
    if count >= 3 and count / total >= 0.7:
        return dominant
    if strong_counts:
        strong_dominant, strong_count = max(
            strong_counts.items(), key=lambda item: (item[1], item[0])
        )
        if strong_count / sum(strong_counts.values()) >= 0.7:
            return strong_dominant
    return None


_detect_dominant_factsheet_month = detect_dominant_factsheet_month


def _month_from_date_text(value: str) -> date | None:
    text = " ".join(str(value or "").replace(",", " ").split())
    named = re.search(
        r"(?i)\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|"
        r"jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|"
        r"nov(?:ember)?|dec(?:ember)?)\b[\s/-]*(?:\d{1,2}[\s,/-]*)?(\d{2,4})\b",
        text,
    )
    if named:
        month_names = {
            "jan": 1,
            "feb": 2,
            "mar": 3,
            "apr": 4,
            "may": 5,
            "jun": 6,
            "jul": 7,
            "aug": 8,
            "sep": 9,
            "oct": 10,
            "nov": 11,
            "dec": 12,
        }
        year = int(named.group(2))
        if year < 100:
            year += 2000
        return date(year, month_names[named.group(1)[:3].lower()], 1)
    numeric = re.search(r"\b\d{1,2}[/-](\d{1,2})[/-](\d{2,4})\b", text)
    if numeric:
        month = int(numeric.group(1))
        year = int(numeric.group(2))
        if year < 100:
            year += 2000
        if 1 <= month <= 12:
            return date(year, month, 1)
    return None


def _extract_html_text(file_path: str) -> str:
    raw = Path(file_path).read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(raw, "html.parser")
    for node in soup(["script", "style", "noscript"]):
        node.decompose()
    lines = [" ".join(line.split()) for line in soup.get_text("\n").splitlines()]
    return "\n".join(line for line in lines if line)


def _clean_scheme_name(raw: str) -> str:
    value = " ".join(str(raw or "").replace("\xa0", " ").split())
    value = re.sub(r"\s+\([^)]{1,40}\)\s*$", "", value)
    return value.strip()


def _is_generic_amc_heading(value: str) -> bool:
    key = _scheme_key(value)
    return (
        key.endswith("mutualfund")
        or key.endswith("assetmanagementfund")
        or ("investmentmanagers" in key and "fundfacts" in key)
    )


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


def _record_score(record: FactsheetRecord) -> int:
    return _score_fields(
        {
            "aum": record.aum,
            "expense_ratio": record.expense_ratio,
            "benchmark": record.benchmark,
            "fund_manager": record.fund_manager,
            "risk_level": record.risk_level,
        }
    )


def _merge_factsheet_records(existing: FactsheetRecord, incoming: FactsheetRecord) -> FactsheetRecord:
    scheme_name = _preferred_scheme_name(existing.scheme_name, incoming.scheme_name)
    merged = FactsheetRecord(
        scheme_name=scheme_name,
        report_month=existing.report_month or incoming.report_month,
        aum=existing.aum if existing.aum is not None else incoming.aum,
        expense_ratio=existing.expense_ratio if existing.expense_ratio is not None else incoming.expense_ratio,
        benchmark=existing.benchmark or incoming.benchmark,
        fund_manager=_merge_manager_names(existing.fund_manager, incoming.fund_manager),
        risk_level=existing.risk_level or incoming.risk_level,
        scheme_isin=_merge_scheme_isin(existing.scheme_isin, incoming.scheme_isin),
        confidence_score=max(existing.confidence_score, incoming.confidence_score),
    )
    if incoming.expense_ratio is not None and (existing.expense_ratio is None or incoming.confidence_score >= existing.confidence_score):
        merged.expense_ratio = incoming.expense_ratio
    return merged


def _extract_labeled_scheme_isin(chunk: str) -> str | None:
    """Extract only a labelled mutual-fund unit ISIN, never a portfolio security ISIN."""
    for match in re.finditer(
        r"\b(?:scheme\s+)?isin(?:\s+(?:growth|idcw|dividend|payout|reinvestment))?"
        r"\s*(?::|-)\s*(?P<isin>INF[A-Z0-9]{8}\d)\b",
        str(chunk or ""),
        re.IGNORECASE,
    ):
        # PDF text extraction can turn a holding-table column heading such as
        # "Holding ISIN" into an otherwise identical label.
        preceding = str(chunk or "")[max(0, match.start() - 32) : match.start()].lower()
        if re.search(r"(?:holding|security|instrument)\s+$", preceding):
            continue
        return match.group("isin").upper()
    return None


def _merge_scheme_isin(left: str | None, right: str | None) -> str | None:
    if left and right and left != right:
        return None
    return left or right


def _preferred_scheme_name(left: str, right: str) -> str:
    if _is_all_caps_scheme_name(left) and not _is_all_caps_scheme_name(right):
        return right
    if _is_all_caps_scheme_name(right) and not _is_all_caps_scheme_name(left):
        return left
    return left if len(left) >= len(right) else right


def _is_all_caps_scheme_name(value: str) -> bool:
    letters = re.sub(r"[^A-Za-z]+", "", str(value or ""))
    return bool(letters) and letters.upper() == letters


def _merge_manager_names(left: str | None, right: str | None) -> str | None:
    names: list[str] = []
    for value in (left, right):
        for name in str(value or "").split(";"):
            cleaned = " ".join(name.split()).strip()
            if cleaned and cleaned not in names:
                names.append(cleaned)
    return "; ".join(names) if names else None


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


def _extract_page_aligned_risk_levels(page_texts: list[str]) -> dict[str, str]:
    """Map columnar riskometer rows only when page order and counts align exactly."""
    risk_by_scheme: dict[str, str] = {}
    risk_pattern = re.compile(
        r"(?i)\bThe\s+risk\s+of\s+the\s+scheme\s+is\s+"
        r"(Low\s+to\s+Moderate|Moderately\s+High|Very\s+High|Moderate|High|Low)"
        r"(?:\s+risk)?\b"
    )
    for raw_page in page_texts:
        page = _preprocess_factsheet_text(raw_page)
        scheme_names: list[str] = []
        seen: set[str] = set()
        for match in SCHEME_NAME_PATTERN.finditer(page):
            scheme_name = _clean_scheme_name(match.group("name"))
            scheme_key = _scheme_key(scheme_name)
            if not scheme_key or scheme_key in seen or "mutualfund" in scheme_key:
                continue
            seen.add(scheme_key)
            scheme_names.append(scheme_name)

        risk_labels = [
            label
            for match in risk_pattern.finditer(page)
            if (label := _normalize_risk_label(match.group(1)))
        ]
        if not risk_labels or len(scheme_names) != len(risk_labels) or len(scheme_names) > 8:
            continue
        for scheme_name, risk_label in zip(scheme_names, risk_labels):
            risk_by_scheme[_scheme_key(scheme_name)] = risk_label
    return risk_by_scheme


def _extract_page_aligned_expense_ratios(
    page_texts: list[str],
    allowed_scheme_names: list[str] | None = None,
) -> dict[str, float]:
    """Recover TER values when a factsheet puts the metric before its scheme title."""
    expense_by_scheme: dict[str, float] = {}
    for raw_page in page_texts:
        page = _preprocess_factsheet_text(raw_page)
        markers = list(
            re.finditer(
                r"(?i)(?:expense\s+ratios?|ber\s*/\s*ter|total\s+expense\s+ratio)",
                page,
            )
        )
        if not markers:
            continue
        value = _extract_expense_ratio(page)
        if value is None:
            continue
        scheme_matches = list(SCHEME_NAME_PATTERN.finditer(page))
        known_matches: list[tuple[int, str]] = [
            (match.start(), _clean_scheme_name(match.group("name")))
            for match in scheme_matches
        ]
        for scheme_name in allowed_scheme_names or []:
            normalized_name = " ".join(str(scheme_name or "").split())
            if not normalized_name:
                continue
            name_pattern = re.escape(normalized_name).replace(r"\ ", r"\s+")
            match = re.search(name_pattern, page, flags=re.IGNORECASE)
            if match:
                known_matches.append((match.start(), normalized_name))
        if known_matches:
            known_matches = list(dict.fromkeys(known_matches))
        if not scheme_matches:
            if not known_matches:
                continue
        for marker in markers:
            following = [match for match in known_matches if match[0] >= marker.end()]
            selected = min(
                following or known_matches,
                key=lambda match: abs(match[0] - marker.end()),
            )
            scheme_key = _scheme_key(selected[1])
            if scheme_key and scheme_key not in expense_by_scheme:
                expense_by_scheme[scheme_key] = value
    return expense_by_scheme


def _extract_product_suitability_risk_levels(page_texts: list[str]) -> dict[str, str]:
    """Map each product-suitability scheme to its own textual risk label."""
    risk_by_scheme: dict[str, str] = {}
    risk_pattern = re.compile(
        r"(?i)\bThe\s+risk\s+of\s+the\s+scheme\s+is\s+"
        r"(Low\s+to\s+Moderate|Moderately\s+High|Very\s+High|Moderate|High|Low)"
        r"(?:\s+risk)?\b"
    )
    for raw_page in page_texts:
        page = _preprocess_factsheet_text(raw_page)
        lower_page = page.lower()
        if "name of the scheme" not in lower_page or "scheme riskometer" not in lower_page:
            continue
        matches = list(PRODUCT_SUITABILITY_SCHEME_PATTERN.finditer(page))
        for index, match in enumerate(matches):
            section_end = matches[index + 1].start() if index + 1 < len(matches) else len(page)
            risk_match = risk_pattern.search(page, match.end(), section_end)
            if not risk_match:
                continue
            scheme_name = _clean_scheme_name(match.group("name"))
            label = _normalize_risk_label(risk_match.group(1))
            if scheme_name and label:
                risk_by_scheme[_scheme_key(scheme_name)] = label
    return risk_by_scheme


def _extract_vector_riskometer_levels(
    file_path: str,
    diagnostics: list[dict[str, Any]] | None = None,
    allowed_scheme_names: list[str] | None = None,
) -> dict[str, str]:
    """Read vector needles from official riskometer tables; abstain on any row-count mismatch."""
    risk_by_scheme: dict[str, str] = {}
    document_texts: list[str] = []
    all_needles: list[str] = []
    with fitz.open(file_path) as document:
        for page in document:
            raw_text = page.get_text("text")
            document_texts.append(raw_text)
            risk_by_scheme.update(
                _extract_axis_page_vector_riskometer_levels(
                    page_text=raw_text,
                    drawings=page.get_drawings(),
                    text_blocks=page.get_text("blocks"),
                    page_width=float(page.rect.width),
                    page_height=float(page.rect.height),
                    product_header_rects=page.search_for("Product Riskometer"),
                )
            )
            risk_by_scheme.update(
                _extract_absl_page_vector_riskometer_level(
                    page_text=raw_text,
                    drawings=page.get_drawings(),
                    header_rects=page.search_for("Risk-o-meter"),
                )
            )
            if "ALL PRODUCT LABELLING DISCLOSURES" in raw_text.upper():
                uti_risks = _uti_vector_riskometer_rows(
                    page.get_drawings(),
                    page.get_text("blocks"),
                    page.search_for("Riskometer"),
                )
                for scheme_name, label in uti_risks.items():
                    risk_by_scheme[_scheme_key(scheme_name)] = label
                    risk_by_scheme[_uti_alias_key(scheme_name)] = label
            single_scheme_risk = _single_scheme_vector_risk_level(
                raw_text,
                page.get_drawings(),
                [
                    *page.search_for("Scheme Riskometer"),
                    *page.search_for("Fund Riskometer"),
                ],
            )
            if single_scheme_risk:
                scheme_name, risk_label = single_scheme_risk
                risk_by_scheme[_scheme_key(scheme_name)] = risk_label
            upper_text = raw_text.upper()
            if (
                "RISKOMETER OF SCHEME" not in upper_text
                and "BENCHMARK AND SCHEME RISKOMETERS" not in upper_text
            ):
                continue
            page_text = _preprocess_factsheet_text(raw_text)
            scheme_names: list[str] = []
            seen: set[str] = set()
            for match in SCHEME_NAME_PATTERN.finditer(page_text):
                scheme_name = _clean_scheme_name(match.group("name"))
                scheme_key = _scheme_key(scheme_name)
                if not scheme_key or scheme_key in seen or _is_generic_amc_heading(scheme_name):
                    continue
                seen.add(scheme_key)
                scheme_names.append(scheme_name)

            drawings = page.get_drawings()
            table_headers = sorted(
                (
                    rect
                    for rect in page.search_for("Scheme Riskometer")
                    if float(rect.y0) > 50.0
                ),
                key=lambda rect: float(rect.y0),
            )
            needle_rows: list[tuple[float, str]] = []
            for header_index, table_header in enumerate(table_headers):
                section_bottom = (
                    float(table_headers[header_index + 1].y0)
                    if header_index + 1 < len(table_headers)
                    else float(page.rect.height)
                )
                scheme_column = _riskometer_scheme_column(drawings, table_header)
                needle_rows.extend(
                    _vector_riskometer_needles(
                        drawings,
                        float(page.rect.width),
                        scheme_column=scheme_column,
                        row_range=(float(table_header.y1), section_bottom),
                    )
                )
            if not table_headers:
                needle_rows = _vector_riskometer_needles(
                    drawings,
                    float(page.rect.width),
                )
            needle_rows = sorted(set(needle_rows))
            needles = [label for _, label in needle_rows]
            all_needles.extend(needles)
            row_scheme_names = _riskometer_row_scheme_names(
                page.get_text("blocks"),
                needle_rows,
                page_height=float(page.rect.height),
            )
            if len(row_scheme_names) == len(needles):
                risk_by_scheme.update(
                    {
                        _scheme_key(scheme_name): label
                        for scheme_name, label in zip(row_scheme_names, needles)
                    }
                )
            if diagnostics is not None:
                diagnostics.append(
                    {
                        "page_number": page.number + 1,
                        "scheme_count": len(scheme_names),
                        "needle_count": len(needles),
                        "schemes": scheme_names,
                        "row_schemes": row_scheme_names,
                        "labels": needles,
                    }
                )
            if not scheme_names or len(scheme_names) != len(needles):
                continue
            for scheme_name, label in zip(scheme_names, needles):
                risk_by_scheme[_scheme_key(scheme_name)] = label

    allowed_by_key = {
        _scheme_key(name): name
        for name in (allowed_scheme_names or [])
        if _scheme_key(name)
    }
    if allowed_by_key and all_needles:
        ordered_names: list[str] = []
        seen: set[str] = set()
        document_text = _preprocess_factsheet_text("\n".join(document_texts))
        for match in SCHEME_NAME_PATTERN.finditer(document_text):
            key = _scheme_key(_clean_scheme_name(match.group("name")))
            if key in allowed_by_key and key not in seen:
                seen.add(key)
                ordered_names.append(allowed_by_key[key])
        ordered_mapping = _map_document_order_risk_labels(
            ordered_names,
            all_needles,
            expected_scheme_count=len(allowed_by_key),
        )
        risk_by_scheme.update(ordered_mapping)
        if diagnostics is not None:
            diagnostics.append(
                {
                    "scope": "document_order_fallback",
                    "allowed_scheme_count": len(allowed_by_key),
                    "ordered_scheme_count": len(ordered_names),
                    "needle_count": len(all_needles),
                    "applied": bool(ordered_mapping),
                }
            )
    return risk_by_scheme


def _uti_vector_riskometer_rows(
    drawings: list[dict[str, Any]],
    text_blocks: list[tuple[Any, ...]],
    header_rects: list[Any],
) -> dict[str, str]:
    if not header_rects:
        return {}
    scheme_header = min(header_rects, key=lambda rect: float(rect.x0))
    scheme_column = _riskometer_scheme_column(drawings, scheme_header)
    if not scheme_column:
        return {}
    column_left, column_right = scheme_column
    column_center = (column_left + column_right) / 2.0
    needle_rows: list[tuple[float, str]] = []
    for drawing in drawings:
        fill = drawing.get("fill")
        rect = drawing.get("rect")
        items = drawing.get("items") or []
        if (
            not fill
            or max(float(value) for value in fill) >= 0.2
            or rect is None
            or not (column_left <= float(rect.x0) and float(rect.x1) <= column_right)
            or not (5.0 <= float(rect.width) <= 35.0)
            or not (3.0 <= float(rect.height) <= 25.0)
            or float(rect.width) * float(rect.height) <= 50.0
            or not (5 <= len(items) <= 20)
        ):
            continue
        points = [point for item in items for point in item[1:] if hasattr(point, "x")]
        if not points:
            continue
        pivot_y = float(rect.y1)
        tip = max(
            points,
            key=lambda point: (
                ((float(point.x) - column_center) ** 2)
                + ((float(point.y) - pivot_y) ** 2)
            ),
        )
        angle = degrees(
            atan2(
                pivot_y - float(tip.y),
                float(tip.x) - column_center,
            )
        )
        label = _risk_label_from_needle_angle(angle)
        if label:
            needle_rows.append((float(rect.y0), label))
    needle_rows.sort()
    scheme_names = _uti_riskometer_row_scheme_names(text_blocks, needle_rows)
    if len(scheme_names) != len(needle_rows):
        return {}
    return dict(zip(scheme_names, (label for _, label in needle_rows)))


def _uti_riskometer_row_scheme_names(
    text_blocks: list[tuple[Any, ...]],
    needle_rows: list[tuple[float, str]],
) -> list[str]:
    title_pattern = re.compile(
        r"(?i)^(?P<name>UTI\s+.{2,180}?"
        r"(?:ETF\s+Fund\s+of\s+Fund|Fund\s+of\s+Fund|FOF|ETF|Fund))\b"
    )
    title_rows: list[tuple[int, float, str]] = []
    for block_index, block in enumerate(text_blocks):
        if len(block) < 5 or not (10.0 <= float(block[0]) <= 60.0):
            continue
        match = title_pattern.search(" ".join(str(block[4] or "").split()))
        if match:
            title_rows.append(
                (
                    block_index,
                    float(block[1]),
                    _clean_scheme_name(match.group("name")),
                )
            )
    names: list[str] = []
    used: set[int] = set()
    for row_y, _ in needle_rows:
        candidates = [
            row
            for row in title_rows
            if row[0] not in used
            and row[1] <= row_y + 8.0
            and row_y - row[1] <= 90.0
        ]
        if not candidates:
            return []
        block_index, _, scheme_name = max(candidates, key=lambda row: row[1])
        used.add(block_index)
        names.append(scheme_name)
    return names


def _single_scheme_vector_risk_level(
    page_text: str,
    drawings: list[dict[str, Any]],
    header_rects: list[Any],
) -> tuple[str, str] | None:
    scheme_name = _product_label_scheme_name(page_text) or _last_scheme_name(
        _preprocess_factsheet_text(page_text)
    )
    if not scheme_name or not header_rects:
        return None
    labels: set[str] = set()
    for header_rect in header_rects:
        header_center = (float(header_rect.x0) + float(header_rect.x1)) / 2.0
        for drawing in drawings:
            fill = drawing.get("fill")
            rect = drawing.get("rect")
            items = drawing.get("items") or []
            if (
                not fill
                or max(float(value) for value in fill) >= 0.2
                or rect is None
                or len(items) != 3
                or any(item[0] != "l" for item in items)
                or not (5.0 <= float(rect.width) <= 30.0)
                or not (2.0 <= float(rect.height) <= 20.0)
                or abs(((float(rect.x0) + float(rect.x1)) / 2.0) - header_center) > 25.0
                or not (
                    float(header_rect.y1)
                    < float(rect.y0)
                    <= float(header_rect.y1) + 100.0
                )
            ):
                continue
            points = [point for item in items for point in item[1:] if hasattr(point, "x")]
            if not points:
                continue
            pivot_x = header_center
            pivot_y = float(rect.y1)
            tip = max(
                points,
                key=lambda point: (
                    ((float(point.x) - pivot_x) ** 2)
                    + ((float(point.y) - pivot_y) ** 2)
                ),
            )
            angle = degrees(atan2(pivot_y - float(tip.y), float(tip.x) - pivot_x))
            label = _risk_label_from_needle_angle(angle)
            if label:
                labels.add(label)
    if len(labels) != 1:
        return None
    return scheme_name, next(iter(labels))


def _extract_axis_page_vector_riskometer_levels(
    *,
    page_text: str,
    drawings: list[dict[str, Any]],
    text_blocks: list[tuple[Any, ...]],
    page_width: float,
    page_height: float,
    product_header_rects: list[Any],
) -> dict[str, str]:
    upper_text = str(page_text or "").upper()
    if "AXIS" not in upper_text:
        return {}
    needles = _axis_vector_riskometer_needles(drawings)
    if not needles:
        return {}

    # Debt pages use a row table with Product and Benchmark riskometer columns.
    if product_header_rects:
        product_rows = sorted(
            {
                (row_y, label)
                for pivot_x, row_y, label in needles
                if any(
                    float(header.x0) - 20.0 <= pivot_x <= float(header.x1) + 20.0
                    for header in product_header_rects
                )
            }
        )
        scheme_names = _riskometer_row_scheme_names(
            text_blocks,
            product_rows,
            page_height=page_height,
        )
        if len(scheme_names) != len(product_rows):
            return {}
        return {
            _scheme_key(scheme_name): label
            for scheme_name, (_, label) in zip(scheme_names, product_rows)
        }

    if "PRODUCT LABELLING" not in upper_text:
        return {}

    # Equity/hybrid pages place two cards per row. Each card has an exact "Fund"
    # label above the scheme needle and a separate benchmark needle.
    scheme_blocks: list[tuple[float, float, float, str]] = []
    fund_headers: list[tuple[float, float, float, float]] = []
    for block in text_blocks:
        if len(block) < 5:
            continue
        block_text = " ".join(str(block[4] or "").split())
        if block_text.lower() == "fund":
            fund_headers.append(
                tuple(float(value) for value in block[:4])
            )
            continue
        scheme_name = _first_scheme_name(_preprocess_factsheet_text(str(block[4] or "")))
        if scheme_name and scheme_name.lower().startswith("axis "):
            scheme_blocks.append(
                (float(block[0]), float(block[1]), float(block[3]), scheme_name)
            )

    risk_by_scheme: dict[str, str] = {}
    for x0, _, scheme_bottom, scheme_name in scheme_blocks:
        is_left_column = x0 < page_width / 2.0
        next_scheme_y = min(
            (
                other_y
                for other_x, other_y, _, _ in scheme_blocks
                if (other_x < page_width / 2.0) == is_left_column
                and other_y > scheme_bottom
            ),
            default=page_height,
        )
        headers = [
            header
            for header in fund_headers
            if (header[0] < page_width / 2.0) == is_left_column
            and header[1] >= scheme_bottom - 2.0
            and header[1] < next_scheme_y
        ]
        candidate_needles = [
            (pivot_x, label)
            for pivot_x, row_y, label in needles
            if (pivot_x < page_width / 2.0) == is_left_column
            and row_y > scheme_bottom
            and row_y < next_scheme_y
        ]
        if len(headers) == 1:
            header = headers[0]
            header_center = (header[0] + header[2]) / 2.0
            candidate_needles = [
                candidate
                for candidate in candidate_needles
                if abs(candidate[0] - header_center) <= 25.0
            ]
        elif len(candidate_needles) == 2:
            # The card's scheme riskometer is left of its benchmark riskometer.
            candidate_needles = [min(candidate_needles, key=lambda value: value[0])]
        if len(candidate_needles) == 1:
            risk_by_scheme[_scheme_key(scheme_name)] = candidate_needles[0][1]
    return risk_by_scheme


def _axis_vector_riskometer_needles(
    drawings: list[dict[str, Any]],
) -> list[tuple[float, float, str]]:
    needles: list[tuple[float, float, str]] = []
    for drawing in drawings:
        fill = drawing.get("fill")
        rect = drawing.get("rect")
        items = drawing.get("items") or []
        if (
            not fill
            or rect is None
            or max(float(value) for value in fill) >= 0.2
            or len(items) != 7
            or any(item[0] != "l" for item in items)
            or not (5.0 <= float(rect.width) <= 30.0)
            or not (2.0 <= float(rect.height) <= 15.0)
        ):
            continue

        baselines = []
        for baseline in drawings:
            baseline_fill = baseline.get("fill")
            baseline_rect = baseline.get("rect")
            if (
                not baseline_fill
                or baseline_rect is None
                or max(float(value) for value in baseline_fill) >= 0.2
                or not (40.0 <= float(baseline_rect.width) <= 70.0)
                or not (1.0 <= float(baseline_rect.height) <= 8.0)
                or abs(float(baseline_rect.y0) - float(rect.y1)) > 8.0
                or float(rect.x0) < float(baseline_rect.x0) - 2.0
                or float(rect.x1) > float(baseline_rect.x1) + 2.0
            ):
                continue
            baselines.append(baseline_rect)
        if not baselines:
            continue

        baseline_rect = min(
            baselines,
            key=lambda value: abs(float(value.y0) - float(rect.y1)),
        )
        pivot_x = (float(baseline_rect.x0) + float(baseline_rect.x1)) / 2.0
        pivot_y = float(rect.y1)
        points = [
            point
            for item in items
            for point in item[1:]
            if hasattr(point, "x")
        ]
        if not points:
            continue
        tip = max(
            points,
            key=lambda point: (
                ((float(point.x) - pivot_x) ** 2)
                + ((float(point.y) - pivot_y) ** 2)
            ),
        )
        angle = degrees(
            atan2(
                pivot_y - float(tip.y),
                float(tip.x) - pivot_x,
            )
        )
        label = _risk_label_from_needle_angle(angle)
        if label:
            needles.append((pivot_x, float(rect.y0), label))
    return sorted(set(needles), key=lambda value: (value[1], value[0]))


def _extract_absl_page_vector_riskometer_level(
    *,
    page_text: str,
    drawings: list[dict[str, Any]],
    header_rects: list[Any],
) -> dict[str, str]:
    if "ADITYA BIRLA SUN LIFE" not in str(page_text or "").upper() or not header_rects:
        return {}
    # The left riskometer is the scheme; the right one is the benchmark.
    scheme_header = min(header_rects, key=lambda rect: float(rect.x0))
    result = _single_scheme_vector_risk_level(
        page_text,
        drawings,
        [scheme_header],
    )
    if not result:
        return {}
    scheme_name, risk_level = result
    if not scheme_name.lower().startswith("aditya birla sun life "):
        return {}
    return {_scheme_key(scheme_name): risk_level}


def _product_label_scheme_name(page_text: str) -> str | None:
    text = str(page_text or "")
    marker = re.search(r"(?i)This\s+product\s+is\s+suitable", text)
    if not marker:
        return None
    product_section = text[marker.start():]
    product_section = re.sub(
        r"(?i)\bFund\s*\n+\s*of\s*\n+\s*Fund\b",
        "Fund of Fund",
        product_section,
    )
    pattern = re.compile(
        rf"(?i)\b(?P<name>{AMC_SCHEME_PREFIX_PATTERN}[^\n]{{3,180}}?"
        rf"(?:ETF\s+Fund\s+of\s+Fund|Fund\s+of\s+Fund|FOF|ETF|Fund))\b"
    )
    match = pattern.search(product_section)
    return _clean_scheme_name(match.group("name")) if match else None


def _map_document_order_risk_labels(
    ordered_scheme_names: list[str],
    labels: list[str],
    *,
    expected_scheme_count: int,
) -> dict[str, str]:
    if not ordered_scheme_names or len(ordered_scheme_names) != len(labels) or len(labels) != expected_scheme_count:
        return {}
    return {
        _scheme_key(scheme_name): label
        for scheme_name, label in zip(ordered_scheme_names, labels)
    }


def _vector_riskometer_needles(
    drawings: list[dict[str, Any]],
    page_width: float,
    *,
    scheme_column: tuple[float, float] | None = None,
    row_range: tuple[float, float] | None = None,
) -> list[tuple[float, str]]:
    column_left, column_right = scheme_column or (page_width * 0.43, page_width * 0.64)
    column_center = (column_left + column_right) / 2.0
    needles: list[tuple[float, str]] = []
    for drawing in drawings:
        fill = drawing.get("fill")
        rect = drawing.get("rect")
        items = drawing.get("items") or []
        if (
            not fill
            or max(float(value) for value in fill) >= 0.03
            or rect is None
            or not (column_left <= rect.x0 and rect.x1 <= column_right)
            or (
                row_range is not None
                and not (row_range[0] <= float(rect.y0) < row_range[1])
            )
            or not (5.0 <= rect.width <= 55.0 and 5.0 <= rect.height <= 30.0)
            or len(items) != 7
            or any(item[0] != "l" for item in items)
        ):
            continue
        points = [point for item in items for point in item[1:] if hasattr(point, "x")]
        if not points:
            continue
        pivot_x = column_center
        pivot_y = float(rect.y1)
        tip = max(
            points,
            key=lambda point: ((float(point.x) - pivot_x) ** 2) + ((float(point.y) - pivot_y) ** 2),
        )
        angle = degrees(atan2(pivot_y - float(tip.y), float(tip.x) - pivot_x))
        label = _risk_label_from_needle_angle(angle)
        if label:
            needles.append((float(rect.y0), label))
    return sorted(needles)


def _riskometer_scheme_column(
    drawings: list[dict[str, Any]],
    header_rect: Any | None,
) -> tuple[float, float] | None:
    if header_rect is None:
        return None
    header_center = (float(header_rect.x0) + float(header_rect.x1)) / 2.0
    vertical_x: set[float] = set()
    for drawing in drawings:
        rect = drawing.get("rect")
        if rect is None or float(rect.width) > 1.5 or float(rect.height) < 30.0:
            continue
        if not (
            float(header_rect.y1) <= float(rect.y0) <= float(header_rect.y1) + 80.0
        ):
            continue
        vertical_x.add(round(float(rect.x0), 2))
    left = [value for value in vertical_x if value < header_center]
    right = [value for value in vertical_x if value > header_center]
    if not left or not right:
        return None
    column_left = max(left)
    column_right = min(right)
    if column_right - column_left < 40.0:
        return None
    return column_left, column_right


def _riskometer_row_scheme_names(
    text_blocks: list[tuple[Any, ...]],
    needle_rows: list[tuple[float, str]],
    *,
    page_height: float,
) -> list[str]:
    if not needle_rows:
        return []
    del page_height  # Kept in the signature for compatibility with callers.
    title_pattern = re.compile(
        rf"(?i)^(?:\d{{1,3}}\s+)?(?P<name>{AMC_SCHEME_PREFIX_PATTERN}\s+.{{3,180}}?"
        rf"(?:Fund\s*-\s*[A-Za-z ]+Plan|ETF\s+Fund\s+of\s+Fund|"
        rf"Fund\s+of\s+Fund|FOF|ETF|Fund|"
        rf"Tax\s+Saver(?!\s+Fund)|Plan))\b"
    )
    title_rows: list[tuple[int, float, str]] = []
    for block_index, block in enumerate(text_blocks):
        if len(block) < 5 or not (20.0 <= float(block[0]) <= 130.0):
            continue
        match = title_pattern.search(" ".join(str(block[4] or "").split()))
        if match:
            title_rows.append(
                (block_index, float(block[1]), _clean_scheme_name(match.group("name")))
            )

    names: list[str] = []
    used_block_indexes: set[int] = set()
    for row_y, _ in needle_rows:
        candidates = [
            candidate
            for candidate in title_rows
            if candidate[0] not in used_block_indexes
            and candidate[1] <= row_y + 5.0
            and row_y - candidate[1] <= 140.0
        ]
        if not candidates:
            return []
        block_index, _, scheme_name = max(candidates, key=lambda candidate: candidate[1])
        used_block_indexes.add(block_index)
        names.append(scheme_name)
    return names


def _risk_label_from_needle_angle(angle: float) -> str | None:
    if not 0.0 <= angle <= 180.0:
        return None
    centers = (
        (165.0, "Low"),
        (135.0, "Low to Moderate"),
        (105.0, "Moderate"),
        (75.0, "Moderately High"),
        (45.0, "High"),
        (15.0, "Very High"),
    )
    center, label = min(centers, key=lambda item: abs(item[0] - angle))
    return label if abs(center - angle) <= 20.0 else None


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
        r"\bAUM\s+as\s+on\s+last\s+day\s*\n+\s*([0-9][0-9,]*(?:\.[0-9]+)?)\b",
        r"\bAUM\s+as\s+on\s+[^\n:]{3,45}\s*:\s*(?:Rs\.?|`|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:crores?|crs?\.?)\b",
        r"\bMonth\s+end\s+AUM\s+(?:Rs\.?|`|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\b",
        r"\bNet\s+AUM\s*(?:\(\s*Cr\.?\s*\)|₹\s*Crores?)\s*\n+\s*([0-9][0-9,]*(?:\.[0-9]+)?)\b",
        r"\bTOTAL\s+AUM\s*:?\s*(?:Rs\.?|`|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:crs?\.?|crores?)\b",
        r"\bAUM\s*:\s*(?:Rs\.?|`|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:crs?\.?|crores?)\b",
        r"Assets\s+Under\s+Management[\s\S]{0,260}?(?:Rs\.?|`|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:crores?|cr)\b",
        r"Assets\s+Under\s+Management[\s\S]{0,260}?(?:crores?|cr)\s*\n\s*([0-9][0-9,]*(?:\.[0-9]+)?)\b",
        r"Closing\s+AUM[\s\S]{0,120}?:\s*(?:Rs\.?|`|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:crores?|cr)\b",
        r"Monthly\s+AAUM[\s\S]{0,120}?:\s*(?:Rs\.?|`|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:crores?|cr)\b",
        r"Latest\s+AUM[\s\S]{0,120}?(?:Rs\.?|`|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*\(?\s*(?:Rs\.?|`|₹)?\s*(?:crores?|cr)\b",
        r"MONTHLY\s*AVERAGE[\s\S]{0,120}?(?:Rs\.?|`|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:Cr\.?|crores?)\b",
        r"AS ON\s+[^\n]{1,30}\n\s*(?:Rs\.?|`|₹)?\s*([0-9][0-9,]*(?:\.[0-9]+)?)\s*(?:Cr\.?|crores?)\b",
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
        following = text[match.end():end]
        next_scheme = SCHEME_NAME_PATTERN.search(following)
        if next_scheme:
            next_name = _clean_scheme_name(next_scheme.group("name"))
            if _scheme_key(next_name) != _scheme_key(scheme_name):
                end = match.end() + next_scheme.start()
        value = _extract_aum(text[start:end])
        if value is not None:
            return value
    return None


def _extract_expense_ratio(chunk: str) -> float | None:
    ber_ter = _extract_ber_ter_expense_ratio(chunk)
    if ber_ter is not None:
        return ber_ter
    patterns = (
        r"Expense\s+Ratio\^?\s+Regular/Other\s+than\s+Direct\s+"
        r"[0-9]+(?:\.[0-9]+)?\s+Direct\s+([0-9]+(?:\.[0-9]+)?)\b",
        r"Expense\s+Ratio\s+Plan\s+Regular\s+Direct\s+TER\s+[0-9]+(?:\.[0-9]+)?\s+([0-9]+(?:\.[0-9]+)?)\b",
        r"Total\s+Expense\s+Ratio\s*:\s*Regular\s+Plan\s+[0-9]+(?:\.[0-9]+)?\s+Direct\s+Plan\s+([0-9]+(?:\.[0-9]+)?)\b",
        r"Direct\s+Plan\s*:\s*(?:\*\s*)?([0-9]+(?:\.[0-9]+)?)\s*%\*?",
        r"Base\s+Expense\s+Ratio[\s\S]{0,220}?Direct(?:\s+Plan)?\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Base\s+Expense\s+Ratio[\s\S]{0,220}?Direct\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Expense\s+Ratio[\s\S]{0,100}?Direct(?:\s+Plan)?\s*[:\-]\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Expense\s+Ratio[\s\S]{0,200}?Direct[\sA-Za-z()\/-]{0,40}[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"TER[\s\S]{0,160}?Direct(?:\s+Plan)?\s*[:\-]?\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Direct(?:\s+Plan)?[\s\S]{0,50}?Expense\s+Ratio[\s:=-]*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Base\s+Expense\s+Ratio\s*:\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Total\s+Expense\s+Ratio(?:\s*\*+)?\s*[:\-]?\s*\n+\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Month\s+End\s+Expense\s+Ratio[\s\S]{0,500}?\bDirect\s*\n+\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"Month\s+End\s+Expense\s+Ratio(?:\s*\*+)?\s*\n+\s*([0-9]+(?:\.[0-9]+)?)\s*%",
    )
    for pattern in patterns:
        match = re.search(pattern, chunk, flags=re.IGNORECASE)
        if not match:
            continue
        try:
            value = float(match.group(1))
        except ValueError:
            continue
        if _valid_expense_ratio(value):
            return value
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
        if _valid_expense_ratio(value):
            return value
    return None


def _extract_ber_ter_expense_ratio(text: str) -> float | None:
    """Read direct TER when available, otherwise the regular/ETF TER."""
    compact = " ".join(str(text or "").replace("\xa0", " ").split())
    if not compact:
        return None

    plan_patterns = (
        r"BER\s*/\s*TER\s*\(\s*Direct\s+Plan\s*\)\s*:?\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*%\s*/\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        r"BER\s*/\s*TER\s*\(\s*Regular\s+Plan\s*\)\s*:?\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*%\s*/\s*([0-9]+(?:\.[0-9]+)?)\s*%",
    )
    for index, pattern in enumerate(plan_patterns):
        match = re.search(pattern, compact, flags=re.IGNORECASE)
        if not match:
            continue
        value = float(match.group(2))
        if _valid_expense_ratio(value):
            return value
        if index == 1:
            continue

    generic = re.search(
        r"BER\s*/\s*TER(?:\s*\([^)]{1,40}\))?\s*:?\s*"
        r"([0-9]+(?:\.[0-9]+)?)\s*%\s*/\s*([0-9]+(?:\.[0-9]+)?)\s*%",
        compact,
        flags=re.IGNORECASE,
    )
    if generic:
        value = float(generic.group(2))
        if _valid_expense_ratio(value):
            return value
    return None


def _valid_expense_ratio(value: float | None) -> bool:
    return value is not None and 0.0 < float(value) <= 3.0


def _extract_axis_ter_ratios(text: str) -> dict[str, float]:
    lines = [_clean_line(line) for line in str(text or "").splitlines()]
    ratios: dict[str, float] = {}
    in_ter_section = False

    idx = 0
    while idx < len(lines):
        line = lines[idx]
        low = line.lower()
        if "discloser of total expenses ratio" in low or "disclosure of total expenses ratio" in low:
            in_ter_section = True
            idx += 1
            continue
        if not in_ter_section:
            idx += 1
            continue
        if _axis_ter_stop_line(line):
            in_ter_section = False
            idx += 1
            continue
        if not low.startswith("axis "):
            idx += 1
            continue

        name_parts = [line]
        cursor = idx + 1
        while cursor < len(lines):
            tail = lines[cursor]
            if tail.lower().startswith("axis "):
                break
            if _parse_axis_ter_number(tail) is not None:
                break
            if _axis_ter_stop_line(tail):
                break
            if tail:
                name_parts.append(tail)
            cursor += 1
        scheme_name = _clean_line(" ".join(name_parts))
        if not _looks_like_axis_table_scheme_name(scheme_name):
            idx += 1
            continue

        percentages: list[float] = []
        while cursor < len(lines):
            tail = lines[cursor]
            if tail.lower().startswith("axis ") or _axis_ter_stop_line(tail):
                break
            value = _parse_axis_ter_number(tail)
            if value is None:
                if tail:
                    break
                cursor += 1
                continue
            percentages.append(value)
            cursor += 1
        if len(percentages) not in {2, 4, 6}:
            idx = max(cursor, idx + 1)
            continue

        direct_ratio = percentages[-2] if len(percentages) == 6 else percentages[-1]
        if _valid_expense_ratio(direct_ratio):
            ratios[_scheme_key(scheme_name)] = direct_ratio
        idx = max(cursor, idx + 1)
    return ratios


def _parse_axis_ter_number(value: str) -> float | None:
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*%?\s*", str(value or ""))
    if not match:
        return None
    return _parse_number(match.group(1))


def _extract_axis_manager_map(text: str) -> dict[str, str]:
    blob = " ".join(_clean_line(line) for line in str(text or "").splitlines())
    manager_pattern = re.compile(
        r"\b(?P<manager>[A-Z][A-Za-z]+(?:\s+[A-Z][A-Za-z]*){0,3})\s+is\s+Managing\s+",
    )
    matches = list(manager_pattern.finditer(blob))
    manager_by_scheme: dict[str, list[str]] = {}

    for index, match in enumerate(matches):
        manager = " ".join(match.group("manager").split())
        if not manager or manager.lower() in {"fund", "scheme"}:
            continue
        end = matches[index + 1].start() if index + 1 < len(matches) else min(len(blob), match.end() + 1200)
        body = blob[match.end() : end]
        body = re.split(
            r"\b(?:PRODUCT\s+LABELLING|Statutory\s+Details|Risk\s+Factors|Mutual\s+Fund\s+investments)\b",
            body,
            maxsplit=1,
            flags=re.IGNORECASE,
        )[0]
        for scheme_name in _axis_scheme_names_from_text(body):
            key = _scheme_key(scheme_name)
            manager_by_scheme.setdefault(key, [])
            if manager not in manager_by_scheme[key]:
                manager_by_scheme[key].append(manager)

    return {key: "; ".join(names) for key, names in manager_by_scheme.items()}


def _axis_scheme_names_from_text(text: str) -> list[str]:
    pattern = re.compile(
        r"\bAxis\s+[A-Za-z0-9&,'()/:.\- ]{2,120}?(?:Fund|ETF|FoF|FOF|Plan)\b",
        flags=re.IGNORECASE,
    )
    names: list[str] = []
    for match in pattern.finditer(text or ""):
        name = _clean_scheme_name(match.group(0))
        name = re.sub(r"\s+since\s+.*$", "", name, flags=re.IGNORECASE).strip(" ,")
        if not name or name.lower().startswith("axis mutual fund"):
            continue
        if name not in names:
            names.append(name)
    return names


def _looks_like_axis_table_scheme_name(line: str) -> bool:
    text = _clean_line(line)
    if not text.lower().startswith("axis "):
        return False
    return bool(re.search(r"\b(Fund|ETF|FOF|FoF|Plan)\b", text, flags=re.IGNORECASE))


def _axis_ter_stop_line(line: str) -> bool:
    low = _clean_line(line).lower()
    if not low:
        return False
    stop_markers = (
        "date of",
        "sip investments",
        "past performance",
        "product labelling",
        "riskometer",
        "statutory details",
    )
    return any(low.startswith(marker) for marker in stop_markers)


def _parse_percent_text(value: str) -> float | None:
    match = re.fullmatch(r"\s*([0-9]+(?:\.[0-9]+)?)\s*%\s*", str(value or ""))
    if not match:
        return None
    parsed = _parse_number(match.group(1))
    return parsed


def _clean_line(value: str) -> str:
    return " ".join(str(value or "").replace("\xa0", " ").split()).strip()


def _extract_benchmark(chunk: str) -> str | None:
    patterns = (
        r"Riskometer\s*\(\s*([^) \n][^)\n]{2,90})\s*\)",
        r"AMFI\s+Tier\s+I\s+Benchmark\s+Index\s+([^\n]{3,90})",
        r"AMFI\s+Tier\s+I\s+Benchmark\s+Index\s*\n\s*([^\n]{3,90})",
        r"(?:Tier\s*I|Tier\s*1)\s+Benchmark(?:\s+Index)?\s*[:\-]\s*([^\n]{3,100})",
        r"Scheme\s+Benchmark(?:\s+Index)?\s*[:\-]\s*([^\n]{3,100})",
        r"Benchmark\s+(?:Name|Index)\s*[:\-]\s*([^\n]{3,100})",
        r"Benchmark\s*[:\-]\s*([^\n]{3,100})",
        r"#?\s*Benchmark\s+Index\s*\n\s*([^\n]{3,100})",
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
    hdfc_managers = _extract_hdfc_fund_managers(chunk)
    if hdfc_managers:
        return "; ".join(hdfc_managers)
    motilal_match = re.search(
        r"(?im)^Fund\s+and\s+Co-Fund\s+Managers?\s*:?\s*([\s\S]{0,2200})",
        chunk,
    )
    if motilal_match:
        body = re.split(
            r"(?im)^(?:NAV|Performance|SIP\s+Performance|IDCW\s+History|"
            r"Scheme\s+Statistics|Portfolio)\b",
            motilal_match.group(1),
            maxsplit=1,
        )[0]
        names = _extract_manager_names(body)
        if names:
            return "; ".join(names)
    block_patterns = (
        r"(?im)^Name\s+of\s+the\s+Fund\s+Managers?\s*[\s:]*([\s\S]{0,2200})",
        r"(?im)^Fund\s+Manager(?:\(s\)|s)?\**\s*:?\s*([\s\S]{0,2200})",
    )
    for pattern in block_patterns:
        match = re.search(pattern, chunk, flags=re.IGNORECASE)
        if not match:
            continue
        body = match.group(1)
        names = _extract_manager_names(body)
        if names:
            return "; ".join(names)
    managed_by = re.search(
        r"(?im)^Fund[ \t]+managed[ \t]+by[ \t]+((?:(?:Mr|Ms|Mrs)\.?[ \t]+)?"
        r"[A-Z][A-Za-z.'-]+(?:[ \t]+[A-Z][A-Za-z.'-]+){1,3})"
        r"(?=[ \t]*(?:$|\())",
        chunk,
    )
    if managed_by:
        return " ".join(managed_by.group(1).split())
    unanchored_match = re.search(
        r"(?i)Fund\s+Manager(?:\(s\)|s)?\**\s*:?\s*([\s\S]{0,2200})", chunk
    )
    if unanchored_match:
        scrambled_names = _extract_scrambled_column_manager_names(unanchored_match.group(1))
        if scrambled_names:
            return "; ".join(scrambled_names)
    return None


def _extract_hdfc_fund_managers(chunk: str) -> list[str]:
    match = re.search(
        r"(?im)^FUND\s+MANAGER\b[^\n]*$([\s\S]{0,1800})",
        chunk or "",
    )
    if not match:
        return []
    body = re.split(
        r"(?im)^(?:DATE\s+OF\s+ALLOTMENT|ASSETS\s+UNDER\s+MANAGEMENT|"
        r"EXPENSE\s+RATIO|BENCHMARK)\b",
        match.group(1),
        maxsplit=1,
    )[0]
    lines = [_clean_line(line) for line in body.splitlines() if _clean_line(line)]
    excluded = {"name", "since", "total exp", "total experience"}
    date_pattern = re.compile(
        r"(?i)^(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?(?:\s+\d{4})?$"
    )
    inline_manager_pattern = re.compile(
        r"^(?P<name>[A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3})\s+"
        r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|"
        r"Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|"
        r"Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2},?(?:\s+\d{4})?$",
        flags=re.IGNORECASE,
    )
    name_line_pattern = re.compile(r"^[A-Z][A-Za-z.'-]*(?:\s+[A-Z][A-Za-z.'-]*){0,3}$")
    managers: list[str] = []
    for index, line in enumerate(lines):
        inline_match = inline_manager_pattern.fullmatch(line)
        if inline_match:
            candidate = " ".join(inline_match.group("name").split())
            if candidate not in managers:
                managers.append(candidate)
            continue
        if not date_pattern.fullmatch(line):
            continue
        candidate_index = index - 1
        while candidate_index >= 0 and re.fullmatch(r"\([^)]{2,80}\)", lines[candidate_index]):
            candidate_index -= 1
        if candidate_index < 0:
            continue
        candidate = lines[candidate_index]
        if candidate.lower() in excluded or not name_line_pattern.fullmatch(candidate):
            continue
        if len(candidate.split()) == 1 and candidate_index > 0:
            previous = lines[candidate_index - 1]
            if (
                previous.lower() not in excluded
                and name_line_pattern.fullmatch(previous)
                and len(previous.split()) == 1
            ):
                candidate = f"{previous} {candidate}"
        if candidate not in managers:
            managers.append(candidate)
    return managers


def _extract_manager_names(text: str) -> list[str]:
    normalized_text = re.sub(
        r"\b(Mr|Ms|Mrs)\.?\s*(?:\n+\s*-\s*)?\n+\s*",
        r"\1. ",
        text or "",
    )
    names: list[str] = []
    for match in MANAGER_NAME_PATTERN.finditer(normalized_text):
        name = _clean_manager_name(match.group(0))
        if name and name not in names:
            names.append(name)
    untitled_pattern = re.compile(
        r"\b([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3})"
        r"(?=\s+Total\s+work\s+experience\b)"
    )
    for match in untitled_pattern.finditer(normalized_text):
        name = " ".join(match.group(1).split())
        if name not in names:
            names.append(name)
    managing_pattern = re.compile(
        r"\b([A-Z][A-Za-z.'-]+(?:\s+[A-Z][A-Za-z.'-]+){1,3})"
        r"(?=\s+(?:\([^)]*Fund\s+Manager[^)]*\)\s+)?"
        r"\((?i:Managing\s+(?:this\s+fund\s+)?Since)\b)",
    )
    for match in managing_pattern.finditer(normalized_text):
        name = " ".join(match.group(1).split())
        if name not in names:
            names.append(name)
    return names


def _clean_manager_name(value: str) -> str:
    name = " ".join(str(value or "").split())
    name = re.split(
        r"(?i)\s+(?:has|is|was|managing|overall|total|years?|since|w\.?e\.?f\.?)\b",
        name,
        maxsplit=1,
    )[0]
    return re.split(r"\s+-\s+|\s*\(", name, maxsplit=1)[0].strip(" ,;:-")


_SCRAMBLED_MANAGER_NAME_RUN_PATTERN = re.compile(r"\b([A-Z][a-z]+[ \t]+[A-Z][a-z]+)\b")

_SCRAMBLED_MANAGER_COMPANY_SUFFIX_WORDS = {
    "limited", "ltd", "corporation", "corp", "bank", "finance", "financial",
    "housing", "reit", "fund", "development", "company", "co", "group",
    "trust", "industries", "holdings", "power", "energy", "metal", "metals",
    "traders", "renewables", "infrastructure", "capital", "services",
    "systems", "national", "rural", "agriculture", "india", "private", "pvt",
    "prime", "airport", "airports", "steel", "cement", "cements", "ports",
    "terminals", "utilities", "grid", "wealth", "insurance", "mutual",
    "parks", "estate", "realty", "telecom", "motors", "chemicals", "pharma",
    "pharmaceuticals", "textiles", "mills", "works", "projects",
    "engineering", "construction", "consultants", "solutions",
    "technologies", "tech", "electronics", "electricals", "automobiles",
    "auto", "management", "securities", "life", "general", "clearing",
    "parent", "properties", "advisors", "advisory", "assets", "asset",
    "fincorp", "leasing", "logistics", "shipping", "textile", "cotton",
    "sugar", "paper", "petro", "petroleum", "oil", "gas", "cables", "wires",
    "pipes", "glass", "electric", "investment", "investments", "portion",
    "reverse", "repo", "commercial", "papers", "treasury",
}

# Known multi-word conglomerate/bank names that recur as bond issuers in debt-fund
# portfolios and don't contain a single blocklisted suffix word within a 2-word
# window (e.g. "Aditya Birla Renewables", "Kotak Mahindra Bank"). Matched as exact
# phrases rather than blocklisting the individual words, since words like "Aditya"
# are also common personal first names and would cause false negatives on real
# fund managers.
_SCRAMBLED_MANAGER_KNOWN_COMPANY_PHRASES = {
    "aditya birla", "kotak mahindra", "bharti airtel", "bharti telecom",
    "state bank", "punjab national", "canara bank", "axis bank", "hdfc bank",
    "icici bank", "union bank", "reliance industries", "tata motors",
    "tata capital", "tata steel", "mahindra finance", "bajaj finance",
    "bajaj auto", "bajaj housing", "godrej properties", "larsen toubro",
    "sundaram finance", "cholamandalam investment", "small industries",
    "national bank", "indian railway", "power finance", "export import",
    "indian oil", "life insurance", "max financial", "hdfc life", "sbi life",
    "canara hsbc", "niva bupa", "adani power", "adani airport",
    "torrent power", "torrent pharmaceuticals", "gmr airports",
    "mindspace business", "nuvama wealth", "nuvoco vistas",
    "jamnagar utilities", "sikka ports", "grasim industries",
    "muthoot finance", "muthoot fincorp", "piramal finance",
    "indostar capital", "kogta financial", "tata housing", "lic housing",
    "shriram finance", "shriram pistons", "bahadur chand", "motilal oswal",
    "angel one", "nuvama clearing", "indian bank", "federal bank",
    "indusind bank", "equitas small",
}


def _looks_like_scrambled_manager_person_name(candidate: str) -> bool:
    words = candidate.split()
    if not (2 <= len(words) <= 3):
        return False
    if any(word.lower().strip(".") in _SCRAMBLED_MANAGER_COMPANY_SUFFIX_WORDS for word in words):
        return False
    if any(len(word) < 2 for word in words):
        return False
    if candidate.lower() in _SCRAMBLED_MANAGER_KNOWN_COMPANY_PHRASES:
        return False
    return True


def _extract_scrambled_column_manager_names(body: str) -> list[str]:
    """Recovers manager names from multi-column factsheet pages (e.g. DSP's debt-fund
    pages) where pdfplumber's reading-order reconstruction interleaves a narrow
    manager-info sidebar with a wide portfolio-holdings table, breaking the normal
    line-anchored "Fund Manager:" patterns. "Total work experience of N years." is a
    reliable, unambiguous per-manager marker regardless of column position; the
    manager's name is taken as the nearest preceding same-line 2-word Title-Case run
    that doesn't look like a portfolio holding's corporate/instrument name.
    """
    marker_pattern = re.compile(r"(?i)Total\s+work\s+experience\s+of\s+\d+\s+years\.?")
    names: list[str] = []
    for match in marker_pattern.finditer(body):
        window = body[max(0, match.start() - 250):match.start()]
        candidates = [m.group(1) for m in _SCRAMBLED_MANAGER_NAME_RUN_PATTERN.finditer(window)]
        valid = [candidate for candidate in candidates if _looks_like_scrambled_manager_person_name(candidate)]
        if valid and valid[-1] not in names:
            names.append(valid[-1])
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
    if clean.lower() in {"returns", "benchmark returns", "additional benchmark returns"}:
        return False
    invalid_phrases = (
        "this product labelling is applicable only to the scheme",
        "product labelling",
        "product labeling",
        "investors should consult",
        "riskometer",
        "performance of the scheme",
        "the risk of",
        "overweight/underweight",
        "fund size",
        "aum (rs",
        "nav (rs",
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
    text = re.split(r"(?i)\b(?:Fund\s+Manager|Riskometer|Assets\s+Under\s+Management)\b", text)[0].strip(" :;,-")
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
