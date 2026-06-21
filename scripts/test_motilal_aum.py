import os
import sys
sys.path.append(os.path.abspath("backend"))

from app.mf_ingestion.parsers.pdf_text_parser import PDFTextParser
import re

mo_dir = os.path.abspath("data/mf_raw_docs/MO")
factsheet_path = os.path.join(mo_dir, "Factsheet May 2026 Active1.pdf")

parser = PDFTextParser()
text = parser.extract_text(factsheet_path)

aum_matches = re.finditer(r"(.{0,40})(AUM|Assets Under Management)(.{0,40})", text, re.IGNORECASE)
for i, match in enumerate(aum_matches):
    if i > 20: break
    print(match.group(0).replace('\n', ' '))
