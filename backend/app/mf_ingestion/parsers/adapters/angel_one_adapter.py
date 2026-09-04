from app.mf_ingestion.constants import AMC_ANGEL_ONE
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class AngelOneAdapter(GenericPortfolioAdapter):
    amc_code = AMC_ANGEL_ONE
    scheme_markers = ("angel one ", "angel ")
