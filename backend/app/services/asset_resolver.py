from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from typing import Any

from app.repositories.mutual_fund_repository import MutualFundRepository
from app.stock_universe import resolve_stock_symbol

logger = logging.getLogger(__name__)

SUPPORTED_MF_AMC_MARKERS: dict[str, tuple[str, ...]] = {
    "HDFC": ("hdfc",),
    "SBI": ("sbi",),
    "ICICI": ("icici",),
    "AXIS": ("axis",),
    "PPFAS": ("ppfas", "parag parikh", "parag", "parikh"),
}

UNSUPPORTED_MF_AMC_KEYWORDS = (
    "quant", "nippon", "kotak", "mirae", "uti", "dsp", "tata", "motilal",
    "canara", "groww", "zerodha", "bandhan", "idfc", "franklin", "edelweiss",
    "sundaram", "lic", "pgim", "invesco", "hsbc", "union", "baroda", "bnp",
    "mahindra", "shriram", "whiteoak", "samco", "helios", "navi", "quantum",
    "taurus", "360 one", "iifl", "jm financial",
)

HIGH_CONFIDENCE = 0.88
MEDIUM_CONFIDENCE = 0.68


@dataclass(frozen=True)
class ResolverCandidate:
    resolved_name: str
    asset_type: str
    id: str | None
    confidence: float
    amc: str | None = None
    match_reason: str | None = None

    def client_payload(self) -> dict[str, Any]:
        return {
            "resolved_name": self.resolved_name,
            "asset_type": self.asset_type,
            "id": self.id,
            "confidence": round(self.confidence, 4),
            "amc": self.amc,
            "match_reason": self.match_reason,
        }


@dataclass(frozen=True)
class AssetResolution:
    input: str
    resolved_name: str | None
    asset_type: str
    id: str | None
    confidence: float
    coverage_status: str
    amc: str | None = None
    match_reason: str | None = None
    candidates: tuple[ResolverCandidate, ...] = field(default_factory=tuple)
    cache_hit: bool = False

    @property
    def is_high_confidence(self) -> bool:
        return self.confidence >= HIGH_CONFIDENCE and self.coverage_status == "supported"

    @property
    def is_medium_confidence(self) -> bool:
        return MEDIUM_CONFIDENCE <= self.confidence < HIGH_CONFIDENCE

    def client_payload(self) -> dict[str, Any]:
        payload = {
            "input": self.input,
            "resolved_name": self.resolved_name,
            "asset_type": self.asset_type,
            "id": self.id,
            "confidence": round(self.confidence, 4),
            "coverage_status": self.coverage_status,
            "amc": self.amc,
            "match_reason": self.match_reason,
            "cache_hit": self.cache_hit,
        }
        if self.is_medium_confidence and self.candidates:
            payload["candidates"] = [candidate.client_payload() for candidate in self.candidates[:3]]
        return payload


class ResolverCache:
    def __init__(self, ttl_seconds: int = 300, max_size: int = 256):
        self.ttl_seconds = ttl_seconds
        self.max_size = max_size
        self._items: dict[str, tuple[float, AssetResolution]] = {}

    def get(self, key: str) -> AssetResolution | None:
        now = time.monotonic()
        item = self._items.get(key)
        if not item:
            return None
        expires_at, value = item
        if expires_at <= now:
            self._items.pop(key, None)
            return None
        return AssetResolution(
            input=value.input,
            resolved_name=value.resolved_name,
            asset_type=value.asset_type,
            id=value.id,
            confidence=value.confidence,
            coverage_status=value.coverage_status,
            amc=value.amc,
            match_reason=value.match_reason,
            candidates=value.candidates,
            cache_hit=True,
        )

    def set(self, key: str, value: AssetResolution) -> None:
        if not value.is_high_confidence:
            return
        if len(self._items) >= self.max_size:
            oldest = min(self._items.items(), key=lambda item: item[1][0])[0]
            self._items.pop(oldest, None)
        self._items[key] = (time.monotonic() + self.ttl_seconds, value)

    def clear(self) -> None:
        self._items.clear()


resolver_cache = ResolverCache()


def normalize_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value or "").lower()))


def fund_name_words(value: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(value or "").lower())


def has_mf_category_hint(words: list[str]) -> bool:
    joined = " ".join(words)
    return any(token in words for token in ("fund", "cap", "flexi", "mid", "large", "small", "nav", "amc")) or "flexi cap" in joined


def looks_like_ppfas_alias(value: str) -> bool:
    words = fund_name_words(value)
    if not words:
        return False
    word_set = set(words)
    if word_set.intersection({"ppfas", "ppfa"}):
        return True
    if word_set.intersection({"parag", "parikh"}):
        return True
    if not has_mf_category_hint(words):
        return False
    if word_set.intersection({"paras", "parakh", "parik", "prag", "paraag", "pfas"}):
        return True
    return any(
        len(word) >= 4
        and (
            SequenceMatcher(None, word, "parag").ratio() >= 0.78
            or SequenceMatcher(None, word, "parikh").ratio() >= 0.78
        )
        for word in words
    )


def looks_like_axis_alias(value: str) -> bool:
    words = fund_name_words(value)
    if not words:
        return False
    word_set = set(words)
    if "axis" in word_set:
        return True
    return "axs" in word_set and has_mf_category_hint(words)


def supported_amc_from_text(value: str) -> str | None:
    text = normalize_text(value)
    if looks_like_ppfas_alias(text):
        return "PPFAS"
    if looks_like_axis_alias(text):
        return "AXIS"
    for label, markers in SUPPORTED_MF_AMC_MARKERS.items():
        if any(marker in text for marker in markers):
            return label
    return None


def canonical_fund_query(value: str) -> str:
    text = normalize_text(value)
    if looks_like_ppfas_alias(text) and "flexi" in text:
        return "Parag Parikh Flexi Cap"
    if looks_like_axis_alias(text) and "flexi" in text:
        return "Axis Flexi Cap"
    if looks_like_axis_alias(text) and "large" in text:
        return "Axis Large Cap"
    if "hdfc" in text and "flexi" in text:
        return "HDFC Flexi Cap"
    if "icici" in text and "multi" in text:
        return "ICICI Multi Asset"
    if "icici" in text and "large" in text:
        return "ICICI Prudential Large Cap"
    if "sbi" in text and ("blue" in text or "bluechip" in text):
        return "SBI Bluechip"
    if "flexi" in text and "cap" not in text:
        return f"{value} Cap"
    return value


def is_supported_mf_query_text(value: str) -> bool:
    return supported_amc_from_text(value) is not None


def has_unsupported_mf_keyword(value: str) -> bool:
    text = normalize_text(value)
    return any(re.search(rf"\b{re.escape(keyword)}\b", text) for keyword in UNSUPPORTED_MF_AMC_KEYWORDS)


def _fund_search_pattern(search_term: str) -> str:
    cleaned = (
        normalize_text(search_term)
        .replace(" fund", "")
        .replace(" growth", "")
        .strip()
    )
    words = [word for word in cleaned.split() if word]
    return f"%{'%'.join(words)}%" if words else "%"


def _coerce_scheme_code_filter(value: Any) -> Any:
    text = str(value or "").strip()
    return int(text) if text.isdigit() else text


class AssetResolver:
    def __init__(self, repository: Any = None, cache: ResolverCache | None = None):
        self.repository = repository if isinstance(repository, MutualFundRepository) else MutualFundRepository(repository)
        self.cache = cache if cache is not None else resolver_cache

    def resolve_many(self, inputs: list[str], asset_type: str = "auto") -> list[AssetResolution]:
        return [self.resolve(item, asset_type=asset_type) for item in inputs]

    def resolve(self, raw_input: str, asset_type: str = "auto") -> AssetResolution:
        if asset_type == "stock":
            return self._resolve_stock(raw_input)
        if asset_type == "mutual_fund":
            return self._resolve_mutual_fund(raw_input)

        mf_hint = has_mf_category_hint(fund_name_words(raw_input)) or is_supported_mf_query_text(raw_input)
        if mf_hint:
            return self._resolve_mutual_fund(raw_input)
        stock = self._resolve_stock(raw_input)
        return stock if stock.coverage_status == "supported" else self._resolve_mutual_fund(raw_input)

    def _resolve_stock(self, raw_input: str) -> AssetResolution:
        symbol = resolve_stock_symbol(raw_input)
        if symbol:
            return AssetResolution(
                input=raw_input,
                resolved_name=symbol,
                asset_type="stock",
                id=symbol,
                confidence=0.96,
                coverage_status="supported",
                match_reason="stock_symbol_resolver",
            )
        return AssetResolution(
            input=raw_input,
            resolved_name=None,
            asset_type="stock",
            id=None,
            confidence=0.0,
            coverage_status="not_found",
            match_reason="stock_symbol_not_found",
        )

    def _resolve_mutual_fund(self, raw_input: str) -> AssetResolution:
        normalized = normalize_text(raw_input)
        cache_key = f"mf:{normalized}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        if has_unsupported_mf_keyword(normalized):
            return AssetResolution(
                input=raw_input,
                resolved_name=None,
                asset_type="mutual_fund",
                id=None,
                confidence=0.0,
                coverage_status="unsupported",
                match_reason="unsupported_amc_keyword",
            )

        query = canonical_fund_query(raw_input)
        rows = self._candidate_rows(query)
        if not rows and query != raw_input:
            rows = self._candidate_rows(raw_input)

        candidates = tuple(self._score_candidates(raw_input, query, rows)[:5])
        if not candidates:
            status = "not_found" if is_supported_mf_query_text(query) else "unsupported"
            return AssetResolution(
                input=raw_input,
                resolved_name=None,
                asset_type="mutual_fund",
                id=None,
                confidence=0.0,
                coverage_status=status,
                match_reason="no_local_candidate",
            )

        top = candidates[0]
        coverage_status = "supported" if top.confidence >= HIGH_CONFIDENCE else "ambiguous"
        result = AssetResolution(
            input=raw_input,
            resolved_name=top.resolved_name if top.confidence >= MEDIUM_CONFIDENCE else None,
            asset_type="mutual_fund",
            id=top.id if top.confidence >= MEDIUM_CONFIDENCE else None,
            confidence=top.confidence,
            coverage_status=coverage_status if top.confidence >= MEDIUM_CONFIDENCE else "not_found",
            amc=top.amc,
            match_reason=top.match_reason,
            candidates=candidates,
        )
        self.cache.set(cache_key, result)
        logger.info(
            "asset_resolver input=%r normalized=%r selected=%r confidence=%.3f status=%s candidates=%s",
            raw_input,
            normalized,
            result.resolved_name,
            result.confidence,
            result.coverage_status,
            [candidate.client_payload() for candidate in candidates[:3]],
        )
        return result

    def _candidate_rows(self, query: str) -> list[dict[str, Any]]:
        if not self.repository:
            return []
        pattern = _fund_search_pattern(query)
        try:
            return self.repository.search_mutual_funds(pattern, limit=25)
        except Exception as exc:
            logger.warning("asset resolver candidate lookup failed for %r: %s", query, exc)
            return []

    def _score_candidates(self, raw_input: str, query: str, rows: list[dict[str, Any]]) -> list[ResolverCandidate]:
        input_norm = normalize_text(query or raw_input)
        raw_norm = normalize_text(raw_input)
        input_words = [word for word in input_norm.split() if len(word) > 2]
        scored: list[ResolverCandidate] = []
        for row in rows:
            name = str(row.get("scheme_name") or "")
            name_norm = normalize_text(name)
            score = 0.0
            reasons: list[str] = []
            if input_norm and input_norm in name_norm:
                score += 0.58
                reasons.append("name_contains_query")
            overlap = sum(1 for word in input_words if word in name_norm)
            if input_words:
                score += 0.4 * (overlap / len(input_words))
                reasons.append(f"token_overlap:{overlap}/{len(input_words)}")
                if overlap == len(input_words) and input_norm not in name_norm:
                    score += 0.18
                    reasons.append("all_query_tokens_match")
            if canonical_fund_query(raw_input) != raw_input and normalize_text(canonical_fund_query(raw_input)) in name_norm:
                score += 0.28
                reasons.append("alias_canonical_match")
            if "direct" in name_norm:
                score += 0.03
            if "regular" in name_norm:
                score -= 0.05
            amc = supported_amc_from_text(" ".join([name, str(row.get("amc_name") or "")]))
            if amc:
                score += 0.08
            if raw_norm == name_norm:
                score = 1.0
                reasons.append("exact_name")
            confidence = max(0.0, min(score, 1.0))
            scored.append(
                ResolverCandidate(
                    resolved_name=name,
                    asset_type="mutual_fund",
                    id=str(row.get("scheme_code")) if row.get("scheme_code") is not None else None,
                    confidence=confidence,
                    amc=amc,
                    match_reason=",".join(reasons) or "candidate_rank",
                )
            )
        return sorted(scored, key=lambda candidate: candidate.confidence, reverse=True)
