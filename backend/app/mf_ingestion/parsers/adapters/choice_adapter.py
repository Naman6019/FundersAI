from app.mf_ingestion.constants import AMC_CHOICE
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class ChoiceAdapter(GenericPortfolioAdapter):
    amc_code = AMC_CHOICE
    scheme_markers = ("choice ",)
