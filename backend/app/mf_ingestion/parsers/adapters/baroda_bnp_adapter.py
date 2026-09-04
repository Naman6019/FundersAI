from app.mf_ingestion.constants import AMC_BARODA_BNP
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class BarodaBNPAdapter(GenericPortfolioAdapter):
    amc_code = AMC_BARODA_BNP
    scheme_markers = ("baroda bnp paribas", "baroda bnp", "baroda pioneer")
