from __future__ import annotations

from collections.abc import Iterable
from typing import Literal


AutomationLane = Literal["green", "approved_restricted", "validation_only"]
AutomationOperation = Literal["discovery", "parser_retry", "disclosure_parse", "research_index"]

GREEN_AMCS = (
    "ppfas", "sbi", "mirae", "hdfc", "axis", "nippon", "motilal", "dsp", "aditya_birla",
    "icici", "kotak",
)
# uti is the only AMC still held back from unattended discovery/parsing: its June
# promotion is on hold pending a human decision on stale source documents (not a code
# bug), so it must keep requiring explicit source_document_ids rather than running
# automatically. nippon, and then hdfc/axis/motilal/dsp/aditya_birla/icici/kotak (whose
# parser/mapping issues, including the GitHub issue #2 family-merge bug, are fixed),
# graduated to GREEN_AMCS once their staging coverage passed cleanly. Note this only
# widens unattended discovery/parsing/research-indexing into staging tables -- runtime
# promotion always stays a manual workflow_dispatch run with a typed approval phrase,
# regardless of lane, so icici's excluded risk scope (10 families need a manual
# riskometer-vs-PDF check) and kotak's excluded holdings/sectors scope (ISIN coverage
# shortfall) still can't reach production data unreviewed.
APPROVED_RESTRICTED_AMCS = ("uti",)
VALIDATION_ONLY_AMCS = ()
FROZEN_ISSUE_2_AMCS = ()

LANE_AMCS: dict[str, tuple[str, ...]] = {
    "green": GREEN_AMCS,
    "approved_restricted": APPROVED_RESTRICTED_AMCS,
    "validation_only": VALIDATION_ONLY_AMCS,
}
OPERATION_LANES: dict[str, frozenset[str]] = {
    "discovery": frozenset({"green", "validation_only"}),
    "parser_retry": frozenset({"green", "approved_restricted", "validation_only"}),
    "disclosure_parse": frozenset({"green", "validation_only"}),
    "research_index": frozenset({"green", "approved_restricted"}),
}
AMC_ALIASES = {
    "absl": "aditya_birla",
    "adityabirla": "aditya_birla",
    "aditya-birla": "aditya_birla",
}


def _tokens(values: str | Iterable[str] | None) -> tuple[str, ...]:
    raw_values = str(values or "").split(",") if isinstance(values, str) or values is None else values
    normalized: list[str] = []
    for raw in raw_values:
        value = str(raw or "").strip().lower().replace(" ", "_")
        value = AMC_ALIASES.get(value, value)
        if value and value not in normalized:
            normalized.append(value)
    return tuple(normalized)


def automation_amcs(lane: AutomationLane) -> tuple[str, ...]:
    try:
        return LANE_AMCS[lane]
    except KeyError as exc:
        raise ValueError(f"unknown_automation_lane:{lane}") from exc


def resolve_automation_scope(
    *,
    operation: AutomationOperation,
    lane: AutomationLane = "green",
    raw_amcs: str | Iterable[str] | None = None,
    event_name: str = "workflow_dispatch",
    source_document_ids: str | Iterable[str] | None = None,
) -> tuple[str, ...]:
    if operation not in OPERATION_LANES:
        raise ValueError(f"unknown_automation_operation:{operation}")

    if str(event_name or "").strip().lower() == "schedule":
        return GREEN_AMCS

    if lane not in OPERATION_LANES[operation]:
        raise ValueError(f"lane_not_allowed_for_{operation}:{lane}")

    requested = _tokens(raw_amcs)
    if not requested:
        if lane != "green":
            raise ValueError(f"explicit_amcs_required:{lane}")
        requested = GREEN_AMCS

    frozen = sorted(set(requested) & set(FROZEN_ISSUE_2_AMCS))
    if frozen:
        raise ValueError(f"amcs_frozen_by_github_issue_2:{','.join(frozen)}")

    allowed = set(automation_amcs(lane))
    invalid = sorted(set(requested) - allowed)
    if invalid:
        raise ValueError(f"amcs_not_in_{lane}:{','.join(invalid)}")

    document_ids = _tokens(source_document_ids)
    if lane in {"approved_restricted", "validation_only"} and operation != "discovery" and not document_ids:
        raise ValueError(f"source_document_ids_required:{lane}")
    return requested


def all_policy_amcs() -> tuple[str, ...]:
    return GREEN_AMCS + APPROVED_RESTRICTED_AMCS + VALIDATION_ONLY_AMCS + FROZEN_ISSUE_2_AMCS
