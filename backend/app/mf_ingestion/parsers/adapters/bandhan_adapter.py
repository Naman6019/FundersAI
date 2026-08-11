from app.mf_ingestion.constants import AMC_BANDHAN
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class BandhanAdapter(GenericPortfolioAdapter):
    amc_code = AMC_BANDHAN
    scheme_markers = ("bandhan ",)
