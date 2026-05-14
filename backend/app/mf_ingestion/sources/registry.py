from __future__ import annotations

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


SOURCES: dict[str, AMCDocumentSource] = {
    "ppfas": AMCDocumentSource(
        amc_name="Parag Parikh Mutual Fund",
        amc_code="PPFAS",
        adapter_key="ppfas",
        factsheet_page_url="https://amc.ppfas.com/downloads/index.php",
        portfolio_disclosure_page_url="https://amc.ppfas.com/statutory-disclosures/index.php",
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
        factsheet_page_url=None,
        portfolio_disclosure_page_url=None,
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=False,
    ),
    "icici": AMCDocumentSource(
        amc_name="ICICI Prudential Mutual Fund",
        amc_code="ICICI",
        adapter_key="icici",
        factsheet_page_url=None,
        portfolio_disclosure_page_url=None,
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=False,
    ),
    "sbi": AMCDocumentSource(
        amc_name="SBI Mutual Fund",
        amc_code="SBI",
        adapter_key="sbi",
        factsheet_page_url=None,
        portfolio_disclosure_page_url=None,
        requires_confirmation=False,
        confirmation_type=None,
        confirmation_notes=None,
        enabled=False,
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
