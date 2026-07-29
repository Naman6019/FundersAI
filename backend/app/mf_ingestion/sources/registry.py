from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class AMCDocumentSource:
    amc_name: str
    amc_code: str
    adapter_key: str
    factsheet_page_url: str | None
    portfolio_disclosure_page_url: str | None
    requires_confirmation: bool
    confirmation_type: str | None
    confirmation_notes: str | None
    enabled: bool = True
    discovery_enabled: bool = True
    acquisition_enabled: bool = True
    factsheet_parser_enabled: bool = True
    portfolio_parser_enabled: bool = True
    promotion_enabled: bool = True
    runtime_enabled: bool = False
    discovery_strategy: str = "generic"
    factsheet_required_keywords: tuple[str, ...] = ("factsheet", "fact sheet")
    portfolio_required_keywords: tuple[str, ...] = ("portfolio", "monthly portfolio", "disclosure")
    excluded_keywords: tuple[str, ...] = ()
    factsheet_extensions: tuple[str, ...] = (".pdf", ".html", ".htm")
    portfolio_extensions: tuple[str, ...] = (".pdf", ".xls", ".xlsx", ".xlsm", ".csv", ".zip")
    factsheet_contains_holdings: bool = False
    browser_recovery_allowed: bool = False
    allowed_host_suffixes: tuple[str, ...] = ()


def _env_url(name: str, default: str) -> str:
    value = os.getenv(name)
    if value is None:
        return default
    value = value.strip()
    return value or default


SOURCES: dict[str, AMCDocumentSource] = {
    "ppfas": AMCDocumentSource(
        amc_name="Parag Parikh Mutual Fund",
        amc_code="PPFAS",
        adapter_key="ppfas",
        factsheet_page_url=_env_url("MF_PPFAS_FACTSHEET_PAGE_URL", "https://amc.ppfas.com/downloads/index.php"),
        portfolio_disclosure_page_url=_env_url("MF_PPFAS_PORTFOLIO_PAGE_URL", "https://amc.ppfas.com/statutory-disclosures/index.php"),
        requires_confirmation=True,
        confirmation_type="indian_citizen_confirmation",
        confirmation_notes=(
            "Downloads and statutory disclosure pages may require confirming Indian citizen eligibility before access."
        ),
        enabled=True,
        runtime_enabled=True,
        discovery_strategy="ppfas_adapter",
        allowed_host_suffixes=("amc.ppfas.com", "ppfas.com"),
    ),
    "mirae": AMCDocumentSource(
        amc_name="Mirae Asset Mutual Fund",
        amc_code="MIRAE",
        adapter_key="mirae",
        factsheet_page_url=_env_url(
            "MF_MIRAE_FACTSHEET_PAGE_URL",
            "https://www.miraeassetmf.co.in/downloads/factsheet",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_MIRAE_PORTFOLIO_PAGE_URL",
            "https://www.miraeassetmf.co.in/downloads/portfolio",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=False,
        discovery_strategy="mirae_api",
        factsheet_required_keywords=("factsheet", "fact sheet", "active factsheet", "passive factsheet"),
        allowed_host_suffixes=("miraeassetmf.co.in",),
    ),
    "hdfc": AMCDocumentSource(
        amc_name="HDFC Mutual Fund",
        amc_code="HDFC",
        adapter_key="hdfc",
        factsheet_page_url=_env_url("MF_HDFC_FACTSHEET_PAGE_URL", "https://www.hdfcfund.com/mutual-funds/factsheets"),
        portfolio_disclosure_page_url=_env_url("MF_HDFC_PORTFOLIO_PAGE_URL", "https://www.hdfcfund.com/statutory-disclosure/portfolio/monthly-portfolio"),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet", "fund fact"),
        portfolio_required_keywords=("portfolio", "holding", "monthly portfolio", "monthly hdfc"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("hdfcfund.com",),
    ),
    "icici": AMCDocumentSource(
        amc_name="ICICI Prudential Mutual Fund",
        amc_code="ICICI",
        adapter_key="icici",
        factsheet_page_url=_env_url("MF_ICICI_FACTSHEET_PAGE_URL", "https://digitalfactsheet.icicipruamc.com/fact/index.php"),
        portfolio_disclosure_page_url=_env_url("MF_ICICI_PORTFOLIO_PAGE_URL", "https://www.icicipruamc.com/media-center/downloads"),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        discovery_strategy="icici_api",
        allowed_host_suffixes=("icicipruamc.com",),
    ),
    "sbi": AMCDocumentSource(
        amc_name="SBI Mutual Fund",
        amc_code="SBI",
        adapter_key="sbi",
        factsheet_page_url=_env_url("MF_SBI_FACTSHEET_PAGE_URL", "https://www.sbimf.com/factsheets"),
        portfolio_disclosure_page_url=_env_url("MF_SBI_PORTFOLIO_PAGE_URL", "https://www.sbimf.com/portfolios"),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        discovery_strategy="sbi_api",
        factsheet_required_keywords=("factsheet", "fact sheet", "fund fact", "scheme-factsheets"),
        portfolio_required_keywords=("portfolio", "holding", "monthly portfolio"),
        portfolio_extensions=(".xlsx", ".xls", ".xlsm", ".csv", ".zip"),
        allowed_host_suffixes=("sbimf.com",),
    ),
    "axis": AMCDocumentSource(
        amc_name="Axis Mutual Fund",
        amc_code="AXIS",
        adapter_key="axis",
        factsheet_page_url=_env_url("MF_AXIS_FACTSHEET_PAGE_URL", "https://www.axismf.com/downloads"),
        portfolio_disclosure_page_url=_env_url("MF_AXIS_PORTFOLIO_PAGE_URL", "https://www.axismf.com/downloads"),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        discovery_strategy="axis_adapter",
        factsheet_contains_holdings=True,
        browser_recovery_allowed=True,
        allowed_host_suffixes=("axismf.com",),
    ),
    "motilal": AMCDocumentSource(
        amc_name="Motilal Oswal Mutual Fund",
        amc_code="MOTILAL",
        adapter_key="motilal",
        factsheet_page_url=_env_url("MF_MOTILAL_FACTSHEET_PAGE_URL", "https://www.motilaloswalmf.com/downloads/factsheets"),
        portfolio_disclosure_page_url=_env_url("MF_MOTILAL_PORTFOLIO_PAGE_URL", "https://www.motilaloswalmf.com/downloads/scheme-portfolio-details"),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        discovery_strategy="motilal_aem_api",
        factsheet_contains_holdings=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("month end portfolio", "monthly portfolio", "portfolio"),
        excluded_keywords=(
            "fortnightly",
            "forthnightly",
            "half yearly",
            "half-yearly",
            "performance",
        ),
        allowed_host_suffixes=("motilaloswalmf.com",),
    ),
    "nippon": AMCDocumentSource(
        amc_name="Nippon India Mutual Fund",
        amc_code="NIPPON",
        adapter_key="nippon",
        factsheet_page_url=_env_url(
            "MF_NIPPON_FACTSHEET_PAGE_URL",
            "https://mf.nipponindiaim.com/investor-service/downloads/factsheet-portfolio-and-other-disclosures",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_NIPPON_PORTFOLIO_PAGE_URL",
            "https://mf.nipponindiaim.com/investor-service/downloads/factsheet-portfolio-and-other-disclosures",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fundamental", "fundamentals", "fund facts", "fund", "nippon"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "disclosure", "nippon"),
        excluded_keywords=("fortnightly",),
        allowed_host_suffixes=("nipponindiaim.com",),
    ),
    "kotak": AMCDocumentSource(
        amc_name="Kotak Mahindra Mutual Fund",
        amc_code="KOTAK",
        adapter_key="kotak",
        factsheet_page_url=_env_url(
            "MF_KOTAK_FACTSHEET_PAGE_URL",
            "https://www.kotakmf.com/factsheet/June_2026/",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_KOTAK_PORTFOLIO_PAGE_URL",
            "https://www.kotakmf.com/Information/forms-and-downloads",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=False,
        factsheet_contains_holdings=True,
        browser_recovery_allowed=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "disclosure"),
        allowed_host_suffixes=("kotakmf.com",),
    ),
    "aditya_birla": AMCDocumentSource(
        amc_name="Aditya Birla Sun Life Mutual Fund",
        amc_code="ABSL",
        adapter_key="aditya_birla",
        factsheet_page_url=_env_url(
            "MF_ABSL_FACTSHEET_PAGE_URL",
            "https://mutualfund.adityabirlacapital.com/forms-and-downloads/factsheets",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_ABSL_PORTFOLIO_PAGE_URL",
            "https://mutualfund.adityabirlacapital.com/forms-and-downloads/portfolio",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=False,
        discovery_strategy="absl_resources_api",
        factsheet_required_keywords=("factsheet", "monthly factsheet", "empower"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "disclosure"),
        excluded_keywords=("fortnightly", "half yearly", "half-yearly"),
        allowed_host_suffixes=("adityabirlacapital.com",),
    ),
    "uti": AMCDocumentSource(
        amc_name="UTI Mutual Fund",
        amc_code="UTI",
        adapter_key="uti",
        factsheet_page_url=_env_url(
            "MF_UTI_FACTSHEET_PAGE_URL",
            "https://www.utimf.com/downloads/fact-sheet",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_UTI_PORTFOLIO_PAGE_URL",
            "https://www.utimf.com/downloads",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=False,
        discovery_strategy="uti_api",
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "disclosure"),
        allowed_host_suffixes=("utimf.com",),
    ),
    "dsp": AMCDocumentSource(
        amc_name="DSP Mutual Fund",
        amc_code="DSP",
        adapter_key="dsp",
        factsheet_page_url=_env_url(
            "MF_DSP_FACTSHEET_PAGE_URL",
            "https://www.dspim.com/downloads?category=Information%20Documents&sub_category=Factsheets",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_DSP_PORTFOLIO_PAGE_URL",
            "https://www.dspim.com/mandatory-disclosures/portfolio-disclosures",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=False,
        discovery_strategy="dsp_api",
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "disclosure"),
        excluded_keywords=("fortnightly", "half-yearly", "performance disclosure", "scheme performance"),
        allowed_host_suffixes=("dspim.com",),
    ),
}

PRODUCTION_TARGET_AMC_KEYS = (
    "hdfc",
    "sbi",
    "icici",
    "axis",
    "ppfas",
    "nippon",
    "motilal",
    "mirae",
    "uti",
    "dsp",
    "kotak",
    "aditya_birla",
)


def normalize_amc_key(amc: str) -> str:
    return (amc or "").strip().lower()


def get_source(amc: str) -> AMCDocumentSource:
    key = normalize_amc_key(amc)
    source = SOURCES.get(key)
    if not source:
        raise ValueError(f"Unknown AMC key: {amc}")
    return source


def get_source_by_code(amc_code: str) -> AMCDocumentSource:
    normalized = str(amc_code or "").strip().lower()
    for source in SOURCES.values():
        if source.amc_code.lower() == normalized or source.adapter_key.lower() == normalized:
            return source
    raise ValueError(f"Unknown AMC code: {amc_code}")


def enabled_sources() -> list[AMCDocumentSource]:
    return [source for source in SOURCES.values() if source.enabled]


def sources_with_capability(capability: str) -> list[AMCDocumentSource]:
    if capability not in {
        "discovery_enabled",
        "acquisition_enabled",
        "factsheet_parser_enabled",
        "portfolio_parser_enabled",
        "promotion_enabled",
        "runtime_enabled",
    }:
        raise ValueError(f"Unknown AMC capability: {capability}")
    return [source for source in SOURCES.values() if bool(getattr(source, capability))]


def capability_keys(capability: str) -> tuple[str, ...]:
    return tuple(source.adapter_key for source in sources_with_capability(capability))
