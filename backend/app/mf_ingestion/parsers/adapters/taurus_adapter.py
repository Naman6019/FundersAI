from app.mf_ingestion.constants import AMC_TAURUS
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class TaurusAdapter(GenericPortfolioAdapter):
    amc_code = AMC_TAURUS
    scheme_markers = ("taurus ",)
