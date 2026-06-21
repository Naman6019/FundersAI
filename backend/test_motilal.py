import asyncio
from datetime import date

from app.mf_ingestion.parsers.adapters.motilal_adapter import MotilalAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext
from app.mf_ingestion.parsers.factsheet_parser import FactsheetParser
from app.mf_ingestion.parsers.holdings_parser import HoldingsParser

async def test_factsheet():
    print("--- Testing Factsheet ---")
    parser = FactsheetParser()
    context = ParseContext(source_document_id=1, source_url="", report_month=date(2026, 5, 1))
    records = parser.parse(r"..\data\mf_raw_docs\MO\Factsheet May 2026 Active1.pdf", context)
    print(f"Parsed {len(records)} schemes from factsheet.")
    for r in records[:2]:
        print(r)

async def test_holdings():
    print("\n--- Testing Holdings ---")
    context = ParseContext(source_document_id="mo_holdings_test", report_month=date(2026, 5, 31), source_url="test")
    parser = HoldingsParser(adapter=MotilalAdapter())
    docs = parser.parse_many(r"..\data\mf_raw_docs\MO\Scheme Portfolio Details 31-05-2026.xlsx", context)
    for doc in docs:
        print(f"Scheme: {doc.scheme_name} | Holdings: {len(doc.holdings)} | AUM %: {doc.metrics.get('total_percent_aum')} | Warns: {doc.warnings}")
    print(f"Total holdings records found: {len(docs)}")

if __name__ == "__main__":
    asyncio.run(test_factsheet())
    asyncio.run(test_holdings())
