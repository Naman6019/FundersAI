from app.mf_ingestion.constants import AMC_KOTAK
from app.mf_ingestion.parsers.adapters.generic_portfolio_adapter import GenericPortfolioAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument
from app.mf_ingestion.parsers.combined_factsheet_portfolio import parse_combined_factsheet_pdf


class KotakAdapter(GenericPortfolioAdapter):
    amc_code = AMC_KOTAK
    scheme_markers = ("kotak ",)

    def parse_pdf_file_many(self, file_path: str, context: ParseContext) -> list[ParsedDocument]:
        return parse_combined_factsheet_pdf(
            file_path,
            context,
            scheme_prefixes=("kotak",),
            continue_after_grand_total=True,
        )
