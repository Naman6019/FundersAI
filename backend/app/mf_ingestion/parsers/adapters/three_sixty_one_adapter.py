from app.mf_ingestion.constants import AMC_360_ONE
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class ThreeSixtyOneAdapter(GenericPortfolioAdapter):
    amc_code = AMC_360_ONE
    scheme_markers = ("360 one ", "iifl ")
