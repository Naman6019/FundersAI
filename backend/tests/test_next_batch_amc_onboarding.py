from __future__ import annotations

import inspect
from datetime import date
from pathlib import Path

import pytest

from app.mf_ingestion.agents.discovery_agent import AGENT_CLASSES, build_discovery_agent
from app.mf_ingestion.agents.validation import validate_candidate, validate_download
from app.mf_ingestion.automation_scope import GREEN_AMCS, VALIDATION_ONLY_AMCS, resolve_automation_scope
from app.mf_ingestion.downloaders import amc_downloader
from app.mf_ingestion.downloaders.base_downloader import (
    DiscoveredDocument,
    DownloadedDocument,
    local_file_sources_allowed,
)
from app.mf_ingestion.services.parsing_service import ParsingService
from app.mf_ingestion.sources.registry import PRODUCTION_TARGET_AMC_KEYS, SOURCES, get_source

NEXT_BATCH_AMCS = ("tata", "bandhan", "edelweiss", "invesco", "hsbc")

LOCAL_FILE_URL = "file:///C:/Users/example/Downloads/factsheet.pdf"


def test_next_batch_amcs_are_registered_and_runtime_enabled():
    for amc in NEXT_BATCH_AMCS:
        source = get_source(amc)
        assert source.enabled is True
        assert source.discovery_enabled is True
        assert source.acquisition_enabled is True
        assert source.factsheet_parser_enabled is True
        assert source.portfolio_parser_enabled is True
        assert source.runtime_enabled is True
        assert source.allowed_host_suffixes
        assert source.factsheet_required_keywords
        assert source.portfolio_required_keywords
        assert source.discovery_strategy


def test_next_batch_amcs_are_in_production_target_keys():
    assert set(NEXT_BATCH_AMCS).issubset(set(PRODUCTION_TARGET_AMC_KEYS))
    assert set(NEXT_BATCH_AMCS).issubset(set(SOURCES))


def test_next_batch_amcs_are_in_the_unattended_staging_lane():
    assert set(NEXT_BATCH_AMCS).issubset(set(GREEN_AMCS))
    assert VALIDATION_ONLY_AMCS == ()


@pytest.mark.parametrize("amc", NEXT_BATCH_AMCS)
def test_next_batch_discovery_agent_factory_builds_each_specialist(amc: str) -> None:
    agent = build_discovery_agent(amc)

    assert isinstance(agent, AGENT_CLASSES[amc])
    assert agent.source.adapter_key == amc


@pytest.mark.parametrize("amc", NEXT_BATCH_AMCS)
def test_next_batch_parser_adapter_is_wired(amc: str) -> None:
    service = ParsingService()

    assert amc in service.adapters
    assert service.adapters[amc].amc_code == amc


@pytest.mark.parametrize("amc", NEXT_BATCH_AMCS)
def test_next_batch_discovery_resolves_in_green_lane(amc: str) -> None:
    resolved = resolve_automation_scope(
        operation="discovery",
        lane="green",
        raw_amcs=amc,
    )
    assert resolved == (amc,)

    assert resolve_automation_scope(
        operation="parser_retry",
        lane="green",
        raw_amcs=amc,
    ) == (amc,)


def test_next_batch_amcs_resolve_on_scheduled_runs():
    scheduled = resolve_automation_scope(
        operation="disclosure_parse",
        event_name="schedule",
    )
    for amc in NEXT_BATCH_AMCS:
        assert amc in scheduled


@pytest.mark.parametrize("amc", NEXT_BATCH_AMCS)
def test_next_batch_factsheet_parser_has_prefix_patterns(amc: str) -> None:
    from app.mf_ingestion.parsers.factsheet_parser import AMC_SCHEME_PREFIX_PATTERN, FACTSHEET_AMC_NAME_PREFIXES
    assert amc.lower() in AMC_SCHEME_PREFIX_PATTERN.lower()
    assert amc in FACTSHEET_AMC_NAME_PREFIXES


def test_hsbc_factsheet_keywords_match_the_asset_without_matching_every_document():
    """HSBC names its monthly factsheet "The Asset as on - <Month> <Year>", so neither
    the title nor the slug contains "factsheet" -- "the asset" must stay in the keyword
    list or discovery silently finds nothing.

    The inverse trap matters just as much: keyword matching also runs against the URL,
    and every HSBC document URL contains "/assets/documents/", so a bare "asset" keyword
    matches the entire library (4,336 files against 75 for "the asset" when measured on
    the live page) and exhausts the discovery action budget on non-factsheets.
    """
    keywords = get_source("hsbc").factsheet_required_keywords

    assert "the asset" in keywords
    assert "asset" not in keywords

    real_factsheet = (
        "The Asset as on - June 2026 "
        "https://www.assetmanagement.hsbc.co.in/assets/documents/mutual-funds/en/"
        "5b15dfe0-604c-4ff5-a161-8073a9bbaae7/the-asset-june-2026.pdf"
    ).lower()
    unrelated = (
        "Corporate Deck - July 2026 "
        "https://www.assetmanagement.hsbc.co.in/assets/documents/mutual-funds/en/"
        "367ad50a-0292-46e8-80cc-347119e37524/corporate-deck-july-2026.pdf"
    ).lower()

    assert any(keyword in real_factsheet for keyword in keywords)
    assert not any(keyword in unrelated for keyword in keywords)


def _local_file_candidate() -> DiscoveredDocument:
    return DiscoveredDocument(
        amc_name="HSBC Mutual Fund",
        amc_code="HSBC",
        document_type="factsheet",
        title="Local factsheet",
        url=LOCAL_FILE_URL,
        discovery_page_url="https://www.assetmanagement.hsbc.co.in",
        file_ext=".pdf",
        report_month=date(2026, 6, 1),
        priority_score=1.0,
    )


def test_local_file_sources_are_rejected_by_default(monkeypatch):
    """A `file://` document has no official host and no reproducible provenance, so it
    must never be accepted just because it is readable on the machine running the job.
    This guards the pipeline's first non-negotiable rule (official sources only) for
    every AMC, not only the one being tested."""
    monkeypatch.delenv("MF_ALLOW_LOCAL_FILE_SOURCES", raising=False)

    assert local_file_sources_allowed() is False

    errors, _warnings = validate_candidate(
        get_source("hsbc"),
        _local_file_candidate(),
        expected_month=date(2026, 6, 1),
    )
    assert "local_file_source_not_allowed" in errors

    with pytest.raises(PermissionError, match="local_file_source_not_allowed"):
        amc_downloader._request_with_retry("GET", LOCAL_FILE_URL, timeout_seconds=1)


def test_local_file_candidate_and_download_validators_agree(monkeypatch):
    """The two validators must reach the same verdict. When they disagree a locally
    sourced document passes candidate validation and then fails at download, stranding
    it mid-pipeline instead of being rejected up front."""
    downloaded = DownloadedDocument(
        amc_name="HSBC Mutual Fund",
        amc_code="HSBC",
        document_type="factsheet",
        source_url=LOCAL_FILE_URL,
        discovery_page_url="https://www.assetmanagement.hsbc.co.in",
        file_name="factsheet.pdf",
        file_ext=".pdf",
        report_month=date(2026, 6, 1),
        content_type="application/pdf",
        file_size_bytes=5,
        file_bytes=b"%PDF-",
    )

    for enabled in ("", "true"):
        if enabled:
            monkeypatch.setenv("MF_ALLOW_LOCAL_FILE_SOURCES", enabled)
        else:
            monkeypatch.delenv("MF_ALLOW_LOCAL_FILE_SOURCES", raising=False)

        candidate_errors, _ = validate_candidate(
            get_source("hsbc"),
            _local_file_candidate(),
            expected_month=date(2026, 6, 1),
        )
        download_errors = validate_download(get_source("hsbc"), downloaded)

        blocked = "local_file_source_not_allowed"
        assert (blocked in candidate_errors) == (blocked in download_errors)


def test_discovery_helpers_carry_no_machine_specific_or_pinned_month_sources():
    """Discovery must stay live and reproducible. A developer-machine path returns zero
    documents in a hosted run -- indistinguishable from "not published yet" -- and a
    pinned month URL keeps re-injecting a stale document at maximum priority once that
    month passes, bypassing the stale-candidate ranking protections. A known-exact
    official URL belongs in the reviewed source manifest instead."""
    for helper in (
        amc_downloader._discover_hsbc_documents,
        amc_downloader._discover_invesco_documents,
    ):
        body = inspect.getsource(helper)
        code = body.split('"""')[-1] if '"""' in body else body
        assert "C:/Users" not in code and "C:\\Users" not in code
        assert "date(2026" not in code

    downloader_source = Path(
        "backend/app/mf_ingestion/downloaders/amc_downloader.py"
    ).read_text(encoding="utf-8")
    assert "C:/Users/naman" not in downloader_source

