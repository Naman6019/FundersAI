from app.mf_ingestion.constants import AMC_QUANT
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class QuantAdapter(GenericPortfolioAdapter):
    amc_code = AMC_QUANT
    scheme_markers = ("quant ",)
