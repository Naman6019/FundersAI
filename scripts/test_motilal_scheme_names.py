import os
import sys
from datetime import date
sys.path.append(os.path.abspath("backend"))

from app.mf_ingestion.parsers.excel_parser import ExcelParser

mo_dir = os.path.abspath("data/mf_raw_docs/MO")
portfolio_path = os.path.join(mo_dir, "Scheme Portfolio Details 31-05-2026.xlsx")

excel_parser = ExcelParser()
frames = excel_parser.parse_all_sheets(portfolio_path)

with open("motilal_scheme_test.txt", "w", encoding="utf-8") as f:
    f.write("Sheet 1:\n")
    f.write(frames[1].head(15).to_string())
    f.write("\n\nSheet 84:\n")
    f.write(frames[84].head(15).to_string())
