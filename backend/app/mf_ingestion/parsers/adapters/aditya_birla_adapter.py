from app.mf_ingestion.constants import AMC_ADITYA_BIRLA
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class AdityaBirlaAdapter(GenericPortfolioAdapter):
    amc_code = AMC_ADITYA_BIRLA
    scheme_markers = ("aditya birla", "birla sun life", "absl ")
