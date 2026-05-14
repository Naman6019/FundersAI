from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any


@dataclass
class ParseContext:
    source_document_id: str
    source_url: str
    report_month: date | None


@dataclass
class ParsedDocument:
    scheme_name: str
    report_month: date | None
    holdings: list[dict[str, Any]] = field(default_factory=list)
    metrics: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    confidence_score: float = 0.0


class BaseParser:
    def parse(self, file_path: str, context: ParseContext) -> ParsedDocument:
        raise NotImplementedError
