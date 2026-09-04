from app.mf_ingestion.constants import AMC_SUNDARAM
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class SundaramAdapter(GenericPortfolioAdapter):
    amc_code = AMC_SUNDARAM
    scheme_markers = ("sundaram ",)
