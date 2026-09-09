from app.mf_ingestion.constants import AMC_BOI
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class BOIAdapter(GenericPortfolioAdapter):
    amc_code = AMC_BOI
    scheme_markers = ("bank of india ", "boi ")
