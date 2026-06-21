from __future__ import annotations

import pandas as pd
import pdfplumber


class PDFTableParser:
    def extract_tables(self, file_path: str, page_numbers: list[int] | set[int] | None = None) -> list[pd.DataFrame]:
        frames: list[pd.DataFrame] = []
        selected_pages = {int(page) for page in page_numbers} if page_numbers else None

        import fitz
        fitz_doc = fitz.open(file_path)

        try:
            with pdfplumber.open(file_path) as pdf:
                for page_index, page in enumerate(pdf.pages):
                    if selected_pages is not None and int(page.page_number) not in selected_pages:
                        continue

                    fitz_page = fitz_doc[page_index]
                    page_text = fitz_page.get_text("text") or ""
                    page_text_head = "\n".join(page_text.splitlines()[:35])

                    page_words = page.extract_words(x_tolerance=1, y_tolerance=3) or []
                    tables = page.extract_tables() or []
                    if not tables:
                        df = pd.DataFrame()
                        df.attrs["page_number"] = page.page_number
                        df.attrs["page_text_head"] = page_text_head
                        df.attrs["page_text_full"] = page_text
                        df.attrs["page_words"] = page_words
                        frames.append(df)
                        continue

                    for table in tables:
                        if not table:
                            continue
                        df_raw = pd.DataFrame(table)
                        if df_raw.empty:
                            continue
                        header = df_raw.iloc[0].tolist()
                        df = df_raw.iloc[1:].copy()
                        df.columns = [str(c) if c is not None else "" for c in header]
                        df = df.dropna(how="all")
                        if not df.empty:
                            df.attrs["page_number"] = page.page_number
                            df.attrs["page_text_head"] = page_text_head
                            df.attrs["page_text_full"] = page_text
                            df.attrs["page_words"] = page_words
                            frames.append(df)
        finally:
            fitz_doc.close()

        return frames
