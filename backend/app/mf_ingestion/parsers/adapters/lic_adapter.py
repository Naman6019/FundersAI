from app.mf_ingestion.constants import AMC_LIC
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class LICAdapter(GenericPortfolioAdapter):
    amc_code = AMC_LIC
    scheme_markers = ("lic mf ", "lic mutual fund")
