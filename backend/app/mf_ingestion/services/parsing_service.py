from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from app.database import supabase
from app.mf_ingestion.constants import VALIDATION_STATUS_INVALID, VALIDATION_STATUS_REVIEW
from app.mf_ingestion.normalizers.scheme_name_normalizer import match_scheme_name
from app.mf_ingestion.parsers.adapters.hdfc_adapter import HDFCAdapter
from app.mf_ingestion.parsers.adapters.icici_adapter import ICICIAdapter
from app.mf_ingestion.parsers.adapters.mirae_adapter import MiraeAdapter
from app.mf_ingestion.parsers.adapters.ppfas_adapter import PPFASAdapter
from app.mf_ingestion.parsers.adapters.sbi_adapter import SBIAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext
from app.mf_ingestion.parsers.holdings_parser import HoldingsParser
from app.mf_ingestion.services.review_service import ReviewService
from app.mf_ingestion.validators.holdings_validator import validate_holdings

logger = logging.getLogger(__name__)


class ParsingService:
    def __init__(self) -> None:
        self.review_service = ReviewService()
        self.adapters = {
            "ppfas": PPFASAdapter(),
            "mirae": MiraeAdapter(),
            "hdfc": HDFCAdapter(),
            "icici": ICICIAdapter(),
            "sbi": SBIAdapter(),
        }

    def parse_pending_documents(self, limit: int = 20, amc_code: str | None = None, report_month: str | None = None) -> dict[str, Any]:
        if not supabase:
            return {"status": "error", "reason": "supabase_not_configured"}

        query = (
            supabase.table("mf_raw_documents")
            .select("*")
            .in_("parse_status", ["pending", "downloaded", "needs_reparse"])
            .order("downloaded_at", desc=False)
            .limit(limit)
        )
        if amc_code:
            query = query.eq("amc_code", str(amc_code).upper())
        if report_month:
            query = query.eq("report_month", report_month)

        documents = query.execute().data or []
        processed = []

        for document in documents:
            processed.append(self._parse_one(document))

        return {"status": "ok", "processed": processed, "count": len(processed)}

    def _parse_one(self, document: dict[str, Any]) -> dict[str, Any]:
        document_id = str(document.get("id"))
        amc_code = str(document.get("amc_code") or "")
        adapter = self.adapters.get(amc_code.lower())
        if not adapter:
            self._mark_document(document_id, "failed", ["adapter_not_found"])
            return {"source_document_id": document_id, "status": "failed", "reason": "adapter_not_found"}

        if self._already_parsed(document_id):
            self._mark_document(document_id, "parsed", ["already_parsed_for_document"])
            return {"source_document_id": document_id, "status": "skipped", "reason": "already_parsed"}

        file_path = document.get("storage_path")
        if not file_path or not Path(file_path).exists():
            self._mark_document(document_id, "failed", ["raw_file_missing"])
            return {"source_document_id": document_id, "status": "failed", "reason": "raw_file_missing"}

        parser = HoldingsParser(adapter)
        parsed = parser.parse(
            file_path,
            ParseContext(
                source_document_id=document_id,
                source_url=str(document.get("source_url") or ""),
                report_month=_to_date_or_none(document.get("report_month")),
            ),
        )

        candidates = self._load_scheme_candidates(amc_code)
        scheme_match = match_scheme_name(parsed.scheme_name, candidates=candidates)

        validation = validate_holdings(
            parsed.holdings,
            scheme_match_confidence=scheme_match.confidence,
            report_month_present=bool(parsed.report_month),
        )

        final_confidence = min(parsed.confidence_score, scheme_match.confidence)
        scheme_id = self._upsert_scheme(amc_code, scheme_match.canonical_name, scheme_match.confidence)

        inserted_count = 0
        if validation.validation_status != VALIDATION_STATUS_INVALID:
            rows = []
            for row in parsed.holdings:
                rows.append(
                    {
                        "scheme_id": scheme_id,
                        "report_month": parsed.report_month.isoformat() if parsed.report_month else None,
                        "instrument_name": row.get("instrument_name"),
                        "instrument_name_normalized": str(row.get("instrument_name") or "").lower(),
                        "isin": row.get("isin") or None,
                        "sector": row.get("sector") or None,
                        "percent_aum": row.get("percent_aum"),
                        "source_document_id": document_id,
                        "source_url": document.get("source_url"),
                        "source_row_hash": _source_hash(row),
                        "parser_version": document.get("parser_version"),
                        "confidence_score": float(final_confidence),
                        "validation_status": validation.validation_status,
                    }
                )

            if rows:
                upsert_resp = (
                    supabase.table("mf_scheme_holdings")
                    .upsert(rows, on_conflict="source_document_id,source_row_hash")
                    .execute()
                )
                inserted_count = len(upsert_resp.data or [])

        metrics_payload = {
            "scheme_id": scheme_id,
            "report_month": parsed.report_month.isoformat() if parsed.report_month else None,
            "metric_name": "total_percent_aum",
            "metric_value": parsed.metrics.get("total_percent_aum"),
            "source_document_id": document_id,
            "source_url": document.get("source_url"),
            "parser_version": document.get("parser_version"),
            "confidence_score": float(final_confidence),
            "validation_status": validation.validation_status,
        }
        if metrics_payload.get("report_month"):
            supabase.table("mf_scheme_monthly_metrics").upsert(
                metrics_payload,
                on_conflict="scheme_id,report_month,metric_name,source_document_id",
            ).execute()

        review_needed = validation.validation_status in {VALIDATION_STATUS_REVIEW, VALIDATION_STATUS_INVALID}
        if review_needed:
            self.review_service.enqueue_document_review(
                source_document_id=document_id,
                amc_code=amc_code,
                report_month=parsed.report_month.isoformat() if parsed.report_month else None,
                source_url=document.get("source_url"),
                validation_issues=validation.issues,
                confidence_score=final_confidence,
                parser_version=str(document.get("parser_version") or ""),
                sample_rows=parsed.holdings[:5],
            )

        status = "needs_review" if review_needed else "parsed"
        self._mark_document(document_id, status, validation.issues)

        return {
            "source_document_id": document_id,
            "status": status,
            "scheme_name": scheme_match.canonical_name,
            "scheme_match_confidence": scheme_match.confidence,
            "confidence_score": final_confidence,
            "inserted_holdings": inserted_count,
            "validation_issues": validation.issues,
        }

    def _already_parsed(self, source_document_id: str) -> bool:
        res = (
            supabase.table("mf_scheme_holdings")
            .select("id")
            .eq("source_document_id", source_document_id)
            .limit(1)
            .execute()
        )
        return bool(res.data)

    def _upsert_scheme(self, amc_code: str, scheme_name: str, confidence: float) -> str:
        payload = {
            "amc_code": amc_code,
            "scheme_name": scheme_name,
            "scheme_name_normalized": scheme_name.lower(),
            "match_confidence": confidence,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        response = supabase.table("mf_schemes").upsert(payload, on_conflict="amc_code,scheme_name_normalized").execute()
        if response.data:
            return str(response.data[0]["id"])

        fallback = (
            supabase.table("mf_schemes")
            .select("id")
            .eq("amc_code", amc_code)
            .eq("scheme_name_normalized", scheme_name.lower())
            .limit(1)
            .execute()
        )
        if not fallback.data:
            raise RuntimeError("failed_to_upsert_scheme")
        return str(fallback.data[0]["id"])

    def _load_scheme_candidates(self, amc_code: str) -> list[str]:
        res = supabase.table("mf_schemes").select("scheme_name").eq("amc_code", amc_code).limit(500).execute()
        names = [str(row.get("scheme_name")) for row in (res.data or []) if row.get("scheme_name")]
        if str(amc_code).lower() == "ppfas" and "Parag Parikh Flexi Cap Fund" not in names:
            names.append("Parag Parikh Flexi Cap Fund")
        return names

    def _mark_document(self, source_document_id: str, status: str, issues: list[str]) -> None:
        supabase.table("mf_raw_documents").update(
            {
                "parse_status": status,
                "validation_issues": issues,
                "parsed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", source_document_id).execute()


def _source_hash(row: dict[str, Any]) -> str:
    return "|".join(
        [
            str(row.get("instrument_name") or "").strip().lower(),
            str(row.get("isin") or "").strip().upper(),
            str(row.get("percent_aum") or ""),
        ]
    )


def _to_date_or_none(value: Any) -> date | None:
    if value in (None, ""):
        return None
    if hasattr(value, "year") and hasattr(value, "month") and hasattr(value, "day"):
        return value
    raw = str(value)
    try:
        return datetime.fromisoformat(raw[:10]).date()
    except ValueError:
        return None
