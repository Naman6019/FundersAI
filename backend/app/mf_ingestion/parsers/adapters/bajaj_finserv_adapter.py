from app.mf_ingestion.constants import AMC_BAJAJ_FINSERV
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class BajajFinservAdapter(GenericPortfolioAdapter):
    amc_code = AMC_BAJAJ_FINSERV
    scheme_markers = ("bajaj finserv ", "bajaj ")
