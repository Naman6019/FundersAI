from app.mf_ingestion.constants import AMC_SHRIRAM
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class ShriramAdapter(GenericPortfolioAdapter):
    amc_code = AMC_SHRIRAM
    scheme_markers = ("shriram ",)
