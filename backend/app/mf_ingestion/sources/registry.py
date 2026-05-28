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
    ),
    "mirae": AMCDocumentSource(
        amc_name="Mirae Asset Mutual Fund",
        amc_code="MIRAE",
        adapter_key="mirae",
        factsheet_page_url=None,
        portfolio_disclosure_page_url=None,
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=False,
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
    ),
}


def normalize_amc_key(amc: str) -> str:
    return (amc or "").strip().lower()


def get_source(amc: str) -> AMCDocumentSource:
    key = normalize_amc_key(amc)
    source = SOURCES.get(key)
    if not source:
        raise ValueError(f"Unknown AMC key: {amc}")
    return source


def enabled_sources() -> list[AMCDocumentSource]:
    return [source for source in SOURCES.values() if source.enabled]
