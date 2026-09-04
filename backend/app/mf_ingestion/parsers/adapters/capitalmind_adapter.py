from app.mf_ingestion.constants import AMC_CAPITALMIND
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class CapitalmindAdapter(GenericPortfolioAdapter):
    amc_code = AMC_CAPITALMIND
    scheme_markers = ("capitalmind ",)
