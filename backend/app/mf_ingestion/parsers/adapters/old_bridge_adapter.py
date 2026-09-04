from app.mf_ingestion.constants import AMC_OLD_BRIDGE
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class OldBridgeAdapter(GenericPortfolioAdapter):
    amc_code = AMC_OLD_BRIDGE
    scheme_markers = ("old bridge ", "oldbridge ")
