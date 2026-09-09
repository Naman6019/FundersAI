from app.mf_ingestion.constants import AMC_NJ
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class NJAdapter(GenericPortfolioAdapter):
    amc_code = AMC_NJ
    scheme_markers = ("nj ",)
