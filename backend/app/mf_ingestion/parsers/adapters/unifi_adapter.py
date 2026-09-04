from app.mf_ingestion.constants import AMC_UNIFI
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class UnifiAdapter(GenericPortfolioAdapter):
    amc_code = AMC_UNIFI
    scheme_markers = ("unifi ",)
