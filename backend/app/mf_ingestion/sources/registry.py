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
    # Some official scheme-factsheet listings expose current document URLs without a
    # report period. Acquisition may admit those only after the PDF body confirms the
    # requested month.
    factsheet_report_month_in_content_only: bool = False
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
        enabled=True,
        runtime_enabled=True,
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
        runtime_enabled=True,
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
            "https://www.kotakmf.com/Information/forms-and-downloads",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_KOTAK_PORTFOLIO_PAGE_URL",
            "https://www.kotakmf.com/Information/forms-and-downloads",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
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
        enabled=True,
        runtime_enabled=True,
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
        enabled=True,
        runtime_enabled=True,
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
        enabled=True,
        runtime_enabled=True,
        discovery_strategy="dsp_api",
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "disclosure"),
        excluded_keywords=("fortnightly", "half-yearly", "performance disclosure", "scheme performance"),
        allowed_host_suffixes=("dspim.com",),
    ),
    # These five sources were live-checked against current official July/August 2026
    # documents before joining the unattended staging lane. Discovery writes staging
    # evidence only; the separately approval-gated promotion workflow remains manual.
    "tata": AMCDocumentSource(
        amc_name="Tata Mutual Fund",
        amc_code="TATA",
        adapter_key="tata",
        factsheet_page_url=_env_url(
            "MF_TATA_FACTSHEET_PAGE_URL",
            "https://www.tatamutualfund.com/schemes-related/scheme-factsheet",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_TATA_PORTFOLIO_PAGE_URL",
            "https://www.tatamutualfund.com/schemes-related/portfolio",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet", "scheme factsheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "disclosure"),
        factsheet_contains_holdings=True,
        factsheet_report_month_in_content_only=True,
        allowed_host_suffixes=("tatamutualfund.com",),
    ),
    "bandhan": AMCDocumentSource(
        amc_name="Bandhan Mutual Fund",
        amc_code="BANDHAN",
        adapter_key="bandhan",
        factsheet_page_url=_env_url(
            "MF_BANDHAN_FACTSHEET_PAGE_URL",
            "https://bandhanmutual.com/downloads/factsheet/all-schemes",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_BANDHAN_PORTFOLIO_PAGE_URL",
            "https://bandhanmutual.com/downloads/portfolio-summary/monthly",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet", "monthly factsheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "disclosure"),
        factsheet_contains_holdings=True,
        browser_recovery_allowed=True,
        allowed_host_suffixes=("bandhanmutual.com",),
    ),
    "edelweiss": AMCDocumentSource(
        amc_name="Edelweiss Mutual Fund",
        amc_code="EDELWEISS",
        adapter_key="edelweiss",
        factsheet_page_url=_env_url(
            "MF_EDELWEISS_FACTSHEET_PAGE_URL",
            "https://www.edelweissmf.com/downloads/factsheets",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_EDELWEISS_PORTFOLIO_PAGE_URL",
            "https://www.edelweissmf.com/statutory/portfolio-of-schemes",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        discovery_strategy="edelweiss_monthly_portfolio_browser",
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "disclosure"),
        # Factsheets only expose Top 30 holdings. Use the monthly workbook for
        # complete holdings and sector allocation instead.
        factsheet_contains_holdings=False,
        browser_recovery_allowed=True,
        allowed_host_suffixes=("edelweissmf.com",),
    ),
    "invesco": AMCDocumentSource(
        amc_name="Invesco Mutual Fund",
        amc_code="INVESCO",
        adapter_key="invesco",
        factsheet_page_url=_env_url(
            "MF_INVESCO_FACTSHEET_PAGE_URL",
            "https://www.invescomutualfund.com/literature-forms/factsheets",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_INVESCO_PORTFOLIO_PAGE_URL",
            "https://www.invescomutualfund.com/literature-forms/monthly-holdings",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "holding", "holdings", "disclosure"),
        factsheet_contains_holdings=True,
        browser_recovery_allowed=True,
        allowed_host_suffixes=("invescomutualfund.com",),
    ),
    "hsbc": AMCDocumentSource(
        amc_name="HSBC Mutual Fund",
        amc_code="HSBC",
        adapter_key="hsbc",
        factsheet_page_url=_env_url(
            "MF_HSBC_FACTSHEET_PAGE_URL",
            "https://www.assetmanagement.hsbc.co.in/en/mutual-funds/investor-resources?Date=&Cap=&Doc=fund-factsheets",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_HSBC_PORTFOLIO_PAGE_URL",
            "https://www.assetmanagement.hsbc.co.in/en/mutual-funds/investor-resources?Date=&Cap=&Doc=monthly-portfolio-disclosures",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes="HSBC Mutual Fund serves direct PDF downloads without inline HTML previews.",
        enabled=True,
        runtime_enabled=True,
        # HSBC names its monthly factsheet "The Asset as on - <Month> <Year>" (slug
        # `the-asset-<month>-<year>.pdf`), so neither the title nor the URL contains
        # "factsheet" -- without "the asset" here the real document is filtered out and
        # discovery finds nothing. A bare "asset" keyword must NOT be added back: every
        # HSBC document URL contains "/assets/documents/", so it matched 4,336 of the
        # library's files against 75 for "the asset", which would burn the whole
        # discovery action budget on non-factsheets.
        factsheet_required_keywords=("factsheet", "fact sheet", "the asset"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "disclosure"),
        factsheet_contains_holdings=True,
        # The document library renders every document server-side into one ~12 MB HTML
        # page (its type/date filters are client-side only), so an earlier plain fetch
        # timed out on page weight rather than bot protection. Anchors are present in
        # the served HTML, so scraping works; browser recovery is retained only as a
        # fallback for that size-related fetch risk.
        browser_recovery_allowed=True,
        allowed_host_suffixes=("assetmanagement.hsbc.co.in", "hsbc.co.in"),
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
    "tata",
    "bandhan",
    "edelweiss",
    "invesco",
    "hsbc",
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
