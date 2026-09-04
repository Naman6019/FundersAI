from app.mf_ingestion.constants import AMC_WEALTH_COMPANY
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class WealthCompanyAdapter(GenericPortfolioAdapter):
    amc_code = AMC_WEALTH_COMPANY
    scheme_markers = ("wealth company ", "the wealth company ")
