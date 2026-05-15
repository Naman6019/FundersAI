from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

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
