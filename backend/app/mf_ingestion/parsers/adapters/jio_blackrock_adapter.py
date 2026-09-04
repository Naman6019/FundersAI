from app.mf_ingestion.constants import AMC_JIO_BLACKROCK
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class JioBlackRockAdapter(GenericPortfolioAdapter):
    amc_code = AMC_JIO_BLACKROCK
    scheme_markers = ("jio blackrock ", "jio black rock ")
