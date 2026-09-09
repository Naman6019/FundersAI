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
        raw_amcs="uti",
        event_name="schedule",
    ) == GREEN_AMCS


def test_no_amcs_remain_frozen_by_issue_2():
    """All three AMCs originally frozen by GitHub issue #2 (aditya_birla/absl, icici,
    kotak) had the shared family-merge bug fixed. icici and kotak each have their own
    residual, unrelated data question (icici: 10 families with a fresh vs. live
    risk_level disagreement; kotak: a holdings/portfolio-ISIN coverage shortfall) that
    the promotion job's own conflict gates already handle directly -- neither needs the
    blanket automation freeze anymore."""
    assert FROZEN_ISSUE_2_AMCS == ()


@pytest.mark.parametrize("amc", ["absl", "aditya_birla", "icici", "kotak", "hdfc", "axis", "motilal", "dsp", "nippon", "uti", "tata", "bandhan", "edelweiss", "invesco", "hsbc"])
def test_verified_amcs_are_in_the_green_lane(amc):
    """These AMCs' parser/mapping issues are resolved and their staging coverage passes
    cleanly, so they no longer need explicit source_document_ids for discovery/parsing.
    UTI's current official Active/Passive factsheets and consolidated portfolio ZIP
    were independently smoke-checked before it re-entered the scheduled lane."""
    resolved = resolve_automation_scope(operation="parser_retry", lane="green", raw_amcs=amc)
    assert resolved == (("aditya_birla",) if amc in ("absl", "aditya_birla") else (amc,))


def test_uti_no_longer_requires_manual_document_ids():
    assert resolve_automation_scope(
        operation="parser_retry",
        lane="green",
        raw_amcs="uti",
    ) == ("uti",)
    assert APPROVED_RESTRICTED_AMCS == ()


def test_cross_lane_and_operation_requests_are_rejected():
    with pytest.raises(ValueError, match="amcs_not_in_green"):
        resolve_automation_scope(operation="discovery", raw_amcs="franklin")
    with pytest.raises(ValueError, match="lane_not_allowed_for_research_index"):
        resolve_automation_scope(operation="research_index", lane="validation_only", raw_amcs="axis")
