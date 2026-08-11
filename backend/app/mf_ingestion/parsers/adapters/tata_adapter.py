from app.mf_ingestion.constants import AMC_TATA
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class TataAdapter(GenericPortfolioAdapter):
    amc_code = AMC_TATA
    scheme_markers = ("tata ",)
