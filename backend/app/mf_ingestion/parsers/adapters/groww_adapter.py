from app.mf_ingestion.constants import AMC_GROWW
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class GrowwAdapter(GenericPortfolioAdapter):
    amc_code = AMC_GROWW
    scheme_markers = ("groww ",)
