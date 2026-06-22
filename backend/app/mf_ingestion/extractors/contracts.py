from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


NORMALIZED_EXTRACTION_KEYS = {
    "scheme_name",
    "report_month",
    "holdings",
    "aum",
    "expense_ratio",
    "benchmark",
    "fund_manager",
    "risk_level",
    "source_document_id",
    "extractor_type",
    "confidence_score",
    "validation_issues",
}


@dataclass(frozen=True)
class NormalizedExtractionRecord:
    scheme_name: str
    report_month: str | None
    holdings: list[dict[str, Any]] = field(default_factory=list)
    aum: float | None = None
    expense_ratio: float | None = None
    benchmark: str | None = None
    fund_manager: str | None = None
    risk_level: str | None = None
    confidence_score: float = 0.0
    validation_issues: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedExtraction:
    source_document_id: str
    extractor_type: str
    records: list[NormalizedExtractionRecord] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def parse_normalized_extraction(payload: dict[str, Any]) -> NormalizedExtraction:
    if not isinstance(payload, dict):
        raise ValueError("normalized_extraction_not_object")

    unknown = set(payload) - NORMALIZED_EXTRACTION_KEYS
    if unknown and unknown != {"records"}:
        raise ValueError(f"normalized_extraction_unknown_keys:{','.join(sorted(unknown))}")

    source_document_id = str(payload.get("source_document_id") or "").strip()
    extractor_type = str(payload.get("extractor_type") or "").strip()
    if not source_document_id:
        raise ValueError("normalized_extraction_source_document_id_missing")
    if extractor_type not in {"deterministic", "llm"}:
        raise ValueError("normalized_extraction_extractor_type_invalid")

    raw_records = payload.get("records")
    if raw_records is None:
        raw_records = [payload]
    if not isinstance(raw_records, list):
        raise ValueError("normalized_extraction_records_not_list")

    records = [_parse_record(row) for row in raw_records]
    if not records:
        raise ValueError("normalized_extraction_records_empty")

    return NormalizedExtraction(
        source_document_id=source_document_id,
        extractor_type=extractor_type,
        records=records,
    )


def _parse_record(payload: dict[str, Any]) -> NormalizedExtractionRecord:
    if not isinstance(payload, dict):
        raise ValueError("normalized_extraction_record_not_object")

    scheme_name = str(payload.get("scheme_name") or "").strip()
    if not scheme_name:
        raise ValueError("normalized_extraction_scheme_name_missing")

    holdings = payload.get("holdings") or []
    if not isinstance(holdings, list):
        raise ValueError("normalized_extraction_holdings_not_list")
    for row in holdings:
        if not isinstance(row, dict):
            raise ValueError("normalized_extraction_holding_not_object")
        if not str(row.get("instrument_name") or row.get("security_name") or "").strip():
            raise ValueError("normalized_extraction_holding_name_missing")

    return NormalizedExtractionRecord(
        scheme_name=scheme_name,
        report_month=str(payload.get("report_month") or "").strip() or None,
        holdings=holdings,
        aum=_optional_float(payload.get("aum")),
        expense_ratio=_optional_float(payload.get("expense_ratio")),
        benchmark=str(payload.get("benchmark") or "").strip() or None,
        fund_manager=str(payload.get("fund_manager") or "").strip() or None,
        risk_level=str(payload.get("risk_level") or "").strip() or None,
        confidence_score=float(payload.get("confidence_score") or 0.0),
        validation_issues=[str(item) for item in (payload.get("validation_issues") or [])],
    )


def _optional_float(value: object) -> float | None:
    if value in (None, ""):
        return None
    return float(value)
