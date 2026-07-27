from __future__ import annotations

import fitz


class PDFTextParser:
    def extract_pages(self, file_path: str) -> list[str]:
        with fitz.open(file_path) as doc:
            return [page.get_text("text") for page in doc]

    def extract_text(self, file_path: str) -> str:
        return "\n".join(self.extract_pages(file_path))
