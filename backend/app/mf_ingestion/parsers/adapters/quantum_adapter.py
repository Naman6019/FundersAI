from app.mf_ingestion.constants import AMC_QUANTUM
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class QuantumAdapter(GenericPortfolioAdapter):
    amc_code = AMC_QUANTUM
    scheme_markers = ("quantum ",)
