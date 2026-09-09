"""Typed, safety-first contract for the Fund Truth Check.

Phase 0 deliberately contains no parsing, metric calculation, retrieval, or
recommendation logic. It gives later phases one restricted language for claims
and makes clarification a separate state from a factual verdict.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ClaimMetric(str, Enum):
    EXPENSE_RATIO = "expense_ratio"
    AUM = "aum"
    CAGR = "cagr"
    ROLLING_RETURN = "rolling_return"
    SHARPE_RATIO = "sharpe_ratio"
    MAX_DRAWDOWN = "max_drawdown"
    VOLATILITY = "volatility"
    RISKOMETER = "riskometer"
    BENCHMARK = "benchmark"
    FUND_MANAGER = "fund_manager"
    HOLDS_STOCK = "holds_stock"
    STOCK_EXPOSURE = "stock_exposure"
    SECTOR_EXPOSURE = "sector_exposure"
    HOLDINGS_CONCENTRATION = "holdings_concentration"
    PORTFOLIO_OVERLAP = "portfolio_overlap"
    INVESTMENT_OBJECTIVE = "investment_objective"


class ClaimVerdict(str, Enum):
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    MIXED = "mixed"
    UNVERIFIABLE = "unverifiable"


class ClaimFreshness(str, Enum):
    CURRENT = "current"
    STALE = "stale"
    UNKNOWN = "unknown"


class ClaimStatus(str, Enum):
    EVALUATED = "evaluated"
    CLARIFICATION_REQUIRED = "clarification_required"
    UNSUPPORTED = "unsupported"
    ENTITY_RESOLUTION_REQUIRED = "entity_resolution_required"


class ClaimOperator(str, Enum):
    LOWER_THAN = "lower_than"
    HIGHER_THAN = "higher_than"
    EQUAL_TO = "equal_to"
    DIFFERENT_FROM = "different_from"
    CONTAINS = "contains"
    DOES_NOT_CONTAIN = "does_not_contain"
    IS = "is"


class ClarificationOption(str, Enum):
    MAX_DRAWDOWN = ClaimMetric.MAX_DRAWDOWN.value
    VOLATILITY = ClaimMetric.VOLATILITY.value
    RISKOMETER = ClaimMetric.RISKOMETER.value
    ROLLING_RETURN = ClaimMetric.ROLLING_RETURN.value
    HOLDINGS_CONCENTRATION = ClaimMetric.HOLDINGS_CONCENTRATION.value
    SECTOR_EXPOSURE = ClaimMetric.SECTOR_EXPOSURE.value
    PORTFOLIO_OVERLAP = ClaimMetric.PORTFOLIO_OVERLAP.value


SUBJECTIVE_TERM_CLARIFICATIONS: dict[str, tuple[ClarificationOption, ...]] = {
    "less risky": (
        ClarificationOption.MAX_DRAWDOWN,
        ClarificationOption.VOLATILITY,
        ClarificationOption.RISKOMETER,
    ),
    "lower risk": (
        ClarificationOption.MAX_DRAWDOWN,
        ClarificationOption.VOLATILITY,
        ClarificationOption.RISKOMETER,
    ),
    "stable": (
        ClarificationOption.ROLLING_RETURN,
        ClarificationOption.VOLATILITY,
        ClarificationOption.MAX_DRAWDOWN,
    ),
    "safer": (
        ClarificationOption.MAX_DRAWDOWN,
        ClarificationOption.VOLATILITY,
        ClarificationOption.RISKOMETER,
    ),
    "safe": (
        ClarificationOption.MAX_DRAWDOWN,
        ClarificationOption.VOLATILITY,
        ClarificationOption.RISKOMETER,
    ),
    "consistent": (
        ClarificationOption.ROLLING_RETURN,
        ClarificationOption.VOLATILITY,
        ClarificationOption.MAX_DRAWDOWN,
    ),
    "diversified": (
        ClarificationOption.HOLDINGS_CONCENTRATION,
        ClarificationOption.SECTOR_EXPOSURE,
        ClarificationOption.PORTFOLIO_OVERLAP,
    ),
}


UNSUPPORTED_CLAIM_PATTERNS = (
    "buy",
    "sell",
    "best fund",
    "suitable",
    "prediction",
    "will outperform",
    "tax advice",
    "regulatory advice",
    "caused returns",
)


class ClaimCheckRequest(BaseModel):
    input: str = Field(min_length=3, max_length=2_000)


class ResolvedEntity(BaseModel):
    input: str
    scheme_code: str | None = None
    scheme_name: str | None = None
    amc_name: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    resolution_status: str
    candidates: list[dict[str, Any]] = Field(default_factory=list)


class ClaimEvidence(BaseModel):
    source_type: str
    source_name: str
    source_url: str | None = None
    document_id: str | None = None
    as_of_date: str | None = None
    source_fingerprint: str | None = None


class ClaimClarification(BaseModel):
    reason: str
    prompt: str
    choices: list[ClarificationOption] = Field(min_length=1)


class AtomicClaim(BaseModel):
    statement: str
    metric: ClaimMetric | None = None
    operator: ClaimOperator | None = None
    status: ClaimStatus
    # A clarification is not a factual verdict. It remains unverifiable until
    # the user selects an objective, supported metric.
    verdict: ClaimVerdict = ClaimVerdict.UNVERIFIABLE
    freshness: ClaimFreshness = ClaimFreshness.UNKNOWN
    values: dict[str, Any] = Field(default_factory=dict)
    evidence: list[ClaimEvidence] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    clarification: ClaimClarification | None = None
    trackable: bool = False


class ClaimCheckResponse(BaseModel):
    input: str
    resolved_entities: list[ResolvedEntity] = Field(default_factory=list)
    claims: list[AtomicClaim] = Field(default_factory=list)
    generated_at: str


def needs_definition_claim(statement: str, term: str) -> AtomicClaim:
    """Create a safe result for a subjective term with no fixed metric."""
    normalized_term = str(term or "").strip().lower()
    choices = SUBJECTIVE_TERM_CLARIFICATIONS.get(normalized_term)
    if not choices:
        raise ValueError(f"No clarification contract is configured for {term!r}.")
    return AtomicClaim(
        statement=statement,
        status=ClaimStatus.CLARIFICATION_REQUIRED,
        verdict=ClaimVerdict.UNVERIFIABLE,
        freshness=ClaimFreshness.UNKNOWN,
        limitations=[f'"{normalized_term}" has no single objective fund metric.'],
        clarification=ClaimClarification(
            reason="metric_definition_required",
            prompt=f'Choose how to define "{normalized_term}" for this comparison.',
            choices=list(choices),
        ),
        trackable=False,
    )
