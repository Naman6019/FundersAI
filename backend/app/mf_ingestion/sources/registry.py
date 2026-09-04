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
        factsheet_report_month_in_content_only=True,
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
        portfolio_required_keywords=(
            "portfolio",
            "monthly portfolio",
            "disclosure",
            "the asset",
        ),
        factsheet_contains_holdings=True,
        # The document library renders every document server-side into one ~12 MB HTML
        # page (its type/date filters are client-side only), so an earlier plain fetch
        # timed out on page weight rather than bot protection. Anchors are present in
        # the served HTML, so scraping works; browser recovery is retained only as a
        # fallback for that size-related fetch risk.
        browser_recovery_allowed=True,
        allowed_host_suffixes=("assetmanagement.hsbc.co.in", "hsbc.co.in"),
    ),
    "quant": AMCDocumentSource(
        amc_name="quant Mutual Fund",
        amc_code="QUANT",
        adapter_key="quant",
        factsheet_page_url=_env_url(
            "MF_QUANT_FACTSHEET_PAGE_URL",
            "https://quantmutual.com/downloads/factsheet",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_QUANT_PORTFOLIO_PAGE_URL",
            "https://quantmutual.com/statutory-disclosures",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "statutory"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("quantmutual.com",),
    ),
    "canara_robeco": AMCDocumentSource(
        amc_name="Canara Robeco Mutual Fund",
        amc_code="CANARA_ROBECO",
        adapter_key="canara_robeco",
        factsheet_page_url=_env_url(
            "MF_CANARA_ROBECO_FACTSHEET_PAGE_URL",
            "https://www.canararobeco.com/documents/forms-downloads/forms-information-documents/information-documents/factsheets/",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_CANARA_ROBECO_PORTFOLIO_PAGE_URL",
            "https://www.canararobeco.com/documents/statutory-disclosures/scheme-dashboard/scheme-monthly-portfolio/",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("canararobeco.com",),
    ),
    "groww": AMCDocumentSource(
        amc_name="Groww Mutual Fund",
        amc_code="GROWW",
        adapter_key="groww",
        factsheet_page_url=_env_url(
            "MF_GROWW_FACTSHEET_PAGE_URL",
            "https://www.growwmf.in/downloads/fact-sheet",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_GROWW_PORTFOLIO_PAGE_URL",
            "https://growwmf.in/statutory-disclosure/portfolio",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet", "monthly factsheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("growwmf.in", "assets-netstorage.growwmf.in"),
    ),
    "zerodha": AMCDocumentSource(
        amc_name="Zerodha Fund House",
        amc_code="ZERODHA",
        adapter_key="zerodha",
        factsheet_page_url=_env_url(
            "MF_ZERODHA_FACTSHEET_PAGE_URL",
            "https://www.zerodhafundhouse.com/resources/fund-documents",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_ZERODHA_PORTFOLIO_PAGE_URL",
            "https://www.zerodhafundhouse.com/resources/disclosures",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet", "fund document"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "disclosure"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("zerodhafundhouse.com", "assets.zerodhafundhouse.com"),
    ),
    "baroda_bnp": AMCDocumentSource(
        amc_name="Baroda BNP Paribas Mutual Fund",
        amc_code="BARODA_BNP",
        adapter_key="baroda_bnp",
        factsheet_page_url=_env_url(
            "MF_BARODA_BNP_FACTSHEET_PAGE_URL",
            "https://www.barodabnpparibasmf.in/downloads/monthly-factsheet",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_BARODA_BNP_PORTFOLIO_PAGE_URL",
            "https://www.barodabnpparibasmf.in/downloads/monthly-portfolio-scheme",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet", "fund facts"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "holding"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("barodabnpparibasmf.in",),
    ),
    "lic": AMCDocumentSource(
        amc_name="LIC Mutual Fund",
        amc_code="LIC",
        adapter_key="lic",
        factsheet_page_url=_env_url(
            "MF_LIC_FACTSHEET_PAGE_URL",
            "https://www.licmf.com/downloads/factsheet",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_LIC_PORTFOLIO_PAGE_URL",
            "https://www.licmf.com/downloads/monthly-portfolio",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet", "monthly factsheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "dashboard"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("licmf.com",),
    ),
    "sundaram": AMCDocumentSource(
        amc_name="Sundaram Mutual Fund",
        amc_code="SUNDARAM",
        adapter_key="sundaram",
        factsheet_page_url=_env_url(
            "MF_SUNDARAM_FACTSHEET_PAGE_URL",
            "https://www.sundarammutual.com/fundwise-factsheet",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_SUNDARAM_PORTFOLIO_PAGE_URL",
            "https://www.sundarammutual.com/Monthly-Fortnightly-Adhoc-Portfolios",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet", "digital factsheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("sundarammutual.com",),
    ),
    "pgim": AMCDocumentSource(
        amc_name="PGIM India Mutual Fund",
        amc_code="PGIM",
        adapter_key="pgim",
        factsheet_page_url=_env_url(
            "MF_PGIM_FACTSHEET_PAGE_URL",
            "https://www.pgimindia.com/mutual-funds/forms-and-updates/Fund-Factsheet",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_PGIM_PORTFOLIO_PAGE_URL",
            "https://www.pgimindia.com/mutual-funds/disclosures/Portfolios/Monthly-Portfolio",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "disclosure"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("pgimindia.com", "amfiindia.com"),
    ),
    "quantum": AMCDocumentSource(
        amc_name="Quantum Mutual Fund",
        amc_code="QUANTUM",
        adapter_key="quantum",
        factsheet_page_url=_env_url(
            "MF_QUANTUM_FACTSHEET_PAGE_URL",
            "https://www.quantumamc.com/factsheets/combined/-1/0/0",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_QUANTUM_PORTFOLIO_PAGE_URL",
            "https://www.quantumamc.com/FileCDN/FactSheet/5f6c4b6e-5264-472c-b378-d54727d45369.xlsx",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet", "combined", "all funds"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "factsheet"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("quantumamc.com",),
    ),
    "bajaj_finserv": AMCDocumentSource(
        amc_name="Bajaj Finserv Mutual Fund",
        amc_code="BAJAJ_FINSERV",
        adapter_key="bajaj_finserv",
        factsheet_page_url=_env_url(
            "MF_BAJAJ_FINSERV_FACTSHEET_PAGE_URL",
            "https://www.bajajamc.com/downloads?factsheet",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_BAJAJ_FINSERV_PORTFOLIO_PAGE_URL",
            "https://www.bajajamc.com/downloads?statutory-disclosures=",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "statutory"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("bajajamc.com", "media.bajajamc.com"),
    ),
    "capitalmind": AMCDocumentSource(
        amc_name="Capitalmind Mutual Fund",
        amc_code="CAPITALMIND",
        adapter_key="capitalmind",
        factsheet_page_url=_env_url(
            "MF_CAPITALMIND_FACTSHEET_PAGE_URL",
            "https://capitalmindmf.com/factsheet.html",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_CAPITALMIND_PORTFOLIO_PAGE_URL",
            "https://capitalmindmf.com/statutory-disclosures.html",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "product dashboard", "dashboard"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("capitalmindmf.com",),
    ),
    "abakkus": AMCDocumentSource(
        amc_name="Abakkus Mutual Fund",
        amc_code="ABAKKUS",
        adapter_key="abakkus",
        factsheet_page_url=_env_url(
            "MF_ABAKKUS_FACTSHEET_PAGE_URL",
            "https://www.abakkusmf.com/factsheet.html",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_ABAKKUS_PORTFOLIO_PAGE_URL",
            "https://www.abakkusmf.com/statutory-disclosures.html",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "half yearly"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("abakkusmf.com",),
    ),
    "unifi": AMCDocumentSource(
        amc_name="Unifi Mutual Fund",
        amc_code="UNIFI",
        adapter_key="unifi",
        factsheet_page_url=_env_url(
            "MF_UNIFI_FACTSHEET_PAGE_URL",
            "https://unifimf.com/factsheet/",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_UNIFI_PORTFOLIO_PAGE_URL",
            "https://unifimf.com/statutorydocuments/#monthly-portfolio-disclosure",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("unifimf.com",),
    ),
    "shriram": AMCDocumentSource(
        amc_name="Shriram Mutual Fund",
        amc_code="SHRIRAM",
        adapter_key="shriram",
        factsheet_page_url=_env_url(
            "MF_SHRIRAM_FACTSHEET_PAGE_URL",
            "https://www.shriramamc.in/factsheet",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_SHRIRAM_PORTFOLIO_PAGE_URL",
            "https://www.shriramamc.in/investor-statutory-disclosures",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "statutory"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("shriramamc.in", "cdn.shriramamc.in"),
    ),
    "helios": AMCDocumentSource(
        amc_name="Helios Mutual Fund",
        amc_code="HELIOS",
        adapter_key="helios",
        factsheet_page_url=_env_url(
            "MF_HELIOS_FACTSHEET_PAGE_URL",
            "https://www.heliosmf.in/downloads",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_HELIOS_PORTFOLIO_PAGE_URL",
            "https://www.heliosmf.in/portfolio-disclosure",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet", "downloads"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "fortnightly"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("heliosmf.in",),
    ),
    "nj": AMCDocumentSource(
        amc_name="NJ Mutual Fund",
        amc_code="NJ",
        adapter_key="nj",
        factsheet_page_url=_env_url(
            "MF_NJ_FACTSHEET_PAGE_URL",
            "https://downloads.njmutualfund.com/downloads.php",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_NJ_PORTFOLIO_PAGE_URL",
            "https://downloads.njmutualfund.com/njmf_download.php?nme=127",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("downloads.njmutualfund.com", "njmutualfund.com"),
    ),
    "old_bridge": AMCDocumentSource(
        amc_name="Old Bridge Mutual Fund",
        amc_code="OLD_BRIDGE",
        adapter_key="old_bridge",
        factsheet_page_url=_env_url(
            "MF_OLD_BRIDGE_FACTSHEET_PAGE_URL",
            "https://oldbridgemf.com/uploads/OLD_BRIDGE_MF_Factsheet_11305a79bc.pdf",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_OLD_BRIDGE_PORTFOLIO_PAGE_URL",
            "https://oldbridgemf.com/statutory-disclosures.html#v-pills-tabContent2",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "financials"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("oldbridgemf.com",),
    ),
    "360_one": AMCDocumentSource(
        amc_name="360 ONE Mutual Fund",
        amc_code="THREE_SIXTY_ONE",
        adapter_key="360_one",
        factsheet_page_url=_env_url(
            "MF_360_ONE_FACTSHEET_PAGE_URL",
            "https://www.360.one/asset/mutual-funds/downloads/",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_360_ONE_PORTFOLIO_PAGE_URL",
            "https://www.360.one/asset/mutual-funds/downloads/",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("360.one", "s3.ap-south-1.amazonaws.com"),
    ),
    "navi": AMCDocumentSource(
        amc_name="Navi Mutual Fund",
        amc_code="NAVI",
        adapter_key="navi",
        factsheet_page_url=_env_url(
            "MF_NAVI_FACTSHEET_PAGE_URL",
            "https://navi.com/mutual-fund/downloads/factsheet",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_NAVI_PORTFOLIO_PAGE_URL",
            "https://navi.com/mutual-fund/downloads/portfolio",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("navi.com", "navimutualfund.com"),
    ),
    "taurus": AMCDocumentSource(
        amc_name="Taurus Mutual Fund",
        amc_code="TAURUS",
        adapter_key="taurus",
        factsheet_page_url=_env_url(
            "MF_TAURUS_FACTSHEET_PAGE_URL",
            "https://www.taurusmutualfund.com/factsheet",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_TAURUS_PORTFOLIO_PAGE_URL",
            "https://taurusmutualfund.com/monthly-portfolio",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet", "one pager"),
        portfolio_required_keywords=("portfolio", "monthly portfolio"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("taurusmutualfund.com",),
    ),
    "angel_one": AMCDocumentSource(
        amc_name="Angel One Mutual Fund",
        amc_code="ANGEL_ONE",
        adapter_key="angel_one",
        factsheet_page_url=_env_url(
            "MF_ANGEL_ONE_FACTSHEET_PAGE_URL",
            "https://www.angelonemf.com/downloads",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_ANGEL_ONE_PORTFOLIO_PAGE_URL",
            "https://www.angelonemf.com/downloads",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "aaum"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("angelonemf.com", "cms.angelonemf.com"),
    ),
    "boi": AMCDocumentSource(
        amc_name="Bank of India Mutual Fund",
        amc_code="BOI",
        adapter_key="boi",
        factsheet_page_url=_env_url(
            "MF_BOI_FACTSHEET_PAGE_URL",
            "https://www.boimf.in/investor-corner",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_BOI_PORTFOLIO_PAGE_URL",
            "https://www.boimf.in/investor-corner#t2",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "report"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("boimf.in",),
    ),
    "choice": AMCDocumentSource(
        amc_name="Choice Mutual Fund",
        amc_code="CHOICE",
        adapter_key="choice",
        factsheet_page_url=_env_url(
            "MF_CHOICE_FACTSHEET_PAGE_URL",
            "https://choicemf.com/disclosures/factsheets",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_CHOICE_PORTFOLIO_PAGE_URL",
            "https://choicemf.com/disclosures/monthly-portfolio",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("choicemf.com",),
    ),
    "wealth_company": AMCDocumentSource(
        amc_name="The Wealth Company Mutual Fund",
        amc_code="WEALTH_COMPANY",
        adapter_key="wealth_company",
        factsheet_page_url=_env_url(
            "MF_WEALTH_COMPANY_FACTSHEET_PAGE_URL",
            "https://www.wealthcompanyamc.in/literature-forms/scheme-documents/factsheets/",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_WEALTH_COMPANY_PORTFOLIO_PAGE_URL",
            "https://www.wealthcompanyamc.in/literature-forms/portfolio-documents/monthly/",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("wealthcompanyamc.in",),
    ),
    "jio_blackrock": AMCDocumentSource(
        amc_name="Jio BlackRock Mutual Fund",
        amc_code="JIO_BLACKROCK",
        adapter_key="jio_blackrock",
        factsheet_page_url=_env_url(
            "MF_JIO_BLACKROCK_FACTSHEET_PAGE_URL",
            "https://www.jioblackrockamc.com/statutory-disclosure/fund-documents/factsheet",
        ),
        portfolio_disclosure_page_url=_env_url(
            "MF_JIO_BLACKROCK_PORTFOLIO_PAGE_URL",
            "https://www.jioblackrockamc.com/statutory-disclosure/disclosures/monthly-portfolio-disclosure",
        ),
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=True,
        runtime_enabled=True,
        factsheet_required_keywords=("factsheet", "fact sheet"),
        portfolio_required_keywords=("portfolio", "monthly portfolio", "disclosure"),
        factsheet_contains_holdings=True,
        allowed_host_suffixes=("jioblackrockamc.com", "azurefd.net"),
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
    "quant",
    "canara_robeco",
    "groww",
    "zerodha",
    "baroda_bnp",
    "lic",
    "sundaram",
    "pgim",
    "quantum",
    "bajaj_finserv",
    "capitalmind",
    "abakkus",
    "unifi",
    "shriram",
    "helios",
    "nj",
    "old_bridge",
    "360_one",
    "navi",
    "taurus",
    "angel_one",
    "boi",
    "choice",
    "wealth_company",
    "jio_blackrock",
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
