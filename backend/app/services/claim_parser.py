"""Rules-first parser for the restricted Fund Truth Check claim language.

Phase 1 deliberately does not use a model. Input outside this small grammar is
clarified or rejected rather than guessed at.
"""
from __future__ import annotations

from dataclasses import dataclass
import re

from app.services.claim_check_contract import (
    ClaimMetric,
    ClaimOperator,
    SUBJECTIVE_TERM_CLARIFICATIONS,
)


@dataclass(frozen=True)
class ParsedClaim:
    statement: str
    metric: ClaimMetric | None
    operator: ClaimOperator | None
    entity_inputs: tuple[str, ...]
    subject_term: str | None = None
    target: str | None = None
    period_years: int | None = None
    unsupported_reason: str | None = None


_METRICS: tuple[tuple[ClaimMetric, re.Pattern[str]], ...] = (
    (ClaimMetric.EXPENSE_RATIO, re.compile(r"\b(expense ratios?|ter|cheaper|cost)\b", re.I)),
    (ClaimMetric.AUM, re.compile(r"\b(aum|assets? under management)\b", re.I)),
    (ClaimMetric.CAGR, re.compile(r"\bcagr\b", re.I)),
    (ClaimMetric.ROLLING_RETURN, re.compile(r"\b(rolling returns?|returns?|outperform(?:ed|s|ing)?)\b", re.I)),
    (ClaimMetric.SHARPE_RATIO, re.compile(r"\bsharpe\b", re.I)),
    (ClaimMetric.MAX_DRAWDOWN, re.compile(r"\b(drawdowns?|maximum drawdown|max drawdown)\b", re.I)),
    (ClaimMetric.VOLATILITY, re.compile(r"\b(volatility|volatile)\b", re.I)),
    (ClaimMetric.RISKOMETER, re.compile(r"\b(riskometer|risk label)\b", re.I)),
    (ClaimMetric.BENCHMARK, re.compile(r"\bbenchmark\b", re.I)),
    (ClaimMetric.FUND_MANAGER, re.compile(r"\b(fund manager|manager|manages?|managed by)\b", re.I)),
    (ClaimMetric.HOLDS_STOCK, re.compile(r"\b(holds?|holdings? (?:include|contains?))\b", re.I)),
    (ClaimMetric.STOCK_EXPOSURE, re.compile(r"\b(stock exposure|exposure to|holds?\s+more)\b", re.I)),
    (ClaimMetric.SECTOR_EXPOSURE, re.compile(r"\b(sector exposure|sector allocation|sector|[a-z]+(?:-[a-z]+)+\s+exposure)\b", re.I)),
    (ClaimMetric.HOLDINGS_CONCENTRATION, re.compile(r"\b(concentration|concentrated|top \d+ holdings?)\b", re.I)),
    (ClaimMetric.PORTFOLIO_OVERLAP, re.compile(r"\b(overlap|common holdings?)\b", re.I)),
    (ClaimMetric.INVESTMENT_OBJECTIVE, re.compile(r"\b(investment objective|objective|mandate)\b", re.I)),
)
_COMPARISON = re.compile(
    r"^\s*(?P<left>.+?)\s+(?:is|are|has|have|had|holds?)\s+.+?\s+than\s+(?P<right>.+?)\s*[?.!]?\s*$",
    re.I,
)
_BETWEEN = re.compile(r"\bbetween\s+(?P<left>.+?)\s+(?:and|vs\.?|versus)\s+(?P<right>.+?)\s*[?.!]?\s*$", re.I)
_SINGLE_HOLDING = re.compile(r"^\s*(?:does\s+)?(?P<entity>.+?)\s+(?:hold|holds|have|has)\s+(?P<target>.+?)\s*[?.!]?\s*$", re.I)
_SINGLE_EXPOSURE = re.compile(
    r"^\s*(?P<entity>.+?)\s+(?:has|have|had|is)\s+(?:\d+(?:\.\d+)?%\s+)?(?:stock\s+|sector\s+)?exposure\s+(?:to|in)\s+(?P<target>.+?)\s*[?.!]?\s*$",
    re.I,
)
_EXPOSURE_TARGET = re.compile(r"\b(?:exposure\s+to|sector\s+(?:exposure\s+)?(?:to|in))\s+(?P<target>.+?)\s*[?.!]?\s*$", re.I)
_UNSUPPORTED_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(?:will|going\s+to|next\s+(?:day|week|month|quarter|year))\b", re.I), "Forward-looking predictions are unsupported."),
    (re.compile(r"\bguarantee(?:d|s|ing)?\b", re.I), "Guaranteed-return claims are unsupported."),
    (re.compile(r"\b(?:cause[ds]?|causing|causal|led\s+to|because\s+of|due\s+to|responsible\s+for)\b", re.I), "Causal return attribution is unsupported."),
    (re.compile(r"\b(?:should\s+i|should\s+we|recommend(?:ed|ation)?|advice)\b", re.I), "Investment decisions and personal advice are unsupported."),
    (re.compile(r"\b(?:buy|sell)\b", re.I), "Buy or sell decisions are unsupported."),
    (re.compile(r"\bbest\b", re.I), "Best-fund rankings are unsupported."),
    (re.compile(r"\bsuitab(?:le|ility)\b", re.I), "Personal suitability is unsupported."),
    (re.compile(r"\b(?:tax|taxation)\b", re.I), "Tax advice is unsupported."),
    (re.compile(r"\b(?:regulatory|regulation|sebi\s+compliant|compliant\s+with)\b", re.I), "Regulatory advice is unsupported."),
    (re.compile(r"\b(?:my|our)\s+(?:savings|retirement|portfolio|allocation)\b", re.I), "Personal allocation decisions are unsupported."),
    (re.compile(r"\bprediction\b", re.I), "Predictions are unsupported."),
)


def _clean(value: str) -> str:
    normalized = re.sub(r"\s+", " ", value).strip(" ,.:;?!")
    return re.sub(r"(?:'s|’s)$", "", normalized, flags=re.I).strip()


_TRAILING_CONTEXT = re.compile(
    r"\s+(?:by\s+(?:aum|assets? under management|expense ratios?|sharpe ratios?|maximum drawdown|volatility)"
    r"|according\s+to\b.*|in\s+(?:the\s+)?(?:old|latest|current)\s+factsheet\b.*)$",
    re.I,
)
_TRAILING_METRIC = re.compile(
    r"\s+(?:expense ratios?|aum|assets? under management|cagr|sharpe ratios?|maximum drawdown|"
    r"max drawdown|volatility|riskometers?|risk labels?|benchmarks?|fund managers?|investment objectives?)$",
    re.I,
)


def _entity(value: str) -> str:
    cleaned = _clean(value)
    cleaned = _TRAILING_CONTEXT.sub("", cleaned)
    cleaned = _TRAILING_METRIC.sub("", cleaned)
    return _clean(cleaned)


def _comparison_entities(statement: str) -> tuple[str, ...]:
    text = statement.strip().rstrip("?.!")

    same = re.match(r"^(?:is|are)\s+(?P<left>.+?)\s+(?:the\s+)?same\s+as\s+(?P<right>.+)$", text, re.I)
    if same:
        return (_entity(same.group("left")), _entity(same.group("right")))

    leading = re.match(
        r"^(?:is|are|does|do|did|has|have|had|was|were)\s+(?P<left>.+?)\s+"
        r"(?:(?:have|has|had|show|shows)\s+)?(?:a\s+|the\s+)?"
        r"(?:lower|higher|greater|more|less|larger|smaller|cheaper|better|worse|different|volatile|concentrated)\b.*?\s+than\s+(?P<right>.+)$",
        text,
        re.I,
    )
    if leading:
        return (_entity(leading.group("left")), _entity(leading.group("right")))

    for pattern in (_COMPARISON, _BETWEEN):
        match = pattern.search(text)
        if match:
            return (_entity(match.group("left")), _entity(match.group("right")))
    return ()


def _compare_command_entities(statement: str) -> tuple[str, ...]:
    match = re.match(r"^\s*compare\s+(?P<body>.+?)\s*[?.!]?\s*$", statement, re.I)
    if not match:
        return ()
    body = _clean(match.group("body"))
    body = re.sub(
        r"^(?:the\s+)?(?:[135]\s*[- ]?\s*(?:year|yr)s?\s+)?"
        r"(?:expense ratio|aum|assets? under management|cagr|rolling returns?|sharpe ratio|maximum drawdown|"
        r"volatility|riskometer|benchmark|fund manager|investment objective)s?\s+of\s+",
        "",
        body,
        flags=re.I,
    )
    body = _TRAILING_CONTEXT.sub("", body)
    body = _TRAILING_METRIC.sub("", body)
    parts = [_entity(item) for item in re.split(r"\s*(?:,|\band\b|\bwith\b|\bvs\.?\b|\bversus\b)\s*", body, flags=re.I)]
    parts = [item for item in parts if item]
    if len(parts) == 2 and re.fullmatch(r"(?:direct|regular)(?:\s+(?:growth|idcw))?", parts[1], re.I):
        base = re.sub(r"\s+(?:direct|regular)(?:\s+(?:growth|idcw))?$", "", parts[0], flags=re.I)
        parts[1] = f"{base} {parts[1]}"
    return tuple(parts)


def _entities(statement: str) -> tuple[str, ...]:
    comparison = _comparison_entities(statement)
    if comparison:
        return tuple(item for item in comparison if item)
    command = _compare_command_entities(statement)
    if command:
        return command
    choice = re.match(r"^\s*which\b.+?,\s*(?P<left>.+?)\s+(?:or|vs\.?|versus)\s+(?P<right>.+?)\s*[?.!]?\s*$", statement, re.I)
    if choice:
        return (_entity(choice.group("left")), _entity(choice.group("right")))
    paired_fact = re.match(
        r"^\s*(?:do|does|did)\s+(?P<left>.+?)\s+and\s+(?P<right>.+?)\s+"
        r"(?:have|share|use|track)\b.+?[?.!]?\s*$",
        statement,
        re.I,
    )
    if paired_fact:
        return (_entity(paired_fact.group("left")), _entity(paired_fact.group("right")))
    manager = re.match(r"^\s*who\s+manages\s+(?P<entity>.+?)\s*[?.!]?\s*$", statement, re.I)
    if manager:
        return (_entity(manager.group("entity")),)
    lookup = re.match(
        r"^\s*what(?:'s|\s+is)\s+(?:the\s+)?(?:expense ratio|aum|assets? under management|benchmark|"
        r"riskometer|risk label|fund manager|manager|investment objective|objective|mandate)\s+of\s+(?P<entity>.+?)\s*[?.!]?\s*$",
        statement,
        re.I,
    )
    if lookup:
        return (_entity(lookup.group("entity")),)
    match = _SINGLE_HOLDING.match(statement)
    if match:
        entity = _entity(match.group("entity"))
        return (entity,) if entity else ()
    match = _SINGLE_EXPOSURE.match(statement)
    if match:
        entity = _entity(match.group("entity"))
        return (entity,) if entity else ()
    match = re.match(
        r"^\s*(?:what(?:'s| is)|is|does|show)?\s*(?P<entity>.+?)\s+(?:benchmark|riskometer|risk label|fund manager|manager|investment objective|objective)\b",
        statement,
        re.I,
    )
    if match:
        entity = _entity(match.group("entity"))
        return (entity,) if entity else ()
    return ()


def _period_years(statement: str, metric: ClaimMetric) -> int | None:
    match = re.search(r"\b([135])\s*[- ]?\s*(?:year|yr)s?\b", statement, re.I)
    if match:
        return int(match.group(1))
    return 3 if metric in {ClaimMetric.CAGR, ClaimMetric.ROLLING_RETURN} else None


def _operator(statement: str, metric: ClaimMetric) -> ClaimOperator:
    lowered = statement.lower()
    if re.search(r"\b(?:same|equal)\b", lowered):
        return ClaimOperator.EQUAL_TO
    if re.search(r"\bdifferent\b", lowered):
        return ClaimOperator.DIFFERENT_FROM
    if metric is ClaimMetric.STOCK_EXPOSURE and re.search(r"\bholds?\s+more\b", lowered):
        return ClaimOperator.HIGHER_THAN
    if metric is ClaimMetric.SECTOR_EXPOSURE and re.search(r"\b(?:greater|higher|more)\b.+\bexposure\b", lowered):
        return ClaimOperator.HIGHER_THAN
    if any(token in lowered for token in ("lower", "less", "cheaper", "smaller", "fewer")):
        return ClaimOperator.LOWER_THAN
    if any(token in lowered for token in ("higher", "more", "larger", "greater", "outperform", "better")):
        return ClaimOperator.HIGHER_THAN
    if metric in {ClaimMetric.HOLDS_STOCK, ClaimMetric.STOCK_EXPOSURE, ClaimMetric.SECTOR_EXPOSURE}:
        return ClaimOperator.CONTAINS
    if metric in {ClaimMetric.BENCHMARK, ClaimMetric.RISKOMETER, ClaimMetric.FUND_MANAGER, ClaimMetric.INVESTMENT_OBJECTIVE}:
        return ClaimOperator.IS
    return ClaimOperator.IS


def _target(statement: str, metric: ClaimMetric) -> str | None:
    if metric is ClaimMetric.HOLDS_STOCK:
        match = _SINGLE_HOLDING.match(statement)
        return _clean(match.group("target")) if match else None
    if metric in {ClaimMetric.STOCK_EXPOSURE, ClaimMetric.SECTOR_EXPOSURE}:
        holding_comparison = re.search(r"\bholds?\s+more\s+(?P<target>.+?)\s+than\b", statement, re.I)
        if holding_comparison:
            return _clean(holding_comparison.group("target"))
        named_exposure = re.search(
            r"\b(?:greater|higher|more|lower|less)\s+(?P<target>[a-z]+(?:-[a-z]+)+)\s+exposure\s+than\b",
            statement,
            re.I,
        )
        if named_exposure:
            return _clean(named_exposure.group("target").replace("-", " ")).title()
        match = _SINGLE_EXPOSURE.match(statement)
        if match:
            return _clean(match.group("target"))
        match = _EXPOSURE_TARGET.search(statement)
        if match:
            return _clean(re.split(r"\s+than\s+", match.group("target"), maxsplit=1, flags=re.I)[0])
        return None
    return None


class ClaimParser:
    """Parse only the reviewable Phase 1 claim vocabulary."""

    def parse(self, statement: str) -> list[ParsedClaim]:
        normalized = " ".join(str(statement or "").split())
        if not normalized:
            return []
        lowered = normalized.lower()
        for pattern, reason in _UNSUPPORTED_RULES:
            if pattern.search(normalized):
                return [ParsedClaim(normalized, None, None, (), unsupported_reason=reason)]

        entities = _entities(normalized)
        parsed: list[ParsedClaim] = []
        for term in SUBJECTIVE_TERM_CLARIFICATIONS:
            if re.search(rf"\b{re.escape(term)}\b", lowered):
                parsed.append(ParsedClaim(normalized, None, None, entities, subject_term=term))
        for metric, pattern in _METRICS:
            if metric is ClaimMetric.STOCK_EXPOSURE and "sector exposure" in lowered:
                continue
            if metric is ClaimMetric.HOLDS_STOCK and re.search(r"\bholds?\s+more\b", lowered):
                continue
            if pattern.search(normalized):
                parsed.append(ParsedClaim(
                    normalized,
                    metric,
                    _operator(normalized, metric),
                    entities,
                    target=_target(normalized, metric),
                    period_years=_period_years(normalized, metric),
                ))
        if parsed:
            return parsed
        if entities:
            return [ParsedClaim(normalized, None, None, entities)]
        return [ParsedClaim(normalized, None, None, (), unsupported_reason="The statement is outside the reviewed Phase 1 claim grammar.")]
