from __future__ import annotations

import gzip
import json
import logging
import os
import re
import tempfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from app.database import supabase
from app.mf_ingestion.constants import VALIDATION_STATUS_INVALID, VALIDATION_STATUS_REVIEW
from app.mf_ingestion.extractors.contracts import NormalizedExtraction, NormalizedExtractionRecord
from app.mf_ingestion.extractors.llm_extractor import LLMExtractionUnavailable, StrictJSONLLMExtractor
from app.mf_ingestion.normalizers.scheme_name_normalizer import match_scheme_name
from app.mf_ingestion.parsers.adapters.hdfc_adapter import HDFCAdapter
from app.mf_ingestion.parsers.adapters.icici_adapter import ICICIAdapter
from app.mf_ingestion.parsers.adapters.mirae_adapter import MiraeAdapter
from app.mf_ingestion.parsers.adapters.ppfas_adapter import PPFASAdapter
from app.mf_ingestion.parsers.adapters.sbi_adapter import SBIAdapter
from app.mf_ingestion.parsers.adapters.axis_adapter import AxisAdapter
from app.mf_ingestion.parsers.adapters.motilal_adapter import MotilalAdapter
from app.mf_ingestion.parsers.adapters.nippon_adapter import NipponAdapter
from app.mf_ingestion.parsers.adapters.uti_adapter import UTIAdapter
from app.mf_ingestion.parsers.adapters.dsp_adapter import DSPAdapter
from app.mf_ingestion.parsers.adapters.kotak_adapter import KotakAdapter
from app.mf_ingestion.parsers.adapters.aditya_birla_adapter import AdityaBirlaAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext
from app.mf_ingestion.parsers.factsheet_parser import FactsheetParser, filter_factsheet_records_for_amc
from app.mf_ingestion.parsers.holdings_parser import HoldingsParser
from app.mf_ingestion.config import get_config
from app.mf_ingestion.storage.r2_store import R2Store, build_safe_key
from app.repositories.stock_repository import StockRepository
from app.mf_ingestion.services.document_classifier import DocumentClassification, classify_raw_document
from app.mf_ingestion.services.review_service import ReviewService
from app.mf_ingestion.sources.registry import get_source_by_code
from app.mf_ingestion.validators.holdings_validator import validate_holdings
from app.supabase_retry import execute_with_retry

logger = logging.getLogger(__name__)

HOLDINGS_SUPPORTED_DOCUMENT_TYPES = {"portfolio_disclosure"}
FACTSHEET_SUPPORTED_DOCUMENT_TYPES = {"factsheet", "ter_disclosure"}
AMC_DISCLOSURE_SOURCE = "amc_disclosure"
OFFICIAL_CORE_SOURCE_MARKERS = ("AMFI TER API", "AMFI AUM API", "TER", "AUM", AMC_DISCLOSURE_SOURCE)
OFFICIAL_HOLDING_SOURCES = ("AMFI scheme-wise disclosure", AMC_DISCLOSURE_SOURCE)
MAPPING_REVIEW_KEEP_PROMOTED_TARGET = "mapping_review_keep_applied_promotion_target"


def _execute_supabase(query: Any, operation_name: str) -> Any:
    return execute_with_retry(
        query.execute,
        operation_name=operation_name,
        log=logger,
    )


def guard_promoted_mapping_change(
    existing: dict[str, Any] | None,
    proposed: dict[str, Any],
) -> tuple[dict[str, Any], bool]:
    """Keep a promoted staging row on its reviewed identity when resolution drifts."""
    if not existing:
        return proposed, False
    promoted = bool(existing.get("promoted_scopes")) or str(
        existing.get("promotion_status") or ""
    ).lower() in {"promoted", "partially_promoted"}
    previous_identity = (
        str(existing.get("promoted_scheme_code") or existing.get("mapped_scheme_code") or ""),
        str(existing.get("promoted_family_id") or existing.get("mapped_family_id") or ""),
    )
    proposed_identity = (
        str(proposed.get("mapped_scheme_code") or ""),
        str(proposed.get("mapped_family_id") or ""),
    )
    if not promoted or previous_identity == proposed_identity:
        return proposed, False

    guarded = dict(proposed)
    guarded["mapped_scheme_code"] = previous_identity[0] or None
    guarded["mapped_family_id"] = previous_identity[1] or None
    guarded["mapping_confidence"] = existing.get("mapping_confidence")
    existing_issues = [str(issue) for issue in (existing.get("validation_issues") or [])]
    review_resolved = MAPPING_REVIEW_KEEP_PROMOTED_TARGET in existing_issues
    guarded["mapping_status"] = "mapped" if review_resolved else "needs_review"
    guarded["promotion_status"] = (
        str(existing.get("promotion_status") or "promoted")
        if review_resolved
        else "needs_review"
    )
    issues = list(dict.fromkeys([
        *existing_issues,
        *(proposed.get("validation_issues") or []),
        *([] if review_resolved else ["promoted_mapping_changed"]),
    ]))
    guarded["validation_issues"] = issues
    if review_resolved:
        logger.info(
            "event=reviewed_promoted_mapping_preserved scheme=%s",
            previous_identity[0],
        )
        return guarded, False
    logger.warning(
        "event=promoted_mapping_change_blocked previous_scheme=%s proposed_scheme=%s",
        previous_identity[0],
        proposed_identity[0],
    )
    return guarded, True


class ParsingService:
    def __init__(self) -> None:
        self.config = get_config()
        self.review_service = ReviewService()
        self.repository = StockRepository()
        self.factsheet_parser = FactsheetParser()
        self.r2_store = R2Store(
            endpoint=self.config.r2_endpoint,
            access_key_id=self.config.r2_access_key_id,
            secret_access_key=self.config.r2_secret_access_key,
            raw_bucket=self.config.r2_raw_bucket,
            cold_bucket=self.config.r2_cold_bucket,
            signed_url_ttl_seconds=self.config.r2_signed_url_ttl_seconds,
        )
        self.adapters = {
            "ppfas": PPFASAdapter(),
            "mirae": MiraeAdapter(),
            "hdfc": HDFCAdapter(),
            "icici": ICICIAdapter(),
            "sbi": SBIAdapter(),
            "axis": AxisAdapter(),
            "motilal": MotilalAdapter(),
            "nippon": NipponAdapter(),
            "uti": UTIAdapter(),
            "dsp": DSPAdapter(),
            "kotak": KotakAdapter(),
            "aditya_birla": AdityaBirlaAdapter(),
            "absl": AdityaBirlaAdapter(),
        }
        self.llm_extractor = StrictJSONLLMExtractor(
            enabled=self.config.llm_extractor_enabled,
            mode=self.config.extractor_mode,
            model=self.config.llm_extractor_model,
        )

    def parse_latest_document_for_scheme(self, amc_code: str, scheme_name: str) -> dict[str, Any] | None:
        """Runs the parser on the latest raw document for an AMC, strictly filtering for a specific scheme."""
        if not supabase:
            return None
        
        normalized_amc = str(amc_code).strip()
        query = (
            supabase.table("mf_raw_documents")
            .select("*")
            .in_("amc_code", [normalized_amc.lower(), normalized_amc.upper(), normalized_amc])
            .in_("document_type", ["portfolio_disclosure", "factsheet"])
            .order("report_month", desc=True)
            .order("downloaded_at", desc=True)
            .limit(1)
        )
        response = _execute_supabase(query, "load_latest_parser_document")
        if not response.data:
            return None
            
        document = response.data[0]
        logger.info("event=auto_heal_parsing amc_code=%s scheme_name=%s document_id=%s", amc_code, scheme_name, document.get("id"))
        return self._parse_one(document, bypass_official_coverage=True, target_scheme_name=scheme_name)

    def parse_pending_documents(
        self,
        limit: int = 20,
        amc_code: str | None = None,
        report_month: str | None = None,
        source_document_ids: list[str] | None = None,
    ) -> dict[str, Any]:
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
            normalized_amc_code = str(amc_code).strip()
            amc_filters = {
                normalized_amc_code,
                normalized_amc_code.lower(),
                normalized_amc_code.upper(),
            }
            try:
                resolved_source = get_source_by_code(normalized_amc_code)
            except ValueError:
                resolved_source = None
            if resolved_source:
                amc_filters.update(
                    {
                        resolved_source.amc_code,
                        resolved_source.amc_code.lower(),
                        resolved_source.amc_code.upper(),
                    }
                )
            query = query.in_("amc_code", sorted(amc_filters))
        if report_month:
            query = query.eq("report_month", report_month)
        if source_document_ids:
            query = query.in_("id", source_document_ids)

        documents = _execute_supabase(query, "load_pending_parser_documents").data or []
        if source_document_ids and not documents:
            return {
                "status": "error",
                "reason": "no_requested_documents_selected",
                "processed": [],
                "count": 0,
            }
        processed = []

        for document in documents:
            processed.append(self._parse_one(document))

        return {"status": "ok", "processed": processed, "count": len(processed)}

    def _parse_one(self, document: dict[str, Any], *, bypass_official_coverage: bool = False, target_scheme_name: str | None = None) -> dict[str, Any]:
        document_id = str(document.get("id"))
        amc_code = str(document.get("amc_code") or "")
        document_type = str(document.get("document_type") or document.get("source_document_type") or "").strip().lower()
        classification = classify_raw_document(document, set(self.adapters))
        irrelevant_issue = _irrelevant_document_issue(document)
        if irrelevant_issue:
            self._mark_document(document_id, "skipped_not_supported", [irrelevant_issue])
            return _attach_extraction_metadata(
                {"source_document_id": document_id, "status": "skipped", "reason": irrelevant_issue},
                classification,
            )
        if document_type and document_type not in HOLDINGS_SUPPORTED_DOCUMENT_TYPES and document_type not in FACTSHEET_SUPPORTED_DOCUMENT_TYPES:
            issue = f"unsupported_document_type:{document_type}"
            self._mark_document(document_id, "skipped_not_supported", [issue])
            return _attach_extraction_metadata(
                {"source_document_id": document_id, "status": "skipped", "reason": issue},
                classification,
            )
        try:
            source = get_source_by_code(amc_code)
        except ValueError:
            source = None
        parser_enabled = bool(
            source
            and (
                source.factsheet_parser_enabled
                if document_type in FACTSHEET_SUPPORTED_DOCUMENT_TYPES
                else source.portfolio_parser_enabled
            )
        )
        if not parser_enabled:
            issue = f"parser_disabled:{amc_code}:{document_type}"
            self._mark_document(document_id, "skipped_not_supported", [issue])
            return _attach_extraction_metadata(
                {"source_document_id": document_id, "status": "skipped", "reason": issue},
                classification,
            )

        if not bypass_official_coverage:
            api_coverage_issue = self._api_coverage_issue(document)
            if api_coverage_issue:
                self._mark_document(document_id, "official_source_covered", [api_coverage_issue])
                return _attach_extraction_metadata(
                    {"source_document_id": document_id, "status": "official_source_covered", "reason": api_coverage_issue},
                    classification,
                )

        unavailable_issue = self._r2_required_storage_issue(document)
        if unavailable_issue:
            self._mark_document(document_id, "skipped_no_source_data", [unavailable_issue])
            return _attach_extraction_metadata(
                {"source_document_id": document_id, "status": "skipped", "reason": unavailable_issue},
                classification,
            )

        resolved_path, temp_downloaded = self._resolve_document_path(document)
        if not resolved_path:
            self._mark_document(document_id, "failed", ["raw_file_missing"])
            return _attach_extraction_metadata(
                {"source_document_id": document_id, "status": "failed", "reason": "raw_file_missing"},
                classification,
            )

        try:
            if document_type in FACTSHEET_SUPPORTED_DOCUMENT_TYPES:
                content_month_issue = self._factsheet_content_month_issue(document, resolved_path)
                if content_month_issue:
                    self._mark_document(document_id, "needs_review", [content_month_issue])
                    return _attach_extraction_metadata(
                        {
                            "source_document_id": document_id,
                            "status": "needs_review",
                            "reason": content_month_issue,
                        },
                        classification,
                    )

            if self.config.extractor_mode == "llm_then_deterministic":
                llm_primary_result = self._try_llm_primary(document=document, file_path=resolved_path)
                if llm_primary_result:
                    return _attach_extraction_metadata(llm_primary_result, classification)

            if document_type in FACTSHEET_SUPPORTED_DOCUMENT_TYPES:
                factsheet_result = self._parse_factsheet_document(document, resolved_path, target_scheme_name=target_scheme_name)
                if source and source.factsheet_contains_holdings:
                    adapter = self.adapters.get(amc_code.lower())
                    if adapter:
                        holdings_result = self._parse_holdings_document(document, adapter, resolved_path, target_scheme_name=target_scheme_name)
                        return _attach_extraction_metadata(_merge_parse_outcomes(factsheet_result, holdings_result), classification)
                return _attach_extraction_metadata(factsheet_result, classification)

            adapter = self.adapters.get(amc_code.lower())
            if not adapter:
                self._mark_document(document_id, "failed", ["adapter_not_found"])
                return _attach_extraction_metadata(
                    {"source_document_id": document_id, "status": "failed", "reason": "adapter_not_found"},
                    classification,
                )
            return _attach_extraction_metadata(
                self._parse_holdings_document(document, adapter, resolved_path, target_scheme_name=target_scheme_name),
                classification,
            )
        finally:
            if temp_downloaded:
                try:
                    Path(temp_downloaded).unlink(missing_ok=True)
                except Exception:
                    logger.warning("event=temp_file_cleanup_failed path=%s", temp_downloaded)

    def _factsheet_content_month_issue(
        self,
        document: dict[str, Any],
        file_path: str,
    ) -> str | None:
        expected = _to_date_or_none(document.get("report_month"))
        if not expected:
            return None
        try:
            observed = self.factsheet_parser.detect_report_month(file_path)
        except Exception as exc:
            logger.info(
                "event=factsheet_content_month_detection_unavailable source_document_id=%s reason=%s",
                document.get("id"),
                type(exc).__name__,
            )
            return None
        if not observed or observed == expected:
            return None
        return (
            "factsheet_content_report_month_mismatch:"
            f"{observed.isoformat()}!={expected.isoformat()}"
        )

    def _r2_required_storage_issue(self, document: dict[str, Any]) -> str | None:
        if not self.config.require_r2_for_raw_storage:
            return None
        storage_backend = str(document.get("storage_backend") or "local").strip().lower()
        if storage_backend != "r2":
            return "raw_file_unavailable_in_r2_required_runtime"
        storage_key = str(document.get("storage_key") or "").strip()
        if not storage_key:
            return "missing_r2_storage_key"
        if not self.r2_store.object_exists(
            storage_key,
            bucket=str(document.get("storage_bucket") or "").strip() or self.config.r2_raw_bucket,
        ):
            return "missing_r2_object"
        return None

    def _parse_holdings_document(self, document: dict[str, Any], adapter: Any, file_path: str, target_scheme_name: str | None = None) -> dict[str, Any]:
        document_id = str(document.get("id"))
        amc_code = str(document.get("amc_code") or "")

        if document.get("parse_status") != "needs_reparse" and self._already_parsed(document_id):
            self._mark_document(document_id, "parsed", ["already_parsed_for_document"])
            return {"source_document_id": document_id, "status": "skipped", "reason": "already_parsed"}

        if supabase:
            try:
                _execute_supabase(
                    supabase.table("mf_scheme_holdings").delete().eq("source_document_id", document_id),
                    "clear_staged_holdings",
                )
                _execute_supabase(supabase.table("mf_scheme_sector_allocations").delete().eq(
                    "source_document_id",
                    document_id,
                ), "clear_staged_sectors")
                _execute_supabase(
                    supabase.table("mf_scheme_monthly_metrics").delete().eq("source_document_id", document_id),
                    "clear_staged_monthly_metrics",
                )
                _execute_supabase(
                    supabase.table("mf_parse_review_queue").delete().eq("source_document_id", document_id),
                    "clear_parser_review_queue",
                )
            except Exception as e:
                logger.warning("event=cleanup_failed source_document_id=%s reason=%s", document_id, e)

        parser = HoldingsParser(adapter)
        try:
            parse_batch = parser.parse_batch(
                file_path,
                ParseContext(
                    source_document_id=document_id,
                    source_url=str(document.get("source_url") or ""),
                    report_month=_to_date_or_none(document.get("report_month")),
                ),
            )
            parsed_documents = parse_batch.records
        except Exception as exc:
            logger.exception("event=parse_failed source_document_id=%s reason=%s", document_id, exc)
            self._mark_document(document_id, "failed", [f"parse_exception:{type(exc).__name__}"])
            return {"source_document_id": document_id, "status": "failed", "reason": "parse_exception"}

        parse_diagnostics = [diagnostic.to_dict() for diagnostic in parse_batch.diagnostics]
        if not parsed_documents:
            if parse_batch.failed_sources > 0:
                issue = "holdings_source_parse_failed"
                self._upload_parse_debug_snapshot(
                    document=document,
                    artifact="holdings_parse_failure",
                    payload={
                        "reason": issue,
                        "diagnostics": parse_diagnostics,
                        "failed_sources": parse_batch.failed_sources,
                        "empty_sources": parse_batch.empty_sources,
                    },
                )
                self._mark_document(document_id, "failed", [issue])
                return {
                    "source_document_id": document_id,
                    "status": "failed",
                    "reason": issue,
                    "diagnostics": parse_diagnostics,
                }
            issue = "holdings_not_found_in_document"
            llm_result = self._try_llm_fallback(document=document, file_path=file_path, issues=[issue])
            if llm_result:
                return llm_result
            self._upload_parse_debug_snapshot(
                document=document,
                artifact="holdings_parse_failure",
                payload=self._build_parse_failure_debug_payload(file_path=file_path, reason=issue),
            )
            self._mark_document(document_id, "needs_review", [issue])
            return {"source_document_id": document_id, "status": "needs_review", "reason": issue}

        results: list[dict[str, Any]] = []
        review_needed_overall = parse_batch.has_failures
        merged_issues: list[str] = ["partial_source_parse_failure"] if parse_batch.has_failures else []
        inserted_total = 0
        candidates = self._load_scheme_candidates(amc_code)
        document_report_month = _to_date_or_none(document.get("report_month"))

        for parsed in parsed_documents:
            parsed_scheme_name = str(parsed.scheme_name or "").strip()
            
            # Auto-Heal target filtering
            if target_scheme_name and parsed_scheme_name:
                # Check if this parsed scheme matches our target scheme
                temp_match = match_scheme_name(parsed_scheme_name, candidates=[target_scheme_name])
                if temp_match.confidence < 80.0:
                    continue

            report_month_issue = _parsed_record_report_month_issue(
                parsed.report_month,
                document_report_month,
            )
            if report_month_issue:
                review_needed_overall = True
                merged_issues.append(report_month_issue)
                self.review_service.enqueue_document_review(
                    source_document_id=document_id,
                    amc_code=amc_code,
                    report_month=(
                        parsed.report_month.isoformat()
                        if parsed.report_month
                        else None
                    ),
                    source_url=document.get("source_url"),
                    validation_issues=[report_month_issue],
                    confidence_score=float(parsed.confidence_score),
                    parser_version=str(document.get("parser_version") or ""),
                    sample_rows=parsed.holdings[:5],
                )
                results.append(
                    {
                        "scheme_name": parsed_scheme_name,
                        "scheme_match_confidence": 0.0,
                        "confidence_score": float(parsed.confidence_score),
                        "inserted_holdings": 0,
                        "inserted_sector_allocations": 0,
                        "validation_issues": [report_month_issue],
                    }
                )
                continue

            if parsed_scheme_name and parsed_scheme_name not in candidates:
                candidates.append(parsed_scheme_name)
            scheme_match = match_scheme_name(parsed.scheme_name, candidates=candidates)
            validation = validate_holdings(
                parsed.holdings,
                scheme_match_confidence=scheme_match.confidence,
                report_month_present=bool(parsed.report_month),
                total_percent_aum=parsed.metrics.get("total_percent_aum"),
            )
            final_confidence = min(parsed.confidence_score, scheme_match.confidence)
            scheme_id = self._upsert_scheme(amc_code, scheme_match.canonical_name, scheme_match.confidence)
            mapped_scheme_code, mapped_family_id, mapping_confidence, mapping_status = self._resolve_staged_mapping(
                amc_code,
                parsed.scheme_name,
            )

            inserted_count = 0
            inserted_sector_count = 0
            should_insert_holdings = validation.validation_status != VALIDATION_STATUS_INVALID
            if amc_code.lower() == "axis" and "percent_aum_out_of_band" in validation.issues:
                should_insert_holdings = False

            if should_insert_holdings:
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
                            "source_row_hash": f"{scheme_id}|{_source_hash(row)}",
                            "parser_version": document.get("parser_version"),
                            "confidence_score": float(final_confidence),
                            "validation_status": validation.validation_status,
                            "raw_scheme_name": parsed.scheme_name,
                            "mapped_scheme_code": mapped_scheme_code,
                            "mapped_family_id": mapped_family_id,
                            "mapping_confidence": mapping_confidence,
                            "mapping_status": mapping_status,
                        }
                    )
                if rows:
                    upsert_resp = _execute_supabase(
                        supabase.table("mf_scheme_holdings")
                        .upsert(rows, on_conflict="source_document_id,source_row_hash"),
                        "upsert_staged_holdings",
                    )
                    inserted_count = len(upsert_resp.data or [])

            sector_allocations = parsed.metrics.get("sector_allocations")
            if (
                isinstance(sector_allocations, list)
                and sector_allocations
                and parsed.report_month
            ):
                normalized_sector_allocations = _normalize_sector_allocations(
                    sector_allocations
                )
                sector_rows = [
                    {
                        "scheme_id": scheme_id,
                        "report_month": parsed.report_month.isoformat(),
                        "sector_name": row["sector"],
                        "sector_name_normalized": row["sector_normalized"],
                        "weight_pct": row.get("weight_pct"),
                        "source_document_id": document_id,
                        "source_url": document.get("source_url"),
                        "source_row_hash": f"{scheme_id}|sector|{row['sector_normalized']}",
                        "parser_version": document.get("parser_version"),
                        "confidence_score": float(final_confidence),
                        "validation_status": "valid",
                        "raw_scheme_name": parsed.scheme_name,
                        "mapped_scheme_code": mapped_scheme_code,
                        "mapped_family_id": mapped_family_id,
                        "mapping_confidence": mapping_confidence,
                        "mapping_status": mapping_status,
                    }
                    for row in normalized_sector_allocations
                ]
                if sector_rows:
                    sector_resp = _execute_supabase(
                        supabase.table("mf_scheme_sector_allocations")
                        .upsert(
                            sector_rows,
                            on_conflict="source_document_id,source_row_hash",
                        ),
                        "upsert_staged_sectors",
                    )
                    inserted_sector_count = len(sector_resp.data or [])

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
                _execute_supabase(
                    supabase.table("mf_scheme_monthly_metrics").upsert(
                        metrics_payload,
                        on_conflict="scheme_id,report_month,metric_name,source_document_id",
                    ),
                    "upsert_staged_monthly_metrics",
                )

            review_needed = (
                validation.validation_status in {VALIDATION_STATUS_REVIEW, VALIDATION_STATUS_INVALID}
                or parse_batch.has_failures
            )
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
            review_needed_overall = review_needed_overall or review_needed
            merged_issues.extend(validation.issues)
            inserted_total += inserted_count
            results.append(
                {
                    "scheme_name": scheme_match.canonical_name,
                    "scheme_match_confidence": scheme_match.confidence,
                    "confidence_score": final_confidence,
                    "inserted_holdings": inserted_count,
                    "inserted_sector_allocations": inserted_sector_count,
                    "validation_issues": validation.issues,
                }
            )

        dedup_issues = sorted(set(merged_issues))
        status = "needs_review" if review_needed_overall else "parsed"
        if review_needed_overall and inserted_total > 0:
            status = "parsed_partial"
            
        if not target_scheme_name:
            self._mark_document(document_id, status, dedup_issues)
            self._upload_parse_debug_snapshot(
                document=document,
                artifact="holdings_parse_summary",
                payload={
                    "source_document_id": document_id,
                    "status": status,
                    "parsed_schemes": len(results),
                    "inserted_holdings": inserted_total,
                    "validation_issues": dedup_issues,
                    "diagnostics": parse_diagnostics,
                    "successful_sources": parse_batch.successful_sources,
                    "empty_sources": parse_batch.empty_sources,
                    "failed_sources": parse_batch.failed_sources,
                    "schemes": results,
                },
            )
            
        if len(results) == 1:
            result = results[0]
            return {
                "source_document_id": document_id,
                "status": status,
                "extractor_type": "deterministic",
                "scheme_name": result["scheme_name"],
                "scheme_match_confidence": result["scheme_match_confidence"],
                "confidence_score": result["confidence_score"],
                "inserted_holdings": result["inserted_holdings"],
                "inserted_sector_allocations": result["inserted_sector_allocations"],
                "validation_issues": result["validation_issues"],
                "diagnostics": parse_diagnostics,
            }
        return {
            "source_document_id": document_id,
            "status": status,
            "extractor_type": "deterministic",
            "parsed_schemes": len(results),
            "inserted_holdings": inserted_total,
            "inserted_sector_allocations": sum(
                int(result["inserted_sector_allocations"]) for result in results
            ),
            "validation_issues": dedup_issues,
            "diagnostics": parse_diagnostics,
        }

    def _parse_factsheet_document(self, document: dict[str, Any], file_path: str, target_scheme_name: str | None = None) -> dict[str, Any]:
        document_id = str(document.get("id"))
        amc_code = str(document.get("amc_code") or "")
        report_month = _to_date_or_none(document.get("report_month"))
        parse_context = ParseContext(
            source_document_id=document_id,
            source_url=str(document.get("source_url") or ""),
            report_month=report_month,
        )
        try:
            records = filter_factsheet_records_for_amc(
                self.factsheet_parser.parse(file_path, parse_context),
                amc_code,
            )
        except Exception as exc:
            logger.exception("event=factsheet_parse_failed source_document_id=%s reason=%s", document_id, exc)
            self._mark_document(document_id, "failed", [f"factsheet_parse_exception:{type(exc).__name__}"])
            return {"source_document_id": document_id, "status": "failed", "reason": "factsheet_parse_exception"}

        if not records:
            issue = "factsheet_fields_not_extracted"
            llm_result = self._try_llm_fallback(document=document, file_path=file_path, issues=[issue])
            if llm_result:
                return llm_result
            self._mark_document(document_id, "needs_review", [issue])
            return {"source_document_id": document_id, "status": "needs_review", "reason": issue}

        updated = 0
        unmatched = 0
        for record in records:
            if target_scheme_name:
                temp_match = match_scheme_name(record.scheme_name, candidates=[target_scheme_name])
                if temp_match.confidence < 80.0:
                    continue
                    
            matched = self._stage_amc_core_fields(
                amc_code=amc_code,
                scheme_name=record.scheme_name,
                report_month=record.report_month or report_month,
                source_document_id=document_id,
                source_url=str(document.get("source_url") or ""),
                parser_version=str(document.get("parser_version") or ""),
                aum=record.aum,
                expense_ratio=record.expense_ratio,
                benchmark=record.benchmark,
                fund_manager=record.fund_manager,
                risk_level=record.risk_level,
            )
            if matched:
                updated += 1
            else:
                unmatched += 1

        issues: list[str] = []
        status = "parsed"
        if updated == 0:
            status = "needs_review"
            issues.append("factsheet_scheme_matching_failed")
        elif unmatched > 0:
            status = "parsed_partial"
            issues.append("factsheet_partial_scheme_matching")
            
        if not target_scheme_name:
            self._mark_document(document_id, status, issues)
            self._upload_parse_debug_snapshot(
                document=document,
                artifact="factsheet_parse_summary",
                payload={
                    "source_document_id": document_id,
                    "status": status,
                    "updated_schemes": updated,
                    "unmatched_schemes": unmatched,
                    "validation_issues": issues,
                    "records": [
                        {
                            "scheme_name": record.scheme_name,
                            "report_month": record.report_month.isoformat() if record.report_month else None,
                            "aum": record.aum,
                            "expense_ratio": record.expense_ratio,
                            "benchmark": record.benchmark,
                            "fund_manager": record.fund_manager,
                            "risk_level": record.risk_level,
                        }
                        for record in records
                    ],
                },
            )
        return {
            "source_document_id": document_id,
            "status": status,
            "extractor_type": "deterministic",
            "updated_schemes": updated,
            "unmatched_schemes": unmatched,
            "validation_issues": issues,
        }

    def _try_llm_fallback(self, *, document: dict[str, Any], file_path: str, issues: list[str]) -> dict[str, Any] | None:
        document_id = str(document.get("id") or "")
        try:
            extraction = self.llm_extractor.extract(file_path, document)
        except LLMExtractionUnavailable as exc:
            logger.info("event=llm_extraction_unavailable source_document_id=%s reason=%s", document_id, exc)
            return None
        except Exception as exc:
            logger.exception("event=llm_extraction_failed source_document_id=%s reason=%s", document_id, exc)
            return None

        payloads = self._build_llm_review_payloads(
            extraction,
            source_document_id=document_id,
            issues=[*issues, "llm_extraction_requires_review"],
        )
        validation_issues = sorted({issue for payload in payloads for issue in payload["validation_issues"]})
        self.review_service.enqueue_document_review(
            source_document_id=document_id,
            amc_code=str(document.get("amc_code") or ""),
            report_month=str(document.get("report_month") or "") or None,
            source_url=document.get("source_url"),
            validation_issues=validation_issues,
            confidence_score=max([float(payload.get("confidence_score") or 0.0) for payload in payloads], default=0.0),
            parser_version=str(document.get("parser_version") or ""),
            sample_rows=payloads,
        )
        self._mark_document(document_id, "fallback_needs_review", validation_issues)
        self._upload_parse_debug_snapshot(
            document=document,
            artifact="llm_fallback_extraction",
            payload={"records": payloads},
        )
        return {
            "source_document_id": document_id,
            "status": "fallback_needs_review",
            "extractor_type": "llm",
            "normalized_extraction": {"records": payloads},
            "validation_issues": validation_issues,
        }

    def _try_llm_primary(self, *, document: dict[str, Any], file_path: str) -> dict[str, Any] | None:
        document_id = str(document.get("id") or "")
        try:
            extraction = self.llm_extractor.extract(file_path, document)
        except LLMExtractionUnavailable as exc:
            logger.info("event=llm_primary_unavailable source_document_id=%s reason=%s", document_id, exc)
            return None
        except Exception as exc:
            logger.exception("event=llm_primary_failed source_document_id=%s reason=%s", document_id, exc)
            return None

        accepted = []
        rejected = []
        for record in extraction.records:
            issues = self._llm_record_write_issues(document, record)
            if issues:
                rejected.append((record, issues))
                continue

            written = self._stage_amc_core_fields(
                amc_code=str(document.get("amc_code") or ""),
                scheme_name=record.scheme_name,
                report_month=_to_date_or_none(record.report_month),
                source_document_id=document_id,
                source_url=str(document.get("source_url") or ""),
                parser_version=str(document.get("parser_version") or ""),
                aum=record.aum,
                expense_ratio=record.expense_ratio,
                benchmark=record.benchmark,
                fund_manager=record.fund_manager,
                risk_level=record.risk_level,
                extractor_type="llm",
                extractor_model=self.config.llm_extractor_model,
                confidence_score=float(record.confidence_score or 0.0),
            )
            if written:
                accepted.append(record)
            else:
                rejected.append((record, ["llm_scheme_match_or_field_write_failed"]))

        if rejected:
            payloads = [
                self._llm_record_payload(
                    record,
                    source_document_id=document_id,
                    issues=[*issues, "llm_primary_requires_review"],
                )
                for record, issues in rejected
            ]
            self.review_service.enqueue_document_review(
                source_document_id=document_id,
                amc_code=str(document.get("amc_code") or ""),
                report_month=str(document.get("report_month") or "") or None,
                source_url=document.get("source_url"),
                validation_issues=sorted({issue for _record, issues in rejected for issue in issues}),
                confidence_score=max([float(record.confidence_score or 0.0) for record, _issues in rejected], default=0.0),
                parser_version=str(document.get("parser_version") or ""),
                sample_rows=payloads,
            )

        if not self.config.llm_allow_final_writes:
            return None

        if not accepted:
            return None

        status = "parsed" if not rejected else "parsed_partial"
        issues = ["llm_partial_review_required"] if rejected else []
        self._mark_document(document_id, status, issues)
        self._upload_parse_debug_snapshot(
            document=document,
            artifact="llm_primary_extraction",
            payload={
                "accepted_records": [record.to_dict() for record in accepted],
                "rejected_records": [
                    self._llm_record_payload(record, source_document_id=document_id, issues=issues)
                    for record, issues in rejected
                ],
            },
        )
        return {
            "source_document_id": document_id,
            "status": status,
            "extractor_type": "llm",
            "updated_schemes": len(accepted),
            "review_schemes": len(rejected),
            "validation_issues": issues,
        }

    def _build_llm_review_payloads(
        self,
        extraction: NormalizedExtraction,
        *,
        source_document_id: str,
        issues: list[str],
    ) -> list[dict[str, Any]]:
        return [
            self._llm_record_payload(
                record,
                source_document_id=source_document_id,
                issues=[*issues, *self._llm_record_validation_issues(record)],
            )
            for record in extraction.records
        ]

    def _llm_record_payload(self, record: NormalizedExtractionRecord, *, source_document_id: str, issues: list[str]) -> dict[str, Any]:
        payload = record.to_dict()
        payload["source_document_id"] = source_document_id
        payload["extractor_type"] = "llm"
        payload["validation_issues"] = sorted(set([*payload.get("validation_issues", []), *issues]))
        return payload

    def _llm_record_write_issues(self, document: dict[str, Any], record: NormalizedExtractionRecord) -> list[str]:
        issues = self._llm_record_validation_issues(record)
        if not self.config.llm_allow_final_writes:
            issues.append("llm_final_writes_disabled")
        if not str(document.get("source_url") or "").strip():
            issues.append("source_url_missing")
        if float(record.confidence_score or 0.0) < float(self.config.llm_min_write_confidence):
            issues.append("llm_confidence_below_write_threshold")
        if not any(value not in (None, "") for value in (record.aum, record.expense_ratio, record.benchmark, record.fund_manager, record.risk_level)):
            issues.append("llm_no_core_fields")
        if record.holdings:
            issues.append("llm_holdings_require_review")
        return sorted(set(issues))

    def _llm_record_validation_issues(self, record: NormalizedExtractionRecord) -> list[str]:
        issues = list(record.validation_issues or [])
        if not record.report_month:
            issues.append("report_month_missing")
        if record.holdings:
            validation = validate_holdings(
                record.holdings,
                scheme_match_confidence=float(record.confidence_score or 0.0),
                report_month_present=bool(record.report_month),
            )
            issues.extend(validation.issues)
        return sorted(set(issues))

    def _already_parsed(self, source_document_id: str) -> bool:
        res = _execute_supabase(
            supabase.table("mf_scheme_holdings")
            .select("id")
            .eq("source_document_id", source_document_id)
            .limit(1),
            "check_already_parsed",
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
        response = _execute_supabase(
            supabase.table("mf_schemes").upsert(payload, on_conflict="amc_code,scheme_name_normalized"),
            "upsert_parsed_scheme",
        )
        if response.data:
            return str(response.data[0]["id"])

        fallback = _execute_supabase(
            supabase.table("mf_schemes")
            .select("id")
            .eq("amc_code", amc_code)
            .eq("scheme_name_normalized", scheme_name.lower())
            .limit(1),
            "load_upserted_scheme",
        )
        if not fallback.data:
            raise RuntimeError("failed_to_upsert_scheme")
        return str(fallback.data[0]["id"])

    def _load_scheme_candidates(self, amc_code: str) -> list[str]:
        res = _execute_supabase(
            supabase.table("mf_schemes").select("scheme_name").eq("amc_code", amc_code).limit(500),
            "load_scheme_candidates",
        )
        names = [str(row.get("scheme_name")) for row in (res.data or []) if row.get("scheme_name")]
        if str(amc_code).lower() == "ppfas" and "Parag Parikh Flexi Cap Fund" not in names:
            names.append("Parag Parikh Flexi Cap Fund")
        return names

    def _api_coverage_issue(self, document: dict[str, Any]) -> str | None:
        if not _truthy_env("ENABLE_MF_OFFICIAL_SOURCE_PARSER_BYPASS", True):
            return None
        document_type = str(document.get("document_type") or document.get("source_document_type") or "").strip().lower()
        amc_code = str(document.get("amc_code") or "").strip().lower()
        report_month = _to_date_or_none(document.get("report_month"))
        if not document_type or not amc_code or not report_month:
            return None

        if document_type in HOLDINGS_SUPPORTED_DOCUMENT_TYPES:
            return None

        if document_type in FACTSHEET_SUPPORTED_DOCUMENT_TYPES:
            if amc_code == "hdfc":
                return None
            factsheet_covered = self._official_factsheet_covers_document(amc_code, report_month)
            if factsheet_covered and self._official_risk_level_covers_document(amc_code, report_month):
                return "skipped_official_source_covered:factsheet"

        return None

    def _official_core_rows_for_amc(self, amc_code: str) -> list[dict[str, Any]]:
        client = self.repository.supabase if self.repository else supabase
        if not client:
            return []
        patterns = _amc_lookup_patterns(amc_code)
        rows: list[dict[str, Any]] = []
        seen: set[str] = set()
        for pattern in patterns:
            try:
                response = _execute_supabase(
                    client.table("mutual_fund_core_snapshot")
                    .select("scheme_code,amc_name,data_source,provider_payload,aum,expense_ratio,benchmark,fund_manager,risk_level")
                    .ilike("amc_name", pattern)
                    .limit(1000),
                    "load_official_core_rows",
                )
            except Exception:
                logger.exception("event=official_core_lookup_failed amc_code=%s", amc_code)
                continue
            for row in response.data or []:
                scheme_code = str(row.get("scheme_code") or "")
                if not scheme_code or scheme_code in seen:
                    continue
                source = str(row.get("data_source") or "")
                if not any(marker in source for marker in OFFICIAL_CORE_SOURCE_MARKERS):
                    continue
                seen.add(scheme_code)
                rows.append(row)
        return rows

    def _official_factsheet_covers_document(self, amc_code: str, report_month: date) -> bool:
        rows = self._official_core_rows_for_amc(amc_code)
        if not rows:
            return False
        return all(
            all(row.get(field) not in (None, "") for field in ("aum", "expense_ratio", "benchmark", "fund_manager"))
            for row in rows
        )

    def _official_risk_level_covers_document(self, amc_code: str, report_month: date) -> bool:
        for row in self._official_core_rows_for_amc(amc_code):
            provider_payload = row.get("provider_payload") if isinstance(row.get("provider_payload"), dict) else {}
            amc_trace = provider_payload.get("amc_trace") if isinstance(provider_payload.get("amc_trace"), dict) else {}
            risk_trace = amc_trace.get("risk_level") if isinstance(amc_trace.get("risk_level"), dict) else {}
            if row.get("risk_level") in (None, "") or risk_trace.get("value") in (None, ""):
                continue
            traced_month = _to_date_or_none(risk_trace.get("report_month"))
            if traced_month and traced_month >= report_month:
                return True
        return False



    def _mark_document(self, source_document_id: str, status: str, issues: list[str]) -> None:
        _execute_supabase(
            supabase.table("mf_raw_documents").update(
                {
                    "parse_status": status,
                    "validation_issues": issues,
                    "parsed_at": datetime.now(timezone.utc).isoformat(),
                }
            ).eq("id", source_document_id),
            "mark_parser_document",
        )
        if status in {"api_covered", "official_source_covered", "parsed", "parsed_partial", "skipped_not_supported", "skipped_no_source_data"}:
            try:
                _execute_supabase(
                    supabase.table("mf_parse_review_queue").delete().eq("source_document_id", source_document_id),
                    "clear_completed_parser_review",
                )
            except Exception:
                logger.warning("event=review_queue_cleanup_failed source_document_id=%s status=%s", source_document_id, status)

    def _resolve_scheme_code_for_scheme(self, scheme_name: str) -> str | None:
        lookup_name = _scheme_name_for_matching(scheme_name)
        candidates: list[dict[str, Any]] = []
        patterns = [
            _build_ilike_pattern(lookup_name),
            _build_relaxed_ilike_pattern(lookup_name),
        ]
        seen_patterns = {pattern for pattern in patterns if pattern and pattern != "%"}
        if not seen_patterns:
            seen_patterns = {"%"}

        for pattern in seen_patterns:
            for table in ("mutual_fund_core_snapshot", "mutual_funds"):
                try:
                    result = _execute_supabase(
                        supabase.table(table)
                        .select("scheme_code,scheme_name")
                        .ilike("scheme_name", pattern)
                        .limit(350),
                        "resolve_parser_scheme_code",
                    )
                    candidates.extend(result.data or [])
                except Exception:
                    logger.exception("event=scheme_code_lookup_failed table=%s scheme_name=%s", table, scheme_name)
                    continue

        if not candidates:
            return None

        best = _select_best_scheme_candidate(lookup_name, candidates)
        if not best:
            return None
        code = str(best.get("scheme_code") or "").strip()
        return code or None

    def _stage_amc_core_fields(
        self,
        amc_code: str,
        scheme_name: str,
        report_month: date | None,
        source_document_id: str,
        source_url: str,
        parser_version: str,
        aum: float | None,
        expense_ratio: float | None,
        benchmark: str | None,
        fund_manager: str | None,
        risk_level: str | None,
        extractor_type: str = "deterministic",
        extractor_model: str | None = None,
        confidence_score: float | None = None,
    ) -> bool:
        field_values: dict[str, Any] = {
            "aum": aum,
            "expense_ratio": expense_ratio,
            "benchmark": benchmark,
            "fund_manager": fund_manager,
            "risk_level": risk_level,
        }
        parsed_fields = {key: value for key, value in field_values.items() if value not in (None, "")}
        if not parsed_fields:
            return False
        scheme_code, family_id, mapping_confidence, mapping_status = self._resolve_staged_mapping(
            amc_code,
            scheme_name,
        )
        issues: list[str] = []
        if mapping_status != "mapped":
            issues.append(f"scheme_mapping_{mapping_status}")
        if not report_month:
            issues.append("report_month_missing")
        try:
            raw_document = _execute_supabase(
                supabase.table("mf_raw_documents")
                .select("storage_bucket,storage_key,checksum")
                .eq("id", source_document_id)
                .limit(1),
                "load_parser_source_metadata",
            )
            source_meta = (raw_document.data or [{}])[0] or {}
        except Exception:
            source_meta = {}

        normalized_scheme_name = _normalize_scheme_text(_scheme_name_for_matching(scheme_name))
        try:
            existing_result = _execute_supabase(
                supabase.table("mf_factsheet_candidates")
                .select(
                    "id,mapped_scheme_code,mapped_family_id,mapping_confidence,mapping_status,"
                    "promotion_status,promoted_scopes,validation_issues"
                )
                .eq("source_document_id", source_document_id)
                .eq("normalized_scheme_name", normalized_scheme_name)
                .limit(1),
                "load_existing_factsheet_candidate",
            )
            existing_candidate = (existing_result.data or [None])[0]
            if existing_candidate and (
                existing_candidate.get("promoted_scopes")
                or str(existing_candidate.get("promotion_status") or "").lower()
                in {"promoted", "partially_promoted"}
            ):
                try:
                    promotion_result = _execute_supabase(
                        supabase.table("mf_promotion_runs")
                        .select("after_snapshot,created_at")
                        .eq("candidate_id", existing_candidate.get("id"))
                        .eq("status", "applied")
                        .order("created_at", desc=True)
                        .limit(1),
                        "load_candidate_promotion_identity",
                    )
                    promotion_row = (promotion_result.data or [None])[0]
                    snapshot = promotion_row.get("after_snapshot") if promotion_row else None
                    promoted_scheme_code = (
                        snapshot.get("scheme_code") if isinstance(snapshot, dict) else None
                    )
                    if promoted_scheme_code:
                        existing_candidate = {
                            **existing_candidate,
                            "promoted_scheme_code": str(promoted_scheme_code),
                        }
                except Exception:
                    logger.exception(
                        "event=promotion_identity_lookup_failed candidate_id=%s",
                        existing_candidate.get("id"),
                    )
        except Exception:
            existing_candidate = None

        payload: dict[str, Any] = {
            "source_document_id": source_document_id,
            "amc_code": amc_code,
            "report_month": report_month.isoformat() if report_month else None,
            "raw_scheme_name": scheme_name,
            "normalized_scheme_name": normalized_scheme_name,
            "mapped_scheme_code": scheme_code,
            "mapped_family_id": family_id,
            "mapping_confidence": mapping_confidence,
            "mapping_status": mapping_status,
            "validation_issues": issues,
            "source_url": source_url,
            "storage_bucket": source_meta.get("storage_bucket"),
            "storage_key": source_meta.get("storage_key"),
            "checksum": source_meta.get("checksum"),
            "parser_version": parser_version,
            "extractor_type": extractor_type,
            "extractor_model": extractor_model,
            "extractor_confidence": confidence_score,
            "promotion_status": "staged" if mapping_status == "mapped" and report_month else "needs_review",
            "updated_at": datetime.now(timezone.utc).isoformat(),
            **parsed_fields,
        }
        payload, mapping_changed = guard_promoted_mapping_change(existing_candidate, payload)
        _execute_supabase(
            supabase.table("mf_factsheet_candidates").upsert(
                payload,
                on_conflict="source_document_id,normalized_scheme_name",
            ),
            "upsert_factsheet_candidate",
        )
        return mapping_status == "mapped" and bool(report_month) and not mapping_changed

    def _resolve_document_path(self, document: dict[str, Any]) -> tuple[str | None, str | None]:
        storage_backend = str(document.get("storage_backend") or "local").strip().lower()
        storage_bucket = str(document.get("storage_bucket") or "").strip() or None
        storage_key = str(document.get("storage_key") or "").strip()
        storage_path = str(document.get("storage_path") or "").strip()

        if storage_backend == "r2" and storage_key and self.r2_store.enabled:
            suffix = Path(storage_key).suffix or ".bin"
            with tempfile.NamedTemporaryFile(prefix="mf_doc_", suffix=suffix, delete=False) as handle:
                temp_path = handle.name
            self.r2_store.download_to_file(storage_key, temp_path, bucket=storage_bucket or self.config.r2_raw_bucket)
            return temp_path, temp_path

        if storage_path and Path(storage_path).exists():
            return str(Path(storage_path).resolve()), None
        return None, None

    def _resolve_family_id_for_scheme(self, scheme_code: str) -> str | None:
        try:
            mapping = _execute_supabase(
                supabase.table("mutual_fund_family_mapping")
                .select("family_id")
                .eq("scheme_code", str(scheme_code))
                .limit(1),
                "load_parser_family_mapping",
            )
            if mapping.data and mapping.data[0].get("family_id"):
                return str(mapping.data[0]["family_id"])
        except Exception:
            logger.exception("event=family_mapping_lookup_failed scheme_code=%s", scheme_code)
        snapshot = self.repository.get_mutual_fund_core_snapshot(scheme_code) or {}
        provider_payload = snapshot.get("provider_payload") if isinstance(snapshot.get("provider_payload"), dict) else {}
        value = provider_payload.get("family_id") or snapshot.get("family_id")
        if value in (None, ""):
            return None
        return str(value)

    def _resolve_staged_mapping(
        self,
        amc_code: str,
        raw_scheme_name: str,
    ) -> tuple[str | None, str | None, float, str]:
        scheme_code = self._resolve_scheme_code_for_scheme(raw_scheme_name)
        if not scheme_code:
            return None, None, 0.0, "unmapped"

        snapshot = self.repository.get_mutual_fund_core_snapshot(scheme_code) or {}
        snapshot_name = str(snapshot.get("scheme_name") or "").strip()
        snapshot_amc = str(snapshot.get("amc_name") or "").strip()
        if not snapshot_name or not _snapshot_matches_amc(amc_code, snapshot_amc):
            return scheme_code, None, 0.0, "needs_review"

        match = match_scheme_name(
            _normalize_family_scheme_name(raw_scheme_name),
            candidates=[_normalize_family_scheme_name(snapshot_name)],
        )
        mapping_confidence = float(match.confidence)
        family_id = self._resolve_family_id_for_scheme(scheme_code)
        if not family_id or mapping_confidence < 90.0:
            return scheme_code, family_id, mapping_confidence, "needs_review"
        return scheme_code, family_id, mapping_confidence, "mapped"

    def _upload_parse_debug_snapshot(self, *, document: dict[str, Any], artifact: str, payload: dict[str, Any]) -> None:
        if not self.r2_store.enabled:
            return
        amc_code = str(document.get("amc_code") or "unknown").lower()
        report_month = str(document.get("report_month") or "")[:7] or "unknown-month"
        source_document_id = str(document.get("id") or "unknown")
        checksum = str(document.get("checksum") or "")
        key = build_safe_key(
            "debug",
            amc_code,
            report_month,
            source_document_id,
            f"{artifact}.json.gz",
        )
        encoded = gzip.compress(json.dumps(payload, default=str).encode("utf-8"))
        metadata = {"source_document_id": source_document_id}
        if checksum:
            metadata["checksum"] = checksum
        self.r2_store.upload_bytes(
            key=key,
            content=encoded,
            bucket=self.config.r2_cold_bucket,
            content_type="application/gzip",
            metadata=metadata,
        )

    def _build_parse_failure_debug_payload(self, *, file_path: str, reason: str) -> dict[str, Any]:
        path = Path(file_path)
        payload: dict[str, Any] = {
            "reason": reason,
            "file_name": path.name,
            "file_ext": path.suffix.lower(),
            "file_size_bytes": path.stat().st_size if path.exists() else None,
            "detected_pages": [],
            "detected_sheets": [],
            "headers": [],
            "raw_sample_rows": [],
            "normalized_sample_rows": [],
        }
        try:
            if path.suffix.lower() in {".xls", ".xlsx", ".xlsm", ".csv"}:
                self._append_excel_failure_debug(payload, path)
            elif path.suffix.lower() == ".pdf":
                self._append_pdf_failure_debug(payload, path)
        except Exception as exc:
            payload["debug_error"] = f"{type(exc).__name__}:{exc}"
        return payload

    def _append_excel_failure_debug(self, payload: dict[str, Any], path: Path) -> None:
        import pandas as pd

        workbook = pd.read_excel(path, sheet_name=None, nrows=12)
        for sheet_name, frame in list(workbook.items())[:8]:
            payload["detected_sheets"].append(sheet_name)
            headers = [str(col) for col in list(frame.columns)[:12]]
            payload["headers"].append({"sheet": sheet_name, "columns": headers})
            rows = frame.head(5).where(pd.notna(frame.head(5)), None).values.tolist()
            payload["raw_sample_rows"].append({"sheet": sheet_name, "rows": rows})
            payload["normalized_sample_rows"].append(
                {
                    "sheet": sheet_name,
                    "rows": [
                        [" ".join(str(cell or "").split()) for cell in row[:12]]
                        for row in rows
                    ],
                }
            )

    def _append_pdf_failure_debug(self, payload: dict[str, Any], path: Path) -> None:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            for page in pdf.pages[:8]:
                page_text = page.extract_text() or ""
                tables = page.extract_tables() or []
                page_payload = {
                    "page_number": page.page_number,
                    "text_head": page_text.splitlines()[:20],
                    "table_count": len(tables),
                }
                payload["detected_pages"].append(page_payload)
                for table_index, table in enumerate(tables[:3]):
                    if not table:
                        continue
                    payload["headers"].append(
                        {
                            "page_number": page.page_number,
                            "table_index": table_index,
                            "columns": [str(cell or "") for cell in table[0][:12]],
                        }
                    )
                    sample_rows = table[1:6]
                    payload["raw_sample_rows"].append(
                        {
                            "page_number": page.page_number,
                            "table_index": table_index,
                            "rows": sample_rows,
                        }
                    )
                    payload["normalized_sample_rows"].append(
                        {
                            "page_number": page.page_number,
                            "table_index": table_index,
                            "rows": [
                                [" ".join(str(cell or "").split()) for cell in row[:12]]
                                for row in sample_rows
                            ],
                        }
                    )


def _source_hash(row: dict[str, Any]) -> str:
    return "|".join(
        [
            str(row.get("instrument_name") or "").strip().lower(),
            str(row.get("isin") or "").strip().upper(),
            str(row.get("percent_aum") or ""),
        ]
    )


def _normalize_sector_allocations(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    aggregated: dict[str, dict[str, Any]] = {}
    for row in rows:
        sector = " ".join(str(row.get("sector") or "").split())
        if not sector or row.get("weight_pct") is None:
            continue
        normalized = sector.casefold()
        current = aggregated.setdefault(
            normalized,
            {
                "sector": sector,
                "sector_normalized": normalized,
                "weight_pct": 0.0,
            },
        )
        current["weight_pct"] = round(
            float(current["weight_pct"]) + float(row["weight_pct"]),
            6,
        )
    return [aggregated[key] for key in sorted(aggregated)]


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


def _parsed_record_report_month_issue(
    parsed_report_month: Any,
    document_report_month: Any,
) -> str | None:
    parsed = _to_date_or_none(parsed_report_month)
    expected = _to_date_or_none(document_report_month)
    if not parsed or not expected:
        return None
    if (parsed.year, parsed.month) == (expected.year, expected.month):
        return None
    return (
        "parsed_record_report_month_mismatch:"
        f"{parsed.replace(day=1).isoformat()}!={expected.replace(day=1).isoformat()}"
    )


def _should_write_risk_level(existing: dict[str, Any], report_month: date | None) -> bool:
    provider_payload = existing.get("provider_payload") if isinstance(existing.get("provider_payload"), dict) else {}
    amc_trace = provider_payload.get("amc_trace") if isinstance(provider_payload.get("amc_trace"), dict) else {}
    risk_trace = amc_trace.get("risk_level") if isinstance(amc_trace.get("risk_level"), dict) else {}

    existing_value = str(existing.get("risk_level") or "").strip()
    if not existing_value:
        return True

    traced_value = str(risk_trace.get("value") or "").strip()
    if not traced_value:
        return True

    traced_month = _to_date_or_none(risk_trace.get("report_month"))
    if report_month and traced_month:
        return report_month >= traced_month
    return False


def _build_ilike_pattern(text: str) -> str:
    words = [word for word in _normalize_lookup_text(text).split() if word]
    return f"%{'%'.join(words)}%" if words else "%"


def _normalize_scheme_text(text: str) -> str:
    return " ".join(str(text or "").lower().replace(".", " ").replace(",", " ").split())


def _normalize_lookup_text(text: object) -> str:
    value = str(text or "").lower().replace("&", " and ")
    value = value.replace("unit linked insurance plan", " ")
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"(?<=[a-z])(?=\d)", " ", value)
    value = re.sub(r"\b(\w+)(?:\s+\1\b)+", r"\1", value)
    return " ".join(value.split())


def _scheme_name_for_matching(text: str) -> str:
    value = " ".join(str(text or "").replace("\xa0", " ").split()).strip()
    value = re.sub(r"(?i)^scheme(?:\s+name)?\s*:\s*", "", value)
    return value.rstrip(" .")


def _snapshot_matches_amc(
    amc_code: str,
    snapshot_amc_name: str,
) -> bool:
    normalized = _normalize_lookup_text(snapshot_amc_name)
    aliases = {
        "hdfc": ("hdfc",),
        "sbi": ("sbi",),
        "icici": ("icici",),
        "axis": ("axis",),
        "ppfas": ("ppfas", "parag parikh"),
        "nippon": ("nippon",),
        "motilal": ("motilal",),
        "mirae": ("mirae",),
        "uti": ("uti",),
        "dsp": ("dsp",),
        "kotak": ("kotak",),
        "aditya_birla": ("aditya birla", "birla sun life"),
        "absl": ("aditya birla", "birla sun life"),
    }.get(str(amc_code or "").strip().lower(), ())
    return bool(normalized and aliases and any(alias in normalized for alias in aliases))


def _build_relaxed_ilike_pattern(text: str) -> str:
    tokens = [token for token in _normalize_lookup_text(text).split() if token]
    removable = {
        "fund",
        "plan",
        "option",
        "direct",
        "regular",
        "growth",
        "idcw",
        "dividend",
        "cumulative",
        "daily",
        "weekly",
        "monthly",
        "quarterly",
        "half",
        "yearly",
        "annual",
        "and",
        "etf",
        "exchange",
        "traded",
        "mf",
    }
    filtered = [token for token in tokens if token not in removable]
    base = filtered if filtered else tokens
    return f"%{'%'.join(base)}%" if base else "%"


def _pick_best_scheme_candidate(target_name: str, candidates: list[dict[str, Any]]) -> dict[str, Any]:
    target_text = _normalize_scheme_text(target_name)
    target_tokens = set(target_text.split())
    wants_direct = "direct" in target_tokens
    wants_regular = "regular" in target_tokens
    wants_growth = "growth" in target_tokens or "cumulative" in target_tokens
    wants_idcw = "idcw" in target_tokens or "dividend" in target_tokens

    def score(candidate: dict[str, Any]) -> tuple[int, int, int]:
        candidate_name = str(candidate.get("scheme_name") or "")
        candidate_text = _normalize_scheme_text(candidate_name)
        candidate_tokens = set(candidate_text.split())
        overlap = len(target_tokens & candidate_tokens)
        value = overlap * 20
        if target_text and target_text in candidate_text:
            value += 60
        if "direct" in candidate_tokens:
            value += 12 if wants_direct else 8
        if "regular" in candidate_tokens:
            value += 10 if wants_regular else -8
        if ("growth" in candidate_tokens or "cumulative" in candidate_tokens):
            value += 8 if wants_growth else 5
        if ("idcw" in candidate_tokens or "dividend" in candidate_tokens):
            value += 8 if wants_idcw else -12
        return value, overlap, -len(candidate_tokens)

    ordered = sorted(candidates, key=score, reverse=True)
    return ordered[0]


def _select_best_scheme_candidate(target_name: str, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
    deduped: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        code = str(candidate.get("scheme_code") or "").strip()
        if not code:
            continue
        deduped[code] = candidate
    unique_candidates = list(deduped.values())
    if not unique_candidates:
        return None

    target_family = _normalize_family_scheme_name(target_name)
    scored: list[tuple[float, dict[str, Any]]] = []
    for candidate in unique_candidates:
        candidate_family = _normalize_family_scheme_name(candidate.get("scheme_name"))
        confidence = match_scheme_name(target_family, candidates=[candidate_family]).confidence
        scored.append((confidence, candidate))
    best_confidence = max(score for score, _candidate in scored)
    family_candidates = [
        candidate
        for score, candidate in scored
        if score >= best_confidence - 0.01
    ]
    return _pick_best_scheme_candidate(target_name, family_candidates)


_FAMILY_CATEGORY_SUBS = (
    (re.compile(r"\bfund\s+of\s+funds?\b"), "fof"),
    (re.compile(r"\bflexi\s+cap\b"), "flexicap"),
    (re.compile(r"\bmid\s+cap\b"), "midcap"),
    (re.compile(r"\bsmall\s+cap\b"), "smallcap"),
    (re.compile(r"\blarge\s+cap\b"), "largecap"),
)

_FAMILY_PLAN_QUALIFIER_WORDS = {
    "plan",
    "option",
    "direct",
    "regular",
    "retail",
    "institutional",
    "growth",
    "idcw",
    "dividend",
    "cumulative",
    "payout",
    "payment",
    "reinvestment",
    "bonus",
    "of",
    "daily",
    "weekly",
    "monthly",
    "quarterly",
    "half",
    "yearly",
    "annual",
}


def _apply_family_category_subs(text: str) -> str:
    for pattern, replacement in _FAMILY_CATEGORY_SUBS:
        text = pattern.sub(replacement, text)
    return text


def _normalize_family_scheme_name(value: object) -> str:
    # Plan/option qualifier words like "regular", "growth", "direct" only ever function
    # as noise at the *end* of a scheme name (AMFI's "<Scheme Name> - <Plan> - <Option>"
    # convention, e.g. "... - Growth - Regular Plan"). Stripping them unconditionally is
    # wrong when a word like "Regular" is part of the scheme's own brand name (e.g.
    # "Regular Savings Fund") rather than a trailing plan qualifier -- that collapsed
    # two genuinely different schemes into one family and made one inherit the other's
    # benchmark (GitHub issue #2). Peeling recognized qualifier words off the *end* of
    # the token list, one at a time, until a real word is hit handles this correctly
    # regardless of whether the source separates the qualifier suffix with a spaced
    # hyphen ("Fund - Direct Plan"), an unspaced one ("Fund-Direct Growth", as used
    # inconsistently in mutual_fund_core_snapshot), or no separator at all.
    text = _apply_family_category_subs(_normalize_lookup_text(value))
    tokens = text.split()
    while len(tokens) > 1 and tokens[-1] in _FAMILY_PLAN_QUALIFIER_WORDS:
        tokens.pop()
    return " ".join(tokens)


def _is_direct_growth_name(name: object) -> bool:
    text = _normalize_scheme_text(str(name or ""))
    return "direct" in text and ("growth" in text or "cumulative" in text)


def _has_plan_or_option_marker(name: object) -> bool:
    text = _normalize_scheme_text(str(name or ""))
    markers = (
        "direct",
        "regular",
        "growth",
        "idcw",
        "dividend",
        "monthly",
        "weekly",
        "daily",
        "quarterly",
        "half yearly",
        "annual",
        "cumulative",
    )
    return any(marker in text for marker in markers)


def _merge_sources(*values: object) -> str:
    ordered: list[str] = []
    for value in values:
        for part in str(value or "").split("+"):
            clean = part.strip()
            if clean and clean not in ordered:
                ordered.append(clean)
    return "+".join(ordered)


def _truthy_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}





def _amc_lookup_patterns(amc_code: str) -> list[str]:
    key = str(amc_code or "").strip().lower()
    labels = {
        "hdfc": ["hdfc"],
        "sbi": ["sbi"],
        "icici": ["icici"],
        "ppfas": ["ppfas", "parag", "parikh"],
        "mirae": ["mirae"],
    }.get(key, [key])
    return [f"%{label}%" for label in labels if label]


def _merge_parse_outcomes(primary: dict[str, Any], secondary: dict[str, Any]) -> dict[str, Any]:
    severity = {
        "failed": 5,
        "error": 5,
        "fallback_needs_review": 4,
        "needs_review": 4,
        "parsed_partial": 3,
        "partial": 3,
        "parsed": 2,
        "ok": 2,
        "skipped": 1,
    }
    s1 = str(primary.get("status") or "").strip().lower()
    s2 = str(secondary.get("status") or "").strip().lower()
    selected = primary if severity.get(s1, 0) >= severity.get(s2, 0) else secondary

    merged = dict(selected)
    merged["factsheet"] = primary
    merged["holdings"] = secondary
    return merged


def _attach_extraction_metadata(result: dict[str, Any], classification: DocumentClassification) -> dict[str, Any]:
    enriched = dict(result)
    enriched.setdefault("extractor_type", "deterministic")
    enriched["document_classification"] = classification.to_dict()
    return enriched


def _irrelevant_document_issue(document: dict[str, Any]) -> str | None:
    icici_quant_issue = _icici_quant_file_issue(document)
    if icici_quant_issue:
        return icici_quant_issue

    ppfas_legacy_issue = _legacy_ppfas_xls_issue(document)
    if ppfas_legacy_issue:
        return ppfas_legacy_issue

    month_mismatch = _report_month_mismatch_issue(document)
    if month_mismatch:
        return month_mismatch

    values = [
        document.get("source_url"),
        document.get("file_name"),
        document.get("discovery_page_url"),
    ]
    text = " ".join(str(value or "").lower() for value in values)
    blocked_markers = (
        "aspxerrorpath=",
        "/error?",
        "/error/",
        "statement-of-additional-information",
        "statement of additional information",
        "/moa-and-aoa/",
        "moa-and-aoa",
        "valuation-update",
        "update on valuation",
        "pms fee",
        "fee illustration",
        "voting policy",
        "addendum",
        "notice",
    )
    for marker in blocked_markers:
        if marker in text:
            return f"skipped_irrelevant_document:{marker}"
    return None


def _icici_quant_file_issue(document: dict[str, Any]) -> str | None:
    amc_code = str(document.get("amc_code") or "").strip().lower()
    if amc_code != "icici":
        return None
    values = [
        document.get("source_url"),
        document.get("file_name"),
        document.get("storage_key"),
        document.get("storage_path"),
    ]
    text = " ".join(str(value or "").lower() for value in values)
    if "quants" in text or "quant" in text:
        return "skipped_irrelevant_document:icici_quant_file"
    return None


def _legacy_ppfas_xls_issue(document: dict[str, Any]) -> str | None:
    amc_code = str(document.get("amc_code") or "").strip().lower()
    document_type = str(document.get("document_type") or "").strip().lower()
    if amc_code != "ppfas" or document_type != "portfolio_disclosure":
        return None
    values = [
        document.get("source_url"),
        document.get("file_name"),
        document.get("storage_key"),
        document.get("storage_path"),
    ]
    text = " ".join(str(value or "").lower() for value in values)
    normalized_text = unquote(text).replace("_", " ")
    if ".xls" not in text or ".xlsx" in text or "monthly portfolio report" not in normalized_text:
        return None
    source_month = _source_month_from_text(text)
    if source_month and source_month.year < 2026:
        return "skipped_irrelevant_document:legacy_ppfas_xls_before_supported_window"
    return None


def _report_month_mismatch_issue(document: dict[str, Any]) -> str | None:
    report_month = _to_date_or_none(document.get("report_month"))
    if not report_month:
        return None
    document_type = str(
        document.get("document_type") or document.get("source_document_type") or ""
    ).strip().lower()
    if document_type in FACTSHEET_SUPPORTED_DOCUMENT_TYPES:
        # Factsheet filenames commonly use the publication month. The parser
        # validates their actual reporting month from the downloaded content.
        return None

    values = [
        document.get("source_url"),
        document.get("file_name"),
        document.get("storage_key"),
        document.get("storage_path"),
    ]
    text = " ".join(str(value or "").lower() for value in values)
    source_month = _source_month_from_text(text)
    if not source_month:
        return None

    if source_month.year == report_month.year and source_month.month == report_month.month:
        return None
    return f"skipped_irrelevant_document:report_month_mismatch:{source_month.isoformat()}!={report_month.isoformat()}"


def _source_month_from_text(text: str) -> date | None:
    text = unquote(str(text or "")).lower().replace("_", " ")
    month_names = {
        "jan": 1,
        "january": 1,
        "feb": 2,
        "february": 2,
        "mar": 3,
        "march": 3,
        "apr": 4,
        "april": 4,
        "may": 5,
        "jun": 6,
        "june": 6,
        "jul": 7,
        "july": 7,
        "aug": 8,
        "august": 8,
        "sep": 9,
        "sept": 9,
        "september": 9,
        "oct": 10,
        "october": 10,
        "nov": 11,
        "november": 11,
        "dec": 12,
        "december": 12,
    }
    name_pattern = "|".join(sorted(month_names, key=len, reverse=True))
    today = datetime.now(timezone.utc).date()
    limit_date = date(today.year, today.month, 1)

    for match in re.finditer(r"\b(0?[1-9]|[12]\d|3[01])[.\-/](0?[1-9]|1[0-2])[.\-/](20\d{2})\b", text):
        year = int(match.group(3))
        parsed = date(year, int(match.group(2)), 1)
        if 2000 <= year and parsed <= limit_date:
            return parsed
    for match in re.finditer(rf"\b\d{{1,2}}[-_\s]+({name_pattern})[-_\s]+(20\d{{2}})\b", text):
        year = int(match.group(2))
        parsed = date(year, month_names[match.group(1)], 1)
        if 2000 <= year and parsed <= limit_date:
            return parsed
    for match in re.finditer(rf"\b({name_pattern})[-_\s]+\d{{1,2}}[-_\s]+(20\d{{2}})\b", text):
        year = int(match.group(2))
        parsed = date(year, month_names[match.group(1)], 1)
        if 2000 <= year and parsed <= limit_date:
            return parsed
    for match in re.finditer(rf"\b({name_pattern})[-_\s]+(20\d{{2}})\b", text):
        year = int(match.group(2))
        parsed = date(year, month_names[match.group(1)], 1)
        if 2000 <= year and parsed <= limit_date:
            return parsed
    for match in re.finditer(r"\b(20\d{2})[-_/](0[1-9]|1[0-2])\b", text):
        year = int(match.group(1))
        parsed = date(year, int(match.group(2)), 1)
        if 2000 <= year and parsed <= limit_date:
            return parsed
    for match in re.finditer(r"\b(0[1-9]|1[0-2])[-_/](20\d{2})\b", text):
        year = int(match.group(2))
        parsed = date(year, int(match.group(1)), 1)
        if 2000 <= year and parsed <= limit_date:
            return parsed
    for match in re.finditer(r"\b(0[1-9]|[12]\d|3[01])(0[1-9]|1[0-2])(20\d{2})\b", text):
        year = int(match.group(3))
        parsed = date(year, int(match.group(2)), 1)
        if 2000 <= year and parsed <= limit_date:
            return parsed
    return None
