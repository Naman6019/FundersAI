from __future__ import annotations

import logging
import zipfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from app.mf_ingestion.constants import EXCEL_EXTENSIONS
from app.mf_ingestion.parsers.adapters.base_adapter import BaseAMCAdapter
from app.mf_ingestion.parsers.base_parser import ParseContext, ParsedDocument
from app.mf_ingestion.parsers.excel_parser import ExcelParser
from app.mf_ingestion.parsers.pdf_table_parser import PDFTableParser
from app.mf_ingestion.parsers.pdf_text_parser import PDFTextParser

logger = logging.getLogger(__name__)
ZIP_MAX_EXCEL_FILES = 2000
ZIP_MAX_MEMBER_BYTES = 50 * 1024 * 1024
ZIP_MAX_TOTAL_UNCOMPRESSED_BYTES = 500 * 1024 * 1024


@dataclass
class ParseDiagnostic:
    level: str
    stage: str
    code: str
    member_name: str | None = None
    sheet_name: str | None = None
    error_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ParseBatchResult:
    records: list[ParsedDocument] = field(default_factory=list)
    diagnostics: list[ParseDiagnostic] = field(default_factory=list)
    successful_sources: int = 0
    empty_sources: int = 0
    failed_sources: int = 0

    @property
    def has_failures(self) -> bool:
        return self.failed_sources > 0


class HoldingsParser:
    def __init__(self, adapter: BaseAMCAdapter) -> None:
        self.adapter = adapter
        self.excel_parser = ExcelParser()
        self.pdf_table_parser = PDFTableParser()
        self.pdf_text_parser = PDFTextParser()

    def parse(self, file_path: str, context: ParseContext) -> ParsedDocument:
        parsed_documents = self.parse_many(file_path, context)
        if not parsed_documents:
            return ParsedDocument(
                scheme_name="",
                report_month=context.report_month,
                holdings=[],
                warnings=["holdings_not_found_in_document"],
                confidence_score=0.0,
            )
        return max(parsed_documents, key=lambda item: len(item.holdings))

    def parse_many(self, file_path: str, context: ParseContext) -> list[ParsedDocument]:
        return self.parse_batch(file_path, context).records

    def parse_batch(self, file_path: str, context: ParseContext) -> ParseBatchResult:
        extension = Path(file_path).suffix.lower()

        if extension in EXCEL_EXTENSIONS:
            try:
                frames = self.excel_parser.parse_all_sheets(file_path)
            except Exception as exc:
                logger.exception("event=excel_document_parse_failed source_document_id=%s", context.source_document_id)
                return ParseBatchResult(
                    diagnostics=[ParseDiagnostic("error", "excel_document", "excel_read_failed", error_type=type(exc).__name__)],
                    failed_sources=1,
                )
            return self._parse_excel_frames_batch(frames, context)

        if extension == ".zip":
            return self._parse_zip_batch(file_path, context)

        pdf_file_many = getattr(self.adapter, "parse_pdf_file_many", None)
        if callable(pdf_file_many):
            try:
                parsed_documents = pdf_file_many(file_path, context)
                if parsed_documents:
                    return ParseBatchResult(records=parsed_documents, successful_sources=1)
            except Exception as exc:
                logger.exception("event=pdf_file_parse_failed source_document_id=%s", context.source_document_id)
                return ParseBatchResult(
                    diagnostics=[ParseDiagnostic("error", "pdf_file", "pdf_file_parse_failed", error_type=type(exc).__name__)],
                    failed_sources=1,
                )

        pdf_text_many = getattr(self.adapter, "parse_pdf_text_many", None)
        if callable(pdf_text_many):
            try:
                pdf_text = self.pdf_text_parser.extract_text(file_path)
                parsed_documents = pdf_text_many(pdf_text, context)
                if parsed_documents:
                    return ParseBatchResult(records=parsed_documents, successful_sources=1)
            except Exception as exc:
                logger.exception("event=pdf_text_many_parse_failed source_document_id=%s", context.source_document_id)
                return ParseBatchResult(
                    diagnostics=[ParseDiagnostic("error", "pdf_text", "pdf_text_parse_failed", error_type=type(exc).__name__)],
                    failed_sources=1,
                )

        try:
            pdf_frames = self.pdf_table_parser.extract_tables(file_path)
        except Exception as exc:
            logger.exception("event=pdf_table_extract_failed source_document_id=%s", context.source_document_id)
            return ParseBatchResult(
                diagnostics=[ParseDiagnostic("error", "pdf_tables", "pdf_table_extract_failed", error_type=type(exc).__name__)],
                failed_sources=1,
            )
        if pdf_frames:
            frame_batch = self._parse_pdf_frames_batch(pdf_frames, context)
            if frame_batch.records or frame_batch.has_failures:
                return frame_batch

            # Backward-safe fallback for adapters that expect all frames together.
            try:
                parsed = self.adapter.parse_holdings([], pdf_frames, "", context)
                if parsed and parsed.holdings:
                    return ParseBatchResult(records=[parsed], successful_sources=1)
            except Exception as exc:
                return ParseBatchResult(
                    diagnostics=[ParseDiagnostic("error", "pdf_tables", "pdf_table_parse_failed", error_type=type(exc).__name__)],
                    failed_sources=1,
                )

        try:
            pdf_text = self.pdf_text_parser.extract_text(file_path)
            parsed = self.adapter.parse_holdings([], [], pdf_text, context)
            if parsed.holdings:
                return ParseBatchResult(records=[parsed], successful_sources=1)
            return ParseBatchResult(
                diagnostics=[ParseDiagnostic("warning", "pdf_text", "holdings_not_found")],
                empty_sources=1,
            )
        except Exception as exc:
            logger.exception("event=pdf_text_parse_failed source_document_id=%s", context.source_document_id)
            return ParseBatchResult(
                diagnostics=[ParseDiagnostic("error", "pdf_text", "pdf_text_parse_failed", error_type=type(exc).__name__)],
                failed_sources=1,
            )

    def _parse_excel_frames(self, frames: list, context: ParseContext) -> list[ParsedDocument]:
        return self._parse_excel_frames_batch(frames, context).records

    def _parse_excel_frames_batch(
        self,
        frames: list,
        context: ParseContext,
        *,
        member_name: str | None = None,
    ) -> ParseBatchResult:
        if not frames:
            return ParseBatchResult(
                diagnostics=[ParseDiagnostic("warning", "excel_sheet", "empty_workbook", member_name=member_name)],
                empty_sources=1,
            )

        by_scheme: dict[str, ParsedDocument] = {}
        result = ParseBatchResult()
        for sheet_index, frame in enumerate(frames):
            try:
                parse_frame_many = getattr(self.adapter, "parse_excel_frame_many", None)
                if callable(parse_frame_many):
                    parsed_documents = parse_frame_many(frame, context)
                else:
                    parsed = self.adapter.parse_holdings([frame], [], "", context)
                    parsed_documents = [parsed]
            except Exception as exc:
                logger.exception("event=excel_sheet_parse_failed source_document_id=%s", context.source_document_id)
                result.failed_sources += 1
                result.diagnostics.append(
                    ParseDiagnostic(
                        "error",
                        "excel_sheet",
                        "sheet_parse_failed",
                        member_name=member_name,
                        sheet_name=f"sheet_{sheet_index + 1}",
                        error_type=type(exc).__name__,
                    )
                )
                continue

            produced = False
            for parsed in parsed_documents:
                if not parsed.holdings:
                    continue
                produced = True
                self._upsert_best_by_scheme(by_scheme, parsed)
            if produced:
                result.successful_sources += 1
            else:
                result.empty_sources += 1
                result.diagnostics.append(
                    ParseDiagnostic(
                        "warning",
                        "excel_sheet",
                        "holdings_not_found",
                        member_name=member_name,
                        sheet_name=f"sheet_{sheet_index + 1}",
                    )
                )

        result.records = list(by_scheme.values())
        return result

    def _parse_zip_documents(self, file_path: str, context: ParseContext) -> list[ParsedDocument]:
        return self._parse_zip_batch(file_path, context).records

    def _parse_zip_batch(self, file_path: str, context: ParseContext) -> ParseBatchResult:
        by_scheme: dict[str, ParsedDocument] = {}
        result = ParseBatchResult()
        try:
            archive = zipfile.ZipFile(file_path)
        except Exception as exc:
            return ParseBatchResult(
                diagnostics=[ParseDiagnostic("error", "zip_archive", "zip_open_failed", error_type=type(exc).__name__)],
                failed_sources=1,
            )
        with archive:
            nested_archives = [
                info.filename
                for info in archive.infolist()
                if Path(info.filename).suffix.lower() in {".zip", ".rar", ".7z", ".tar", ".gz"}
            ]
            for member_name in nested_archives:
                result.failed_sources += 1
                result.diagnostics.append(
                    ParseDiagnostic("error", "zip_member", "nested_archive_not_allowed", member_name=member_name)
                )
            members = sorted(
                [info for info in archive.infolist() if Path(info.filename).suffix.lower() in EXCEL_EXTENSIONS],
                key=lambda info: info.filename,
            )
            if len(members) > ZIP_MAX_EXCEL_FILES:
                result.failed_sources += len(members) - ZIP_MAX_EXCEL_FILES
                result.diagnostics.append(ParseDiagnostic("error", "zip_archive", "zip_member_count_limit"))
                members = members[:ZIP_MAX_EXCEL_FILES]
            total_size = 0
            for member in members:
                member_name = member.filename
                if member.file_size > ZIP_MAX_MEMBER_BYTES:
                    result.failed_sources += 1
                    result.diagnostics.append(
                        ParseDiagnostic("error", "zip_member", "zip_member_size_limit", member_name=member_name)
                    )
                    continue
                total_size += member.file_size
                if total_size > ZIP_MAX_TOTAL_UNCOMPRESSED_BYTES:
                    result.failed_sources += 1
                    result.diagnostics.append(
                        ParseDiagnostic("error", "zip_archive", "zip_total_size_limit", member_name=member_name)
                    )
                    break
                try:
                    member_bytes = archive.read(member_name)
                    member_frames = self.excel_parser.parse_all_sheets_from_bytes(member_bytes)
                    member_result = self._parse_excel_frames_batch(
                        member_frames,
                        context,
                        member_name=member_name,
                    )
                    result.diagnostics.extend(member_result.diagnostics)
                    result.successful_sources += member_result.successful_sources
                    result.empty_sources += member_result.empty_sources
                    result.failed_sources += member_result.failed_sources
                    for parsed in member_result.records:
                        scheme_key = " ".join(str(parsed.scheme_name or "").lower().split())
                        existing = by_scheme.get(scheme_key)
                        if not existing or len(parsed.holdings) > len(existing.holdings):
                            by_scheme[scheme_key] = parsed
                except Exception as exc:
                    logger.exception("event=zip_excel_member_parse_failed file_path=%s member=%s", file_path, member_name)
                    result.failed_sources += 1
                    result.diagnostics.append(
                        ParseDiagnostic(
                            "error",
                            "zip_member",
                            "zip_member_parse_failed",
                            member_name=member_name,
                            error_type=type(exc).__name__,
                        )
                    )
                    continue
        result.records = list(by_scheme.values())
        if not members:
            result.empty_sources += 1
            result.diagnostics.append(ParseDiagnostic("warning", "zip_archive", "zip_no_supported_members"))
        return result

    def _parse_pdf_frames_individually(self, frames: list, context: ParseContext) -> list[ParsedDocument]:
        return self._parse_pdf_frames_batch(frames, context).records

    def _parse_pdf_frames_batch(self, frames: list, context: ParseContext) -> ParseBatchResult:
        by_scheme: dict[str, ParsedDocument] = {}
        result = ParseBatchResult()
        for frame_index, frame in enumerate(frames):
            try:
                parse_frame_many = getattr(self.adapter, "parse_pdf_frame_many", None)
                if callable(parse_frame_many):
                    parsed_documents = parse_frame_many(frame, context)
                else:
                    parsed = self.adapter.parse_holdings([], [frame], "", context)
                    parsed_documents = [parsed]
            except Exception as exc:
                logger.exception("event=pdf_frame_parse_failed source_document_id=%s", context.source_document_id)
                result.failed_sources += 1
                result.diagnostics.append(
                    ParseDiagnostic(
                        "error",
                        "pdf_table",
                        "pdf_frame_parse_failed",
                        sheet_name=f"table_{frame_index + 1}",
                        error_type=type(exc).__name__,
                    )
                )
                continue
            produced = False
            for parsed in parsed_documents:
                if not parsed.holdings:
                    continue
                produced = True
                self._upsert_best_by_scheme(by_scheme, parsed)
            if produced:
                result.successful_sources += 1
            else:
                result.empty_sources += 1
        result.records = list(by_scheme.values())
        return result

    def _upsert_best_by_scheme(self, by_scheme: dict[str, ParsedDocument], parsed: ParsedDocument) -> None:
        scheme_key = " ".join(str(parsed.scheme_name or "").lower().split())
        existing = by_scheme.get(scheme_key)
        if not existing:
            by_scheme[scheme_key] = parsed
            return

        by_scheme[scheme_key] = self._merge_parsed_documents(existing, parsed)

    def _merge_parsed_documents(self, left: ParsedDocument, right: ParsedDocument) -> ParsedDocument:
        deduped: dict[str, dict] = {}
        for row in [*(left.holdings or []), *(right.holdings or [])]:
            name = str(row.get("instrument_name") or "").strip().lower()
            isin = str(row.get("isin") or "").strip().upper()
            key = f"{name}|{isin}" if name or isin else ""
            if not key:
                continue
            existing = deduped.get(key)
            if not existing or float(row.get("percent_aum") or 0.0) > float(existing.get("percent_aum") or 0.0):
                deduped[key] = row

        merged_rows = list(deduped.values())
        total_percent = round(sum(float(row.get("percent_aum") or 0.0) for row in merged_rows), 6)
        all_warnings = set([*(left.warnings or []), *(right.warnings or [])])
        out_of_band_flag = "percent_aum_total_out_of_band"
        if out_of_band_flag in all_warnings:
            all_warnings.discard(out_of_band_flag)
            # Re-evaluate on the merged output instead of preserving fragment-level noise.
            if not (85.0 <= total_percent <= 115.0):
                all_warnings.add(out_of_band_flag)
        month_missing_flag = "report_month_not_detected"
        merged_report_month = right.report_month or left.report_month
        if merged_report_month and month_missing_flag in all_warnings:
            all_warnings.discard(month_missing_flag)
        warnings = sorted(all_warnings)

        return ParsedDocument(
            scheme_name=right.scheme_name or left.scheme_name,
            report_month=merged_report_month,
            holdings=merged_rows,
            metrics={"total_percent_aum": total_percent},
            warnings=warnings,
            confidence_score=max(float(left.confidence_score or 0.0), float(right.confidence_score or 0.0)),
        )
