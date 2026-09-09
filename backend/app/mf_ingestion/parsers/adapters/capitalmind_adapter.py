from app.mf_ingestion.constants import AMC_CAPITALMIND
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter


class CapitalmindAdapter(GenericPortfolioAdapter):
    amc_code = AMC_CAPITALMIND
    scheme_markers = ("capitalmind ",)
    # "% to NAV" is published as a fraction of 1 (0.1018 means 10.18%), so without
    # this the whole portfolio staged at ~1% of AUM instead of ~100%.
    fractional_percent_cells = True
