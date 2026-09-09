from app.mf_ingestion.constants import AMC_ZERODHA
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class ZerodhaAdapter(GenericPortfolioAdapter):
    amc_code = AMC_ZERODHA
    scheme_markers = ("zerodha ",)
