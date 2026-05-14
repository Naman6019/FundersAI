from __future__ import annotations

import pandas as pd
import pdfplumber


class PDFTableParser:
    def extract_tables(self, file_path: str) -> list[pd.DataFrame]:
        frames: list[pd.DataFrame] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables() or []
                for table in tables:
                    if not table:
                        continue
                    header = table[0]
                    rows = table[1:] if len(table) > 1 else []
                    df = pd.DataFrame(rows, columns=header)
                    df = df.dropna(how="all")
                    if not df.empty:
                        frames.append(df)
        return frames
