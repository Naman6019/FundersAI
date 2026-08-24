from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

from rapidfuzz import fuzz, process


@dataclass(frozen=True)
class SchemeMatch:
    input_name: str
    canonical_name: str
    confidence: float


DEFAULT_SCHEMES = [
    "Parag Parikh Flexi Cap Fund",
]


def _normalize_name(value: str) -> str:
    return " ".join(str(value or "").lower().replace(".", " ").replace(",", " ").replace("&", " ").split())


def match_scheme_name(input_name: str, candidates: Iterable[str] | None = None) -> SchemeMatch:
    source_choices = DEFAULT_SCHEMES if candidates is None else candidates
    choices = [name for name in source_choices if name]
    if not input_name and choices:
        return SchemeMatch(input_name="", canonical_name=choices[0], confidence=0.0)
    if not choices:
        confidence = 100.0 if input_name else 0.0
        return SchemeMatch(input_name=input_name, canonical_name=input_name, confidence=confidence)

    normalized_input = _normalize_name(input_name)
    if normalized_input:
        exact = next((choice for choice in choices if _normalize_name(choice) == normalized_input), None)
        if exact is not None:
            return SchemeMatch(input_name=input_name, canonical_name=exact, confidence=100.0)

    best = process.extractOne(input_name, choices, scorer=fuzz.WRatio)
    if not best:
        return SchemeMatch(input_name=input_name, canonical_name=input_name, confidence=0.0)

    canonical, score, _ = best
    return SchemeMatch(input_name=input_name, canonical_name=canonical, confidence=float(score))


# --- Scheme-name normalization and candidate selection -----------------------
# Moved here from mf_ingestion/services/parsing_service.py. These are pure text
# helpers with no I/O; they were the bulk of what made that module a 2,000-line
# parse orchestrator, and they belong beside match_scheme_name, which
# _select_best_scheme_candidate already calls.


_FAMILY_CATEGORY_SUBS = (
    (re.compile(r"\bfund\s+of\s+funds?\b"), "fof"),
    (re.compile(r"\bflexi\s+cap\b"), "flexicap"),
    (re.compile(r"\bmid\s+cap\b"), "midcap"),
    (re.compile(r"\bsmall\s+cap\b"), "smallcap"),
    (re.compile(r"\blarge\s+cap\b"), "largecap"),
)


_FAMILY_PLAN_QUALIFIER_WORDS = {
    "plan",
    "option",
    "direct",
    "regular",
    "retail",
    "institutional",
    "growth",
    "idcw",
    "dividend",
    "cumulative",
    "payout",
    "payment",
    "reinvestment",
    "bonus",
    "of",
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "half",
    "yearly",
    "annual",
}


def _normalize_scheme_text(text: str) -> str:
    return " ".join(str(text or "").lower().replace(".", " ").replace(",", " ").split())


def _normalize_lookup_text(text: object) -> str:
    value = str(text or "").lower().replace("&", " and ")
    value = value.replace("unit linked insurance plan", " ")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"(?<=[a-z])(?=\d)", " ", value)
    value = re.sub(r"\b(\w+)(?:\s+\1\b)+", r"\1", value)
    return " ".join(value.split())


def _scheme_name_for_matching(text: str) -> str:
    value = " ".join(str(text or "").replace("\xa0", " ").split()).strip()
    value = re.sub(r"(?i)\(erstwhile known as [^)]+\)", "", value).strip()
    value = re.sub(r"(?i)^scheme(?:\s+name)?\s*:\s*", "", value)
    return value.rstrip(" .")


def _build_ilike_pattern(text: str) -> str:
    words = [word for word in _normalize_lookup_text(text).split() if word]
    return f"%{'%'.join(words)}%" if words else "%"


def _build_relaxed_ilike_pattern(text: str) -> str:
    tokens = [token for token in _normalize_lookup_text(text).split() if token]
    removable = {
        "fund",
        "plan",
        "option",
        "direct",
        "regular",
        "growth",
        "idcw",
        "dividend",
        "cumulative",
        "daily",
        "weekly",
        "monthly",
        "quarterly",
        "half",
        "yearly",
        "annual",
        "and",
        "etf",
        "exchange",
        "traded",
        "mf",
    }
    filtered = [token for token in tokens if token not in removable]
    base = filtered if filtered else tokens
    return f"%{'%'.join(base)}%" if base else "%"


def _apply_family_category_subs(text: str) -> str:
    for pattern, replacement in _FAMILY_CATEGORY_SUBS:
        text = pattern.sub(replacement, text)
    return text


def _normalize_family_scheme_name(value: object) -> str:
    raw_str = re.sub(r"(\d+)-(\d+)", r"\1 \2", str(value or ""))
    text = _apply_family_category_subs(_normalize_lookup_text(raw_str))
    tokens = text.split()
    while len(tokens) > 1 and tokens[-1] in _FAMILY_PLAN_QUALIFIER_WORDS:
        tokens.pop()
    return " ".join(tokens)


def _is_direct_growth_name(name: object) -> bool:
    text = _normalize_scheme_text(str(name or ""))
    return "direct" in text and ("growth" in text or "cumulative" in text)


def _has_plan_or_option_marker(name: object) -> bool:
    text = _normalize_scheme_text(str(name or ""))
    markers = (
        "direct",
        "regular",
        "growth",
        "idcw",
        "dividend",
        "monthly",
        "weekly",
        "daily",
        "quarterly",
        "half yearly",
        "annual",
        "cumulative",
    )
    return any(marker in text for marker in markers)


def _pick_best_scheme_candidate(target_name: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    target_text = _normalize_scheme_text(target_name)
    target_tokens = set(target_text.split())
    wants_direct = "direct" in target_tokens
    wants_regular = "regular" in target_tokens
    wants_growth = "growth" in target_tokens or "cumulative" in target_tokens
    wants_idcw = "idcw" in target_tokens or "dividend" in target_tokens

    def score(candidate: dict[str, Any]) -> tuple[int, int, int]:
        candidate_name = str(candidate.get("scheme_name") or "")
        candidate_text = _normalize_scheme_text(candidate_name)
        candidate_tokens = set(candidate_text.split())
        overlap = len(target_tokens & candidate_tokens)
        value = overlap * 20
        if target_text and target_text in candidate_text:
            value += 60
        if "direct" in candidate_tokens:
            value += 12 if wants_direct else 8
        if "regular" in candidate_tokens:
            value += 10 if wants_regular else -8
        if ("growth" in candidate_tokens or "cumulative" in candidate_tokens):
            value += 8 if wants_growth else 5
        if ("idcw" in candidate_tokens or "dividend" in candidate_tokens):
            value += 8 if wants_idcw else -12
        return value, overlap, -len(candidate_tokens)

    ordered = sorted(candidates, key=score, reverse=True)
    return ordered[0]


def _select_best_scheme_candidate(target_name: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    deduped: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        code = str(candidate.get("scheme_code") or "").strip()
        if not code:
            continue
        deduped[code] = candidate
    unique_candidates = list(deduped.values())
    if not unique_candidates:
        return None

    target_family = _normalize_family_scheme_name(target_name)
    scored: list[tuple[float, dict[str, Any]]] = []
    for candidate in unique_candidates:
        candidate_family = _normalize_family_scheme_name(candidate.get("scheme_name"))
        confidence = match_scheme_name(target_family, candidates=[candidate_family]).confidence
        scored.append((confidence, candidate))
    best_confidence = max(score for score, _candidate in scored)
    family_candidates = [
        candidate
        for score, candidate in scored
        if score >= best_confidence - 0.01
    ]
    return _pick_best_scheme_candidate(target_name, family_candidates)
