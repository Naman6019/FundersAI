from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

PRIORITY_VERSION = "mf_review_rule_based_v1"

_ISSUE_WEIGHTS = (
    ("parse_exception", 0.45, "Parser exception requires investigation"),
    ("raw_file_missing", 0.40, "Raw source file is unavailable"),
    ("raw_file_unavailable", 0.40, "Raw source file is unavailable"),
    ("holdings_not_found", 0.25, "Holdings were not extracted"),
    ("percent_aum_out_of_band", 0.20, "Holding weights need validation"),
    ("factsheet_fields_not_extracted", 0.18, "Expected factsheet fields are missing"),
    ("llm_partial_review_required", 0.15, "LLM extraction still requires review"),
)


def _age_days(value: Any) -> int:
    if not value:
        return 0
    try:
        timestamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - timestamp).days)
    except (TypeError, ValueError):
        return 0


def score_review_item(item: dict[str, Any]) -> dict[str, Any]:
    issues = [str(issue).strip().lower() for issue in item.get("validation_issues", []) if str(issue).strip()]
    score = 0.0
    reasons: list[str] = []
    for marker, weight, reason in _ISSUE_WEIGHTS:
        if any(marker in issue for issue in issues):
            score += weight
            reasons.append(reason)

    confidence = item.get("confidence_score")
    try:
        confidence_value = min(100.0, max(0.0, float(confidence)))
        confidence_penalty = (1.0 - confidence_value / 100.0) * 0.25
        if confidence_value < 90:
            reasons.append(f"Extractor confidence is {confidence_value:g}%")
    except (TypeError, ValueError):
        confidence_penalty = 0.10
        reasons.append("Extractor confidence is unavailable")
    score += confidence_penalty

    age_days = _age_days(item.get("created_at"))
    if age_days >= 14:
        score += min(0.15, 0.05 + (age_days - 14) * 0.005)
        reasons.append(f"Review has been waiting {age_days} days")

    score = min(score, 1.0)
    priority = "high" if score >= 0.65 else "medium" if score >= 0.35 else "low"
    return {
        **item,
        "priority_version": PRIORITY_VERSION,
        "priority": priority,
        "priority_score": round(score, 3),
        "priority_reasons": reasons or ["Pending manual review"],
    }


class ReviewPriorityService:
    """Deterministic baseline that creates auditable labels for a later supervised model."""

    def __init__(self, repository: Any):
        self.repository = repository

    def list_prioritized(self, *, limit: int = 100) -> dict[str, Any]:
        rows = self.repository.list_pending_review_items(limit=max(1, min(limit, 500)))
        ranked = [score_review_item(row) for row in rows]
        ranked.sort(key=lambda item: (-item["priority_score"], item.get("created_at") or "", item.get("source_document_id") or ""))
        return {
            "priority_version": PRIORITY_VERSION,
            "method": "deterministic review triage baseline; no automated resolution",
            "items": ranked,
            "summary": {
                "total": len(ranked),
                "high": sum(item["priority"] == "high" for item in ranked),
                "medium": sum(item["priority"] == "medium" for item in ranked),
                "low": sum(item["priority"] == "low" for item in ranked),
            },
        }
