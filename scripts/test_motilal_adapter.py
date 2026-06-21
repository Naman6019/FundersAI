import os
import sys
from datetime import date
sys.path.append(os.path.abspath("backend"))

from app.mf_ingestion.parsers.excel_parser import ExcelParser
from app.mf_ingestion.parsers.adapters.motilal_adapter import MotilalAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext

mo_dir = os.path.abspath("data/mf_raw_docs/MO")
portfolio_path = os.path.join(mo_dir, "Scheme Portfolio Details 31-05-2026.xlsx")

excel_parser = ExcelParser()
frames = excel_parser.parse_all_sheets(portfolio_path)

adapter = MotilalAdapter()
context = ParseContext(source_document_id="test", source_url="", report_month=date(2026, 5, 1))

# Let's test parsing each frame individually since HoldingsParser does it frame by frame for Excel
for i, frame in enumerate(frames):
    parsed = adapter.parse_holdings([frame], [], "", context)
    if parsed.holdings:
        print(f"--- Sheet {i} parsed successfully ---")
        print(f"Scheme Name: {parsed.scheme_name}")
        print(f"Report Month: {parsed.report_month}")
        print(f"Total Percent AUM: {parsed.metrics.get('total_percent_aum')}")
        print(f"Holdings Count: {len(parsed.holdings)}")
        print(f"Warnings: {parsed.warnings}")
        print("First 3 holdings:")
        for h in parsed.holdings[:3]:
            print(f"  {h['instrument_name']} | {h['percent_aum']}% | {h['sector']} | {h['isin']}")
        print()
