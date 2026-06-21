import os
import sys
from datetime import date
sys.path.append(os.path.abspath("backend"))

from app.mf_ingestion.parsers.factsheet_parser import FactsheetParser
from app.mf_ingestion.parsers.base_parser import ParseContext

mo_dir = os.path.abspath("data/mf_raw_docs/MO")
factsheet_path = os.path.join(mo_dir, "Factsheet May 2026 Active1.pdf")

parser = FactsheetParser()
context = ParseContext(source_document_id="test_fs", source_url="", report_month=date(2026, 5, 1))
records = parser.parse(factsheet_path, context)

print(f"Extracted {len(records)} schemes from factsheet.")
for r in records[:10]:
    print(f"Scheme: {r.scheme_name}")
    print(f"  AUM: {r.aum}")
    print(f"  TER: {r.expense_ratio}")
    print(f"  Benchmark: {r.benchmark}")
    print(f"  Manager: {r.fund_manager}")
    print(f"  Risk: {r.risk_level}")
    print(f"  Confidence: {r.confidence_score}")
    print("-" * 40)
