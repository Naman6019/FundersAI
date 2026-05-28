from __future__ import annotations

import pandas as pd
import pdfplumber


class PDFTableParser:
    def extract_tables(self, file_path: str, page_numbers: list[int] | set[int] | None = None) -> list[pd.DataFrame]:
        frames: list[pd.DataFrame] = []
        selected_pages = {int(page) for page in page_numbers} if page_numbers else None
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                if selected_pages is not None and int(page.page_number) not in selected_pages:
                    continue
                page_text = page.extract_text() or ""
                page_text_head = "\n".join(page_text.splitlines()[:35])
                page_words = page.extract_words(x_tolerance=1, y_tolerance=3) or []
                tables = page.extract_tables() or []
                for table in tables:
                    if not table:
                        continue
                    header = table[0]
                    rows = table[1:] if len(table) > 1 else []
                    df = pd.DataFrame(rows, columns=header)
                    df = df.dropna(how="all")
                    if not df.empty:
                        df.attrs["page_number"] = page.page_number
                        df.attrs["page_text_head"] = page_text_head
                        df.attrs["page_text_full"] = page_text
                        df.attrs["page_words"] = page_words
                        frames.append(df)
        return frames
