from __future__ import annotations

import pytest

from app.mf_ingestion.agents.discovery_agent import AGENT_CLASSES, build_discovery_agent
from app.mf_ingestion.automation_scope import GREEN_AMCS, VALIDATION_ONLY_AMCS, resolve_automation_scope
from app.mf_ingestion.parsers.factsheet_parser import AMC_SCHEME_PREFIX_PATTERN, FACTSHEET_AMC_NAME_PREFIXES
from app.mf_ingestion.services.parsing_service import ParsingService
from app.mf_ingestion.sources.registry import PRODUCTION_TARGET_AMC_KEYS, SOURCES, get_source
from app.services.supported_amcs import (
    SUPPORTED_AMC_DISPLAY_NAMES,
    SUPPORTED_MF_AMC_MARKERS,
    UNSUPPORTED_MF_AMC_KEYWORDS,
    USER_FACING_SUPPORTED_AMCS,
    supported_amc_label_from_text,
)

VERY_LOW_AMCS = ("quant", "canara_robeco", "groww", "zerodha")

VERIFIED_LOW_AMCS = (
    "baroda_bnp", "lic", "pgim", "quantum", "bajaj_finserv",
    "capitalmind", "abakkus", "unifi", "shriram", "helios",
    "old_bridge", "taurus", "angel_one", "jio_blackrock",
)

VALIDATION_PENDING_AMCS = (
    "sundaram", "nj", "360_one", "navi", "boi", "choice", "wealth_company",
)

ALL_ONBOARDED_AMCS = VERY_LOW_AMCS + VERIFIED_LOW_AMCS + VALIDATION_PENDING_AMCS
ALL_GREEN_ONBOARDED = VERY_LOW_AMCS + VERIFIED_LOW_AMCS


def test_all_onboarded_amcs_are_registered_and_runtime_enabled():
    assert len(ALL_ONBOARDED_AMCS) == 25
    for amc in ALL_ONBOARDED_AMCS:
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


def test_all_onboarded_amcs_are_in_production_target_keys():
    assert set(ALL_ONBOARDED_AMCS).issubset(set(PRODUCTION_TARGET_AMC_KEYS))
    assert set(ALL_ONBOARDED_AMCS).issubset(set(SOURCES))


def test_verified_amcs_are_in_the_unattended_green_lane():
    assert set(ALL_GREEN_ONBOARDED).issubset(set(GREEN_AMCS))


def test_unverified_amcs_remain_in_validation_only_lane():
    assert set(VALIDATION_PENDING_AMCS).issubset(set(VALIDATION_ONLY_AMCS))


@pytest.mark.parametrize("amc", ALL_ONBOARDED_AMCS)
def test_discovery_agent_factory_builds_each_specialist(amc: str) -> None:
    agent = build_discovery_agent(amc)
    assert isinstance(agent, AGENT_CLASSES[amc])
    assert agent.source.adapter_key == amc


@pytest.mark.parametrize("amc", ALL_ONBOARDED_AMCS)
def test_parser_adapter_is_wired(amc: str) -> None:
    service = ParsingService()
    assert amc in service.adapters
    assert service.adapters[amc].amc_code == amc


@pytest.mark.parametrize("amc", ALL_GREEN_ONBOARDED)
def test_green_amcs_resolve_in_green_lane(amc: str) -> None:
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


@pytest.mark.parametrize("amc", VALIDATION_PENDING_AMCS)
def test_validation_only_amcs_resolve_in_validation_only_lane(amc: str) -> None:
    resolved = resolve_automation_scope(
        operation="discovery",
        lane="validation_only",
        raw_amcs=amc,
    )
    assert resolved == (amc,)


@pytest.mark.parametrize("alias,expected", [
    ("canara", "canara_robeco"),
    ("baroda", "baroda_bnp"),
    ("licmf", "lic"),
    ("bajaj", "bajaj_finserv"),
    ("iifl", "360_one"),
    ("360one", "360_one"),
    ("bankofindia", "boi"),
    ("bank_of_india", "boi"),
    ("wealthcompany", "wealth_company"),
    ("jioblackrock", "jio_blackrock"),
])
def test_amc_aliases_resolve_correctly(alias: str, expected: str):
    lane = "green" if expected in GREEN_AMCS else "validation_only"
    assert resolve_automation_scope(
        operation="discovery",
        lane=lane,
        raw_amcs=alias,
    ) == (expected,)


def test_green_amcs_resolve_on_scheduled_runs():
    scheduled = resolve_automation_scope(
        operation="disclosure_parse",
        event_name="schedule",
    )
    for amc in ALL_GREEN_ONBOARDED:
        assert amc in scheduled


@pytest.mark.parametrize("amc", ALL_ONBOARDED_AMCS)
def test_factsheet_parser_has_prefix_patterns(amc: str) -> None:
    assert amc in FACTSHEET_AMC_NAME_PREFIXES


def test_all_amcs_in_supported_amcs_catalog():
    for amc in ALL_ONBOARDED_AMCS:
        source = get_source(amc)
        code = source.amc_code
        assert code in SUPPORTED_MF_AMC_MARKERS
        assert code in USER_FACING_SUPPORTED_AMCS
        assert code in SUPPORTED_AMC_DISPLAY_NAMES
        assert not any(kw == amc.lower() for kw in UNSUPPORTED_MF_AMC_KEYWORDS)


@pytest.mark.parametrize("sample_text,expected_label", [
    ("Quant Small Cap Fund - Direct Plan", "QUANT"),
    ("Canara Robeco Emerging Equities Fund", "CANARA_ROBECO"),
    ("Groww Nifty Total Market Index Fund", "GROWW"),
    ("Zerodha Nifty LargeMidcap 250 Index Fund", "ZERODHA"),
    ("Baroda BNP Paribas Large Cap Fund", "BARODA_BNP"),
    ("LIC MF Infrastructure Fund", "LIC"),
    ("Sundaram Mid Cap Fund", "SUNDARAM"),
    ("PGIM India Flexi Cap Fund", "PGIM"),
    ("Quantum Long Term Equity Value Fund", "QUANTUM"),
    ("Bajaj Finserv Large and Mid Cap Fund", "BAJAJ_FINSERV"),
    ("Capitalmind Focused Fund", "CAPITALMIND"),
    ("Abakkus Emerging Opportunities Fund", "ABAKKUS"),
    ("Unifi Capital Focused Fund", "UNIFI"),
    ("Shriram Flexi Cap Fund", "SHRIRAM"),
    ("Helios Mid Cap Fund", "HELIOS"),
    ("NJ Balanced Advantage Fund", "NJ"),
    ("Old Bridge Flexi Cap Fund", "OLD_BRIDGE"),
    ("360 ONE Focused Equity Fund", "THREE_SIXTY_ONE"),
    ("Navi Nifty 50 Index Fund", "NAVI"),
    ("Taurus Discovery Midcap Fund", "TAURUS"),
    ("Angel One Nifty 1D Rate Liquid ETF", "ANGEL_ONE"),
    ("Bank of India Small Cap Fund", "BOI"),
    ("Choice Multi Asset Allocation Fund", "CHOICE"),
    ("The Wealth Company Dynamic Asset Fund", "WEALTH_COMPANY"),
    ("Jio BlackRock India Large Cap Fund", "JIO_BLACKROCK"),
])
def test_supported_amc_label_extraction(sample_text: str, expected_label: str):
    assert supported_amc_label_from_text(sample_text) == expected_label
