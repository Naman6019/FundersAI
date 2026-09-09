from __future__ import annotations

from collections.abc import Iterable
from typing import Literal


AutomationLane = Literal["green", "approved_restricted", "validation_only"]
AutomationOperation = Literal["discovery", "parser_retry", "disclosure_parse", "research_index"]

GREEN_AMCS = (
    "ppfas", "sbi", "mirae", "hdfc", "axis", "nippon", "motilal", "dsp", "aditya_birla",
    "icici", "kotak", "uti", "tata", "bandhan", "edelweiss", "invesco", "hsbc",
    "quant", "canara_robeco", "groww", "zerodha",
    # Verified live discovery on official portals (September 2026):
    "baroda_bnp", "lic", "pgim", "quantum", "bajaj_finserv",
    "capitalmind", "abakkus", "unifi", "shriram", "helios",
    "old_bridge", "taurus", "angel_one", "jio_blackrock",
)
# UTI's official API now exposes current English Active/Passive Fund Watch PDFs and
# the matching consolidated portfolio ZIP. August 2026 factsheets and the July 2026
# portfolio were smoke-checked against their July body month before this graduation.
# As with every green AMC, unattended jobs only write staging tables. Runtime promotion
# remains a manual workflow_dispatch with a typed approval phrase, so incomplete or
# conflicting scopes cannot reach production data unreviewed.
APPROVED_RESTRICTED_AMCS: tuple[str, ...] = ()
# AMCs registered in sources & parsers but pending live discovery verification or
# document publication before graduation to unattended green staging:
VALIDATION_ONLY_AMCS = (
    "sundaram",
    "nj",
    "360_one",
    "navi",
    "boi",
    "choice",
    "wealth_company",
)
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
    "canara": "canara_robeco",
    "canararobeco": "canara_robeco",
    "canara-robeco": "canara_robeco",
    "baroda": "baroda_bnp",
    "licmf": "lic",
    "bajaj": "bajaj_finserv",
    "iifl": "360_one",
    "360one": "360_one",
    "bankofindia": "boi",
    "bank_of_india": "boi",
    "wealthcompany": "wealth_company",
    "jioblackrock": "jio_blackrock",
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
