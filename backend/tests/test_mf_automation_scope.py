import pytest

from app.mf_ingestion.automation_scope import (
    APPROVED_RESTRICTED_AMCS,
    FROZEN_ISSUE_2_AMCS,
    GREEN_AMCS,
    VALIDATION_ONLY_AMCS,
    all_policy_amcs,
    resolve_automation_scope,
)
from app.mf_ingestion.sources.registry import SOURCES


def test_policy_is_a_disjoint_partition_of_registered_amcs():
    groups = [set(GREEN_AMCS), set(APPROVED_RESTRICTED_AMCS), set(VALIDATION_ONLY_AMCS), set(FROZEN_ISSUE_2_AMCS)]
    assert len(set().union(*groups)) == sum(len(group) for group in groups)
    assert set(all_policy_amcs()) == set(SOURCES)


def test_schedule_always_resolves_to_green_lane():
    assert resolve_automation_scope(
        operation="parser_retry",
        lane="approved_restricted",
        raw_amcs="nippon",
        event_name="schedule",
    ) == GREEN_AMCS


@pytest.mark.parametrize("amc", ["icici", "kotak"])
def test_issue_2_amcs_are_always_rejected(amc):
    with pytest.raises(ValueError, match="github_issue_2"):
        resolve_automation_scope(operation="parser_retry", raw_amcs=amc)


@pytest.mark.parametrize("amc", ["absl", "aditya_birla"])
def test_aditya_birla_was_unfrozen_after_the_family_merge_fix(amc):
    """aditya_birla (and its 'absl' alias) moved from FROZEN_ISSUE_2_AMCS to
    VALIDATION_ONLY_AMCS after the shared family-merge bug (GitHub issue #2) was fixed
    and its June 2026 promotion dry-run passed with zero internal/existing conflicts.
    icici and kotak remain frozen pending their own remaining conflicts."""
    resolved = resolve_automation_scope(
        operation="parser_retry",
        lane="validation_only",
        raw_amcs=amc,
        source_document_ids="doc-1",
    )
    assert resolved == ("aditya_birla",)


def test_restricted_and_validation_mutations_require_exact_document_ids():
    with pytest.raises(ValueError, match="source_document_ids_required"):
        resolve_automation_scope(operation="parser_retry", lane="approved_restricted", raw_amcs="nippon")
    with pytest.raises(ValueError, match="source_document_ids_required"):
        resolve_automation_scope(operation="disclosure_parse", lane="validation_only", raw_amcs="axis")

    assert resolve_automation_scope(
        operation="parser_retry",
        lane="approved_restricted",
        raw_amcs="nippon,uti",
        source_document_ids="doc-1,doc-2",
    ) == ("nippon", "uti")


def test_cross_lane_and_operation_requests_are_rejected():
    with pytest.raises(ValueError, match="amcs_not_in_green"):
        resolve_automation_scope(operation="discovery", raw_amcs="axis")
    with pytest.raises(ValueError, match="lane_not_allowed_for_research_index"):
        resolve_automation_scope(operation="research_index", lane="validation_only", raw_amcs="axis")
