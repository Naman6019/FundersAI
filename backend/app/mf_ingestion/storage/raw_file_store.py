from __future__ import annotations

from pathlib import Path

from app.mf_ingestion.downloaders.base_downloader import DownloadedDocument


class RawFileStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    def save(self, document: DownloadedDocument, checksum: str) -> str:
        ext = document.file_ext or _safe_extension(document.file_name)
        month_segment = document.report_month.isoformat() if document.report_month else "unknown-month"
        folder = self.root / document.amc_code / month_segment
        folder.mkdir(parents=True, exist_ok=True)

        file_name = f"{checksum}{ext}"
        file_path = folder / file_name
        if not file_path.exists():
            file_path.write_bytes(document.file_bytes)
        return str(file_path.resolve())


def _safe_extension(file_name: str) -> str:
    if "." not in file_name:
        return ".bin"
    return "." + file_name.rsplit(".", 1)[-1].lower()
