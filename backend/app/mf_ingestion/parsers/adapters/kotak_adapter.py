from app.mf_ingestion.constants import AMC_KOTAK
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class KotakAdapter(GenericPortfolioAdapter):
    amc_code = AMC_KOTAK
    scheme_markers = ("kotak ",)
