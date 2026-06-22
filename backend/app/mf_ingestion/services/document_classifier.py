from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


SUPPORTED_PARSER_TYPES = {"factsheet", "ter_disclosure", "portfolio_disclosure"}
SUPPORTED_FILE_TYPES = {".pdf", ".xls", ".xlsx", ".xlsm", ".csv", ".zip", ".html", ".htm"}


@dataclass(frozen=True)
class DocumentClassification:
    amc_code: str
    document_type: str
    expected_file_type: str
    file_shape: str
    supported_parser: bool
    extractor_stage: str
    issues: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_raw_document(document: dict[str, Any], adapter_keys: set[str] | None = None) -> DocumentClassification:
    adapter_keys = adapter_keys or set()
    amc_code = str(document.get("amc_code") or "").strip().lower()
    document_type = str(document.get("document_type") or document.get("source_document_type") or "").strip().lower()
    expected_file_type = _document_extension(document)
    issues: list[str] = []

    if not amc_code:
        issues.append("amc_missing")
    if not document_type:
        issues.append("document_type_missing")
    elif document_type not in SUPPORTED_PARSER_TYPES:
        issues.append(f"unsupported_document_type:{document_type}")
    if expected_file_type and expected_file_type not in SUPPORTED_FILE_TYPES:
        issues.append(f"unsupported_file_type:{expected_file_type}")
    if document_type == "portfolio_disclosure" and amc_code and amc_code not in adapter_keys:
        issues.append(f"adapter_not_found:{amc_code}")

    return DocumentClassification(
        amc_code=amc_code,
        document_type=document_type,
        expected_file_type=expected_file_type,
        file_shape=_file_shape(expected_file_type),
        supported_parser=not issues,
        extractor_stage="classified",
        issues=issues,
    )


def _document_extension(document: dict[str, Any]) -> str:
    for key in ("file_ext", "file_name", "source_url", "storage_path", "storage_key"):
        raw = str(document.get(key) or "").strip()
        if not raw:
            continue
        suffix = Path(urlsplit(raw).path).suffix.lower()
        if suffix:
            return suffix
    return ""


def _file_shape(extension: str) -> str:
    if extension in {".xls", ".xlsx", ".xlsm", ".csv"}:
        return "tabular"
    if extension == ".pdf":
        return "pdf"
    if extension == ".zip":
        return "archive"
    if extension in {".html", ".htm"}:
        return "html"
    return "unknown"
