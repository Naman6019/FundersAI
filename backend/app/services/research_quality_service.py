from __future__ import annotations

import json
import os
import re
from typing import Any

import requests


RELEVANCE_GRADER_VERSION = "official_evidence_relevance_v1"
CLAIM_VALIDATOR_VERSION = "claim_citation_support_v1"


def _enabled(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).strip().lower() in {"1", "true", "yes", "on"}


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+(?:\.[0-9]+)?%?", str(value or "").lower())
        if len(token) >= 2
    }


def _deterministic_rewrite(query: str) -> str:
    replacements = {
        "ter": "total expense ratio",
        "tech": "information technology sector allocation",
        "holdings": "portfolio security holdings percentage nav",
        "risk": "riskometer volatility drawdown",
    }
    words = re.findall(r"[a-z0-9.%]+", query.lower())
    stopwords = {
        "a", "an", "and", "are", "can", "does", "for", "from", "how", "in", "is", "it",
        "me", "of", "official", "please", "show", "the", "this", "to", "what", "where", "which",
    }
    compact = [replacements.get(word, word) for word in words if word not in stopwords]
    return " ".join(compact).strip() or query.strip()


class OfficialEvidenceRelevanceGrader:
    """Grades retrieved official evidence and proposes at most one corpus-only rewrite."""

    def __init__(self, *, http_post=requests.post):
        self.http_post = http_post
        self.llm_enabled = _enabled("MF_RESEARCH_LLM_GRADER_ENABLED")

    def grade(self, query: str, retrieval: dict[str, Any], *, allow_rewrite: bool) -> dict[str, Any]:
        sources = retrieval.get("sources") or []
        coverage = float(retrieval.get("query_coverage") or 0.0)
        fallback = self._deterministic_grade(query, sources, coverage, allow_rewrite=allow_rewrite)
        if not self.llm_enabled or not sources:
            return fallback

        try:
            llm_result = self._llm_grade(query, sources, allow_rewrite=allow_rewrite)
        except Exception as exc:
            return {**fallback, "model_status": "fallback", "fallback_reason": type(exc).__name__}

        relevant = bool(llm_result.get("relevant"))
        rewritten_query = str(llm_result.get("rewritten_query") or "").strip() if allow_rewrite else ""
        if rewritten_query.casefold() == query.strip().casefold():
            rewritten_query = ""
        return {
            "grader_version": RELEVANCE_GRADER_VERSION,
            "relevant": relevant,
            "score": round(float(llm_result.get("score") or (1.0 if relevant else 0.0)), 4),
            "reason": str(llm_result.get("reason") or "LLM relevance grade."),
            "rewritten_query": rewritten_query,
            "rewrite_scope": "official_document_corpus",
            "model_status": "active",
        }

    @staticmethod
    def _deterministic_grade(
        query: str,
        sources: list[dict[str, Any]],
        coverage: float,
        *,
        allow_rewrite: bool,
    ) -> dict[str, Any]:
        relevant = bool(sources) and coverage >= 0.35
        rewritten_query = ""
        if not relevant and allow_rewrite:
            candidate = _deterministic_rewrite(query)
            if candidate.casefold() != query.strip().casefold():
                rewritten_query = candidate
        return {
            "grader_version": RELEVANCE_GRADER_VERSION,
            "relevant": relevant,
            "score": round(coverage, 4),
            "reason": "Official evidence met the deterministic coverage gate." if relevant else "Official evidence did not meet the relevance gate.",
            "rewritten_query": rewritten_query,
            "rewrite_scope": "official_document_corpus",
            "model_status": "deterministic",
        }

    def _llm_grade(self, query: str, sources: list[dict[str, Any]], *, allow_rewrite: bool) -> dict[str, Any]:
        key = os.getenv("OPENROUTER_API_KEY", "").strip()
        if not key or key == "OPENROUTER_API_KEY_PLACEHOLDER":
            raise RuntimeError("openrouter_key_missing")
        context = "\n\n".join(
            f"[Source {index}] {source.get('excerpt', '')}"
            for index, source in enumerate(sources[:5], start=1)
        )
        prompt = (
            "Grade whether the official AMC excerpts can answer the question. "
            "Return JSON with relevant (boolean), score (0 to 1), reason, and rewritten_query. "
            "A rewrite may only improve search inside the same official-document corpus; never request web search. "
            f"If rewriting is disabled, rewritten_query must be empty. Rewriting enabled: {allow_rewrite}.\n"
            f"Question: {query}\nEvidence:\n{context}"
        )
        response = self.http_post(
            os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1/chat/completions"),
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": os.getenv("MF_RESEARCH_GRADER_MODEL", os.getenv("OPENROUTER_MODEL", "")).strip(),
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0,
            },
            timeout=30,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        value = json.loads(content)
        if not isinstance(value, dict):
            raise ValueError("unexpected_relevance_grade")
        return value


def validate_claim_citations(
    answer: str,
    sources: list[dict[str, Any]],
    *,
    minimum_support: float = 0.65,
) -> dict[str, Any]:
    """Require every factual answer line to cite source text with meaningful token support."""
    claims: list[dict[str, Any]] = []
    citation_pattern = re.compile(r"\[(\d+)]")
    for raw_line in str(answer or "").splitlines():
        line = raw_line.strip().lstrip("- ").strip()
        if not line or line.endswith(":"):
            continue
        citation_numbers = [int(value) for value in citation_pattern.findall(line)]
        claim_text = citation_pattern.sub("", line).strip()
        claim_tokens = _tokens(claim_text)
        valid_indexes = [index for index in citation_numbers if 1 <= index <= len(sources)]
        evidence = " ".join(str(sources[index - 1].get("excerpt") or "") for index in valid_indexes)
        evidence_tokens = _tokens(evidence)
        support = len(claim_tokens & evidence_tokens) / max(1, len(claim_tokens))
        supported = bool(valid_indexes) and bool(claim_tokens) and support >= minimum_support
        claims.append(
            {
                "claim": claim_text[:240],
                "citations": valid_indexes,
                "support": round(support, 4),
                "supported": supported,
            }
        )

    supported_count = sum(bool(claim["supported"]) for claim in claims)
    valid = bool(sources) and bool(claims) and supported_count == len(claims)
    return {
        "validator_version": CLAIM_VALIDATOR_VERSION,
        "valid": valid,
        "claims": claims,
        "claim_count": len(claims),
        "supported_claims": supported_count,
        "support_rate": round(supported_count / max(1, len(claims)), 4),
    }
