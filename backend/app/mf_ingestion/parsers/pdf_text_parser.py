from __future__ import annotations

import fitz


class PDFTextParser:
    def extract_text(self, file_path: str) -> str:
        with fitz.open(file_path) as doc:
            return "\n".join(page.get_text("text") for page in doc)
