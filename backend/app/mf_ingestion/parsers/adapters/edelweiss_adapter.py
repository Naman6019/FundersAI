from app.mf_ingestion.constants import AMC_EDELWEISS
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class EdelweissAdapter(GenericPortfolioAdapter):
    amc_code = AMC_EDELWEISS
    scheme_markers = ("edelweiss ",)
