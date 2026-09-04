from app.mf_ingestion.constants import AMC_NAVI
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class NaviAdapter(GenericPortfolioAdapter):
    amc_code = AMC_NAVI
    scheme_markers = ("navi ",)
