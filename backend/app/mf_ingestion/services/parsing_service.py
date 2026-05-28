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
from app.mf_ingestion.normalizers.scheme_name_normalizer import match_scheme_name
from app.mf_ingestion.parsers.adapters.hdfc_adapter import HDFCAdapter
from app.mf_ingestion.parsers.adapters.icici_adapter import ICICIAdapter
from app.mf_ingestion.parsers.adapters.mirae_adapter import MiraeAdapter
from app.mf_ingestion.parsers.adapters.ppfas_adapter import PPFASAdapter
from app.mf_ingestion.parsers.adapters.sbi_adapter import SBIAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext
from app.mf_ingestion.parsers.factsheet_parser import FactsheetParser
from app.mf_ingestion.parsers.holdings_parser import HoldingsParser
from app.mf_ingestion.config import get_config
from app.mf_ingestion.storage.r2_store import R2Store, build_safe_key
from app.repositories.stock_repository import StockRepository
from app.mf_ingestion.services.review_service import ReviewService
from app.mf_ingestion.validators.holdings_validator import validate_holdings

logger = logging.getLogger(__name__)

HOLDINGS_SUPPORTED_DOCUMENT_TYPES = {"portfolio_disclosure"}
FACTSHEET_SUPPORTED_DOCUMENT_TYPES = {"factsheet", "ter_disclosure"}
AMC_DISCLOSURE_SOURCE = "amc_disclosure"
OFFICIAL_CORE_SOURCE_MARKERS = ("AMFI TER API", "AMFI AUM API", "TER", "AUM", AMC_DISCLOSURE_SOURCE)
OFFICIAL_HOLDING_SOURCES = ("AMFI scheme-wise disclosure", AMC_DISCLOSURE_SOURCE)


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
            normalized_amc_code = str(amc_code).strip()
            query = query.in_("amc_code", [normalized_amc_code.lower(), normalized_amc_code.upper(), normalized_amc_code])
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
        document_type = str(document.get("document_type") or "").strip().lower()
        irrelevant_issue = _irrelevant_document_issue(document)
        if irrelevant_issue:
            self._mark_document(document_id, "skipped_not_supported", [irrelevant_issue])
            return {"source_document_id": document_id, "status": "skipped", "reason": irrelevant_issue}
        if document_type and document_type not in HOLDINGS_SUPPORTED_DOCUMENT_TYPES and document_type not in FACTSHEET_SUPPORTED_DOCUMENT_TYPES:
            issue = f"unsupported_document_type:{document_type}"
            self._mark_document(document_id, "skipped_not_supported", [issue])
            return {"source_document_id": document_id, "status": "skipped", "reason": issue}

        api_coverage_issue = self._api_coverage_issue(document)
        if api_coverage_issue:
            self._mark_document(document_id, "official_source_covered", [api_coverage_issue])
            return {"source_document_id": document_id, "status": "official_source_covered", "reason": api_coverage_issue}

        resolved_path, temp_downloaded = self._resolve_document_path(document)
        if not resolved_path:
            self._mark_document(document_id, "failed", ["raw_file_missing"])
            return {"source_document_id": document_id, "status": "failed", "reason": "raw_file_missing"}

        try:
            if document_type in FACTSHEET_SUPPORTED_DOCUMENT_TYPES:
                factsheet_result = self._parse_factsheet_document(document, resolved_path)
                # HDFC combined factsheets also contain portfolio tables.
                if amc_code.lower() == "hdfc":
                    adapter = self.adapters.get("hdfc")
                    if adapter:
                        holdings_result = self._parse_holdings_document(document, adapter, resolved_path)
                        return _merge_parse_outcomes(factsheet_result, holdings_result)
                return factsheet_result

            adapter = self.adapters.get(amc_code.lower())
            if not adapter:
                self._mark_document(document_id, "failed", ["adapter_not_found"])
                return {"source_document_id": document_id, "status": "failed", "reason": "adapter_not_found"}
            return self._parse_holdings_document(document, adapter, resolved_path)
        finally:
            if temp_downloaded:
                try:
                    Path(temp_downloaded).unlink(missing_ok=True)
                except Exception:
                    logger.warning("event=temp_file_cleanup_failed path=%s", temp_downloaded)

    def _parse_holdings_document(self, document: dict[str, Any], adapter: Any, file_path: str) -> dict[str, Any]:
        document_id = str(document.get("id"))
        amc_code = str(document.get("amc_code") or "")

        if document.get("parse_status") != "needs_reparse" and self._already_parsed(document_id):
            self._mark_document(document_id, "parsed", ["already_parsed_for_document"])
            return {"source_document_id": document_id, "status": "skipped", "reason": "already_parsed"}

        if supabase:
            try:
                supabase.table("mf_scheme_holdings").delete().eq("source_document_id", document_id).execute()
                supabase.table("mf_scheme_monthly_metrics").delete().eq("source_document_id", document_id).execute()
                supabase.table("mf_parse_review_queue").delete().eq("source_document_id", document_id).execute()
            except Exception as e:
                logger.warning("event=cleanup_failed source_document_id=%s reason=%s", document_id, e)

        parser = HoldingsParser(adapter)
        try:
            parsed_documents = parser.parse_many(
                file_path,
                ParseContext(
                    source_document_id=document_id,
                    source_url=str(document.get("source_url") or ""),
                    report_month=_to_date_or_none(document.get("report_month")),
                ),
            )
        except Exception as exc:
            logger.exception("event=parse_failed source_document_id=%s reason=%s", document_id, exc)
            self._mark_document(document_id, "failed", [f"parse_exception:{type(exc).__name__}"])
            return {"source_document_id": document_id, "status": "failed", "reason": "parse_exception"}

        if not parsed_documents:
            issue = "holdings_not_found_in_document"
            self._upload_parse_debug_snapshot(
                document=document,
                artifact="holdings_parse_failure",
                payload=self._build_parse_failure_debug_payload(file_path=file_path, reason=issue),
            )
            self._mark_document(document_id, "needs_review", [issue])
            return {"source_document_id": document_id, "status": "needs_review", "reason": issue}

        results: list[dict[str, Any]] = []
        review_needed_overall = False
        merged_issues: list[str] = []
        inserted_total = 0
        candidates = self._load_scheme_candidates(amc_code)

        for parsed in parsed_documents:
            parsed_scheme_name = str(parsed.scheme_name or "").strip()
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
                            "source_row_hash": f"{scheme_id}|{_source_hash(row)}",
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
            else:
                if parsed.report_month:
                    self._sync_amc_derived_views(
                        amc_code=amc_code,
                        scheme_name=scheme_match.canonical_name,
                        report_month=parsed.report_month,
                        source_document_id=document_id,
                        source_url=str(document.get("source_url") or ""),
                        parser_version=str(document.get("parser_version") or ""),
                        holdings=parsed.holdings,
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
                    "validation_issues": validation.issues,
                }
            )

        dedup_issues = sorted(set(merged_issues))
        status = "needs_review" if review_needed_overall else "parsed"
        if review_needed_overall and inserted_total > 0:
            status = "parsed_partial"
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
                "schemes": results,
            },
        )
        if len(results) == 1:
            result = results[0]
            return {
                "source_document_id": document_id,
                "status": status,
                "scheme_name": result["scheme_name"],
                "scheme_match_confidence": result["scheme_match_confidence"],
                "confidence_score": result["confidence_score"],
                "inserted_holdings": result["inserted_holdings"],
                "validation_issues": result["validation_issues"],
            }
        return {
            "source_document_id": document_id,
            "status": status,
            "parsed_schemes": len(results),
            "inserted_holdings": inserted_total,
            "validation_issues": dedup_issues,
        }

    def _parse_factsheet_document(self, document: dict[str, Any], file_path: str) -> dict[str, Any]:
        document_id = str(document.get("id"))
        amc_code = str(document.get("amc_code") or "")
        report_month = _to_date_or_none(document.get("report_month"))
        parse_context = ParseContext(
            source_document_id=document_id,
            source_url=str(document.get("source_url") or ""),
            report_month=report_month,
        )
        try:
            records = self.factsheet_parser.parse(file_path, parse_context)
        except Exception as exc:
            logger.exception("event=factsheet_parse_failed source_document_id=%s reason=%s", document_id, exc)
            self._mark_document(document_id, "failed", [f"factsheet_parse_exception:{type(exc).__name__}"])
            return {"source_document_id": document_id, "status": "failed", "reason": "factsheet_parse_exception"}

        if not records:
            issue = "factsheet_fields_not_extracted"
            self._mark_document(document_id, "needs_review", [issue])
            return {"source_document_id": document_id, "status": "needs_review", "reason": issue}

        updated = 0
        unmatched = 0
        for record in records:
            matched = self._upsert_amc_core_fields(
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
                    }
                    for record in records
                ],
            },
        )
        return {
            "source_document_id": document_id,
            "status": status,
            "updated_schemes": updated,
            "unmatched_schemes": unmatched,
            "validation_issues": issues,
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

    def _api_coverage_issue(self, document: dict[str, Any]) -> str | None:
        if not _truthy_env("ENABLE_MF_OFFICIAL_SOURCE_PARSER_BYPASS", True):
            return None
        document_type = str(document.get("document_type") or "").strip().lower()
        amc_code = str(document.get("amc_code") or "").strip().lower()
        report_month = _to_date_or_none(document.get("report_month"))
        if not document_type or not amc_code or not report_month:
            return None

        factsheet_covered = self._official_factsheet_covers_document(amc_code, report_month)
        holdings_covered = self._official_holdings_cover_document(amc_code, report_month)

        if document_type in HOLDINGS_SUPPORTED_DOCUMENT_TYPES:
            return None
        if document_type in FACTSHEET_SUPPORTED_DOCUMENT_TYPES:
            if amc_code == "hdfc":
                return None
            if factsheet_covered:
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
                response = (
                    client.table("mutual_fund_core_snapshot")
                    .select("scheme_code,amc_name,data_source,provider_payload,aum,expense_ratio,benchmark,fund_manager")
                    .ilike("amc_name", pattern)
                    .limit(1000)
                    .execute()
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
        for row in self._official_core_rows_for_amc(amc_code):
            if any(row.get(field) not in (None, "") for field in ("aum", "expense_ratio", "benchmark", "fund_manager")):
                return True
        return False

    def _official_holdings_cover_document(self, amc_code: str, report_month: date) -> bool:
        client = self.repository.supabase if self.repository else supabase
        if not client:
            return False
        scheme_codes = [str(row.get("scheme_code")) for row in self._official_core_rows_for_amc(amc_code) if row.get("scheme_code")]
        if not scheme_codes:
            return False
        code_values: list[Any] = []
        for code in scheme_codes:
            code_values.append(int(code) if code.isdigit() else code)
        try:
            response = (
                client.table("mutual_fund_holdings")
                .select("scheme_code,source,as_of_date")
                .eq("as_of_date", report_month.isoformat())
                .in_("scheme_code", code_values)
                .limit(50)
                .execute()
            )
            return any(_is_official_holding_source(row.get("source")) for row in (response.data or []))
        except Exception:
            logger.exception("event=official_holdings_coverage_lookup_failed amc_code=%s report_month=%s", amc_code, report_month)
            return False

    def _mark_document(self, source_document_id: str, status: str, issues: list[str]) -> None:
        supabase.table("mf_raw_documents").update(
            {
                "parse_status": status,
                "validation_issues": issues,
                "parsed_at": datetime.now(timezone.utc).isoformat(),
            }
        ).eq("id", source_document_id).execute()
        if status in {"api_covered", "official_source_covered", "parsed", "parsed_partial", "skipped_not_supported", "skipped_no_source_data"}:
            try:
                supabase.table("mf_parse_review_queue").delete().eq("source_document_id", source_document_id).execute()
            except Exception:
                logger.warning("event=review_queue_cleanup_failed source_document_id=%s status=%s", source_document_id, status)

    def _sync_amc_derived_views(
        self,
        amc_code: str,
        scheme_name: str,
        report_month: date,
        source_document_id: str,
        source_url: str,
        parser_version: str,
        holdings: list[dict[str, Any]],
    ) -> None:
        scheme_code = self._resolve_scheme_code_for_scheme(scheme_name)
        if not scheme_code:
            logger.info(
                "event=amc_derived_sync_skipped reason=scheme_code_not_found scheme_name=%s amc_code=%s",
                scheme_name,
                amc_code,
            )
            return

        family_id = self._resolve_family_id_for_scheme(scheme_code)
        self._upsert_mutual_fund_holdings(
            scheme_code,
            report_month,
            holdings,
            source_document_id,
            source_url,
            parser_version,
            family_id,
        )
        self._upsert_mutual_fund_sectors(
            scheme_code,
            holdings,
            source_document_id,
            source_url,
            report_month,
            family_id,
        )
        self._upsert_mutual_fund_core_trace(
            scheme_code=scheme_code,
            scheme_name=scheme_name,
            source_document_id=source_document_id,
            source_url=source_url,
            report_month=report_month,
        )

    def _resolve_scheme_code_for_scheme(self, scheme_name: str) -> str | None:
        candidates: list[dict[str, Any]] = []
        patterns = [
            _build_ilike_pattern(scheme_name),
            _build_relaxed_ilike_pattern(scheme_name),
        ]
        seen_patterns = {pattern for pattern in patterns if pattern and pattern != "%"}
        if not seen_patterns:
            seen_patterns = {"%"}

        for pattern in seen_patterns:
            for table in ("mutual_fund_core_snapshot", "mutual_funds"):
                try:
                    result = (
                        supabase.table(table)
                        .select("scheme_code,scheme_name")
                        .ilike("scheme_name", pattern)
                        .limit(350)
                        .execute()
                    )
                    candidates.extend(result.data or [])
                except Exception:
                    logger.exception("event=scheme_code_lookup_failed table=%s scheme_name=%s", table, scheme_name)
                    continue

        if not candidates:
            return None

        best = _select_best_scheme_candidate(scheme_name, candidates)
        if not best:
            return None
        code = str(best.get("scheme_code") or "").strip()
        return code or None

    def _upsert_mutual_fund_holdings(
        self,
        scheme_code: str,
        report_month: date,
        holdings: list[dict[str, Any]],
        source_document_id: str,
        source_url: str,
        parser_version: str,
        family_id: str | None,
    ) -> None:
        if not holdings:
            return
        if not str(scheme_code).isdigit():
            logger.info("event=amc_holdings_sync_skipped reason=non_numeric_scheme_code scheme_code=%s", scheme_code)
            return

        payload: list[dict[str, Any]] = []
        as_of_date = report_month.isoformat()
        for row in holdings:
            security_name = str(row.get("instrument_name") or "").strip()
            if not security_name:
                continue
            payload.append(
                {
                    "scheme_code": int(scheme_code),
                    "as_of_date": as_of_date,
                    "family_id": family_id,
                    "security_name": security_name,
                    "isin": row.get("isin"),
                    "sector": row.get("sector"),
                    "weight_pct": row.get("percent_aum"),
                    "source": AMC_DISCLOSURE_SOURCE,
                    "provider_payload": {
                        "source_document_id": source_document_id,
                        "source_url": source_url,
                        "parser_version": parser_version,
                    },
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        if not payload:
            return
        self._archive_and_trim_holdings(
            scheme_code=int(scheme_code),
            family_id=family_id,
            current_report_month=as_of_date,
        )
        supabase.table("mutual_fund_holdings").upsert(
            payload,
            on_conflict="scheme_code,as_of_date,security_name,isin",
        ).execute()

    def _upsert_mutual_fund_sectors(
        self,
        scheme_code: str,
        holdings: list[dict[str, Any]],
        source_document_id: str,
        source_url: str,
        report_month: date,
        family_id: str | None,
    ) -> None:
        sector_totals: dict[str, float] = {}
        sector_counts: dict[str, int] = {}
        for row in holdings:
            sector_name = str(row.get("sector") or "").strip()
            weight = row.get("percent_aum")
            if not sector_name or weight in (None, ""):
                continue
            try:
                weight_value = float(weight)
            except (TypeError, ValueError):
                continue
            sector_totals[sector_name] = sector_totals.get(sector_name, 0.0) + weight_value
            sector_counts[sector_name] = sector_counts.get(sector_name, 0) + 1

        if not sector_totals:
            return

        rows = []
        for sector_name, total_weight in sector_totals.items():
            rows.append(
                {
                    "scheme_code": str(scheme_code),
                    "family_id": family_id,
                    "sector": sector_name,
                    "weight_pct": round(total_weight, 6),
                    "stock_count": sector_counts.get(sector_name),
                    "source": AMC_DISCLOSURE_SOURCE,
                    "provider_payload": {
                        "source_document_id": source_document_id,
                        "source_url": source_url,
                        "report_month": report_month.isoformat(),
                    },
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        self._archive_and_replace_sectors(
            scheme_code=str(scheme_code),
            family_id=family_id,
            report_month=report_month,
        )
        supabase.table("mutual_fund_sectors").upsert(rows, on_conflict="scheme_code,sector").execute()

    def _upsert_mutual_fund_core_trace(
        self,
        scheme_code: str,
        scheme_name: str,
        source_document_id: str,
        source_url: str,
        report_month: date,
    ) -> None:
        existing: dict[str, Any] = {}
        try:
            response = (
                supabase.table("mutual_fund_core_snapshot")
                .select("scheme_code,data_source,provider_payload,scheme_name")
                .eq("scheme_code", str(scheme_code))
                .limit(1)
                .execute()
            )
            existing = (response.data or [{}])[0] or {}
        except Exception:
            logger.exception("event=core_snapshot_lookup_failed scheme_code=%s", scheme_code)

        provider_payload = existing.get("provider_payload") if isinstance(existing.get("provider_payload"), dict) else {}
        amc_trace = provider_payload.get("amc_trace") if isinstance(provider_payload.get("amc_trace"), dict) else {}
        amc_trace["holdings"] = {
            "source_document_id": source_document_id,
            "source_url": source_url,
            "report_month": report_month.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        amc_trace["sector_allocation"] = {
            "source_document_id": source_document_id,
            "source_url": source_url,
            "report_month": report_month.isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        provider_payload["amc_trace"] = amc_trace

        merged_source = _merge_sources(existing.get("data_source"), AMC_DISCLOSURE_SOURCE)
        self._upsert_core_snapshot_row(
            {
                "scheme_code": str(scheme_code),
                "scheme_name": existing.get("scheme_name") or scheme_name,
                "data_source": merged_source,
                "provider_payload": provider_payload,
            }
        )

    def _upsert_amc_core_fields(
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
    ) -> bool:
        scheme_code = self._resolve_scheme_code_for_scheme(scheme_name)
        if not scheme_code:
            logger.info(
                "event=amc_core_field_sync_skipped reason=scheme_code_not_found scheme_name=%s amc_code=%s",
                scheme_name,
                amc_code,
            )
            return False

        existing = self.repository.get_mutual_fund_core_snapshot(scheme_code) or {}
        provider_payload = existing.get("provider_payload") if isinstance(existing.get("provider_payload"), dict) else {}
        amc_trace = provider_payload.get("amc_trace") if isinstance(provider_payload.get("amc_trace"), dict) else {}
        updated_at = datetime.now(timezone.utc).isoformat()
        report_month_iso = report_month.isoformat() if report_month else None

        field_values: dict[str, Any] = {
            "aum": aum,
            "expense_ratio": expense_ratio,
            "benchmark": benchmark,
            "fund_manager": fund_manager,
        }
        parsed_fields = {key: value for key, value in field_values.items() if value not in (None, "")}
        if not parsed_fields:
            return False
        write_fields = {
            key: value
            for key, value in parsed_fields.items()
            if existing.get(key) in (None, "")
        }
        if not write_fields:
            return True

        for field_name, value in write_fields.items():
            amc_trace[field_name] = {
                "source_document_id": source_document_id,
                "source_url": source_url,
                "report_month": report_month_iso,
                "parser_version": parser_version,
                "value": value,
                "updated_at": updated_at,
            }
        provider_payload["amc_trace"] = amc_trace

        row: dict[str, Any] = {
            "scheme_code": str(scheme_code),
            "scheme_name": existing.get("scheme_name") or scheme_name,
            "data_source": _merge_sources(existing.get("data_source"), AMC_DISCLOSURE_SOURCE),
            "provider_payload": provider_payload,
        }
        for field_name, value in write_fields.items():
            row[field_name] = value

        self._upsert_core_snapshot_row(row)
        return True

    def _upsert_core_snapshot_row(self, row: dict[str, Any]) -> None:
        if self.repository and self.repository.supabase:
            self.repository.upsert_mutual_fund_core_snapshot_rows([row])
            return
        payload = dict(row)
        payload["last_updated"] = datetime.now(timezone.utc).isoformat()
        supabase.table("mutual_fund_core_snapshot").upsert(payload, on_conflict="scheme_code").execute()

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
        snapshot = self.repository.get_mutual_fund_core_snapshot(scheme_code) or {}
        provider_payload = snapshot.get("provider_payload") if isinstance(snapshot.get("provider_payload"), dict) else {}
        value = provider_payload.get("family_id") or snapshot.get("family_id")
        if value in (None, ""):
            return None
        return str(value)

    def _archive_and_trim_holdings(self, *, scheme_code: int, family_id: str | None, current_report_month: str) -> None:
        query = supabase.table("mutual_fund_holdings").select("*").eq("source", AMC_DISCLOSURE_SOURCE).eq("scheme_code", scheme_code)
        if family_id:
            query = query.eq("family_id", family_id)
        rows = query.execute().data or []
        stale_rows = [row for row in rows if str(row.get("as_of_date") or "") != current_report_month]
        if stale_rows:
            self._archive_portfolio_rows(
                report_month=current_report_month,
                family_id=family_id,
                scheme_code=str(scheme_code),
                payload={"table": "mutual_fund_holdings", "rows": stale_rows},
            )
            dates = sorted({str(row.get("as_of_date")) for row in stale_rows if row.get("as_of_date")})
            for as_of_date in dates:
                delete_query = (
                    supabase.table("mutual_fund_holdings")
                    .delete()
                    .eq("source", AMC_DISCLOSURE_SOURCE)
                    .eq("scheme_code", scheme_code)
                    .eq("as_of_date", as_of_date)
                )
                if family_id:
                    delete_query = delete_query.eq("family_id", family_id)
                delete_query.execute()

    def _archive_and_replace_sectors(self, *, scheme_code: str, family_id: str | None, report_month: date) -> None:
        query = supabase.table("mutual_fund_sectors").select("*").eq("source", AMC_DISCLOSURE_SOURCE).eq("scheme_code", scheme_code)
        if family_id:
            query = query.eq("family_id", family_id)
        existing = query.execute().data or []
        if existing:
            self._archive_portfolio_rows(
                report_month=report_month.isoformat(),
                family_id=family_id,
                scheme_code=scheme_code,
                payload={"table": "mutual_fund_sectors", "rows": existing},
            )
            delete_query = (
                supabase.table("mutual_fund_sectors")
                .delete()
                .eq("source", AMC_DISCLOSURE_SOURCE)
                .eq("scheme_code", scheme_code)
            )
            if family_id:
                delete_query = delete_query.eq("family_id", family_id)
            delete_query.execute()

    def _archive_portfolio_rows(self, *, report_month: str, family_id: str | None, scheme_code: str, payload: dict[str, Any]) -> None:
        if not self.r2_store.enabled:
            return
        month_segment = str(report_month)[:7] if report_month else "unknown-month"
        owner = family_id or f"scheme-{scheme_code}"
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        key = build_safe_key(
            "cold",
            "portfolio",
            owner,
            f"report_month={month_segment}",
            f"part-{ts}.parquet",
        )
        data = payload.get("rows") if isinstance(payload.get("rows"), list) else []
        content, content_type = _encode_archive_payload(data)
        self.r2_store.upload_bytes(
            key=key,
            content=content,
            bucket=self.config.r2_cold_bucket,
            content_type=content_type,
            metadata={
                "report_month": month_segment,
                "table": str(payload.get("table") or ""),
                "rows": str(len(data)),
            },
        )

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


def _build_ilike_pattern(text: str) -> str:
    words = [word for word in str(text or "").lower().replace(".", " ").replace(",", " ").split() if word]
    return f"%{'%'.join(words)}%" if words else "%"


def _normalize_scheme_text(text: str) -> str:
    return " ".join(str(text or "").lower().replace(".", " ").replace(",", " ").split())


def _build_relaxed_ilike_pattern(text: str) -> str:
    tokens = [token for token in _normalize_scheme_text(text).split() if token]
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

    direct_growth_candidates = [candidate for candidate in unique_candidates if _is_direct_growth_name(candidate.get("scheme_name"))]
    if direct_growth_candidates:
        return _pick_best_scheme_candidate(target_name, direct_growth_candidates)

    has_variant_candidates = any(_has_plan_or_option_marker(candidate.get("scheme_name")) for candidate in unique_candidates)
    if has_variant_candidates:
        return _pick_best_scheme_candidate(target_name, unique_candidates)
    return _pick_best_scheme_candidate(target_name, unique_candidates)


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


def _is_official_holding_source(value: object) -> bool:
    source = str(value or "")
    return any(marker in source for marker in OFFICIAL_HOLDING_SOURCES)


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


def _irrelevant_document_issue(document: dict[str, Any]) -> str | None:
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


def _report_month_mismatch_issue(document: dict[str, Any]) -> str | None:
    report_month = _to_date_or_none(document.get("report_month"))
    if not report_month:
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
    text = unquote(str(text or "")).lower()
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

    for match in re.finditer(rf"\b\d{{1,2}}[-_\s]+({name_pattern})[-_\s]+(20\d{{2}})\b", text):
        return date(int(match.group(2)), month_names[match.group(1)], 1)
    for match in re.finditer(rf"\b({name_pattern})[-_\s]+(20\d{{2}})\b", text):
        return date(int(match.group(2)), month_names[match.group(1)], 1)
    for match in re.finditer(r"\b(20\d{2})[-_/](0[1-9]|1[0-2])\b", text):
        return date(int(match.group(1)), int(match.group(2)), 1)
    for match in re.finditer(r"\b(0[1-9]|1[0-2])[-_/](20\d{2})\b", text):
        return date(int(match.group(2)), int(match.group(1)), 1)
    return None


def _encode_archive_payload(rows: list[dict[str, Any]]) -> tuple[bytes, str]:
    if not rows:
        return b"", "application/octet-stream"
    try:
        import pandas as pd  # type: ignore

        frame = pd.DataFrame(rows)
        with tempfile.NamedTemporaryFile(prefix="mf_archive_", suffix=".parquet", delete=False) as handle:
            temp_path = Path(handle.name)
        try:
            frame.to_parquet(temp_path, index=False)
            return temp_path.read_bytes(), "application/vnd.apache.parquet"
        finally:
            temp_path.unlink(missing_ok=True)
    except Exception:
        encoded = gzip.compress("\n".join(json.dumps(row, default=str) for row in rows).encode("utf-8"))
        return encoded, "application/gzip"
