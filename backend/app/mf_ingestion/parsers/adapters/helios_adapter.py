from app.mf_ingestion.constants import AMC_HELIOS
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class HeliosAdapter(GenericPortfolioAdapter):
    amc_code = AMC_HELIOS
    scheme_markers = ("helios ",)
