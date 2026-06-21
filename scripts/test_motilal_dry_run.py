import os
import sys
from datetime import date
sys.path.append(os.path.abspath("backend"))

import sys
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from app.mf_ingestion.parsers.holdings_parser import HoldingsParser
from app.mf_ingestion.parsers.adapters.motilal_adapter import MotilalAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext

mo_dir = os.path.abspath("data/mf_raw_docs/MO")
portfolio_path = os.path.join(mo_dir, "Scheme Portfolio Details 31-05-2026.xlsx")

print(f"Loading Motilal adapter and parsing Excel file...")
print(f"File: {portfolio_path}")

adapter = MotilalAdapter()
parser = HoldingsParser(adapter)
context = ParseContext(source_document_id="dry-run", source_url="", report_month=date(2026, 5, 1))

# Execute parse_many exactly how ParsingService invokes it
parsed_docs = parser.parse_many(portfolio_path, context)

print(f"\n✅ Successfully extracted {len(parsed_docs)} schemes from the Excel workbook!\n")

for i, doc in enumerate(parsed_docs[:5]):
    print(f"--- Scheme {i+1} ---")
    print(f"Name: {doc.scheme_name}")
    print(f"AUM Metrics: {doc.metrics}")
    print(f"Holdings Count: {len(doc.holdings)}")
    print(f"Warnings: {doc.warnings}")
    print("Top 3 Holdings:")
    for h in doc.holdings[:3]:
        print(f"  - {h['instrument_name']} | {h['percent_aum']}% | {h['sector']}")
    print("")

print(f"... and {len(parsed_docs) - 5} more schemes.")
