import os
import sys
sys.path.append(os.path.abspath("backend"))

from app.mf_ingestion.parsers.excel_parser import ExcelParser
from app.mf_ingestion.parsers.pdf_text_parser import PDFTextParser
from app.mf_ingestion.parsers.pdf_table_parser import PDFTableParser

mo_dir = os.path.abspath("data/mf_raw_docs/MO")
factsheet_path = os.path.join(mo_dir, "Factsheet May 2026 Active1.pdf")
portfolio_path = os.path.join(mo_dir, "Scheme Portfolio Details 31-05-2026.xlsx")

with open("motilal_test_output.txt", "w", encoding="utf-8") as f:
    f.write("--- EXCEL PORTFOLIO ---\n")
    excel_parser = ExcelParser()
    frames = excel_parser.parse_all_sheets(portfolio_path)
    for i, frame in enumerate(frames):
        f.write(f"Sheet {i} size: {frame.shape}\n")
        if frame.shape[0] > 0:
            f.write(frame.head(20).to_string() + "\n")
        f.write("-" * 40 + "\n")

    f.write("\n--- FACTSHEET TEXT ---\n")
    pdf_text_parser = PDFTextParser()
    text = pdf_text_parser.extract_text(factsheet_path)
    f.write(text[:3000] + "\n")
