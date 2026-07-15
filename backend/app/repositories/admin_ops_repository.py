from __future__ import annotations

from typing import Any

from app.repositories.mutual_fund_repository import MutualFundRepository


class AdminOpsRepository(MutualFundRepository):
    def recent_provider_runs(self, table_name: str) -> list[dict[str, Any]]:
        return (
            self.table(table_name)
            .select("provider,job_name,status,started_at,finished_at,symbols_attempted,symbols_succeeded,symbols_failed,error_summary,metadata")
            .order("started_at", desc=True)
            .limit(120)
            .execute()
            .data
            or []
        )

    def recent_raw_documents(self) -> list[dict[str, Any]]:
        return (
            self.table("mf_raw_documents")
            .select("amc_code,source_document_type,parse_status,downloaded_at,parsed_at,updated_at")
            .order("downloaded_at", desc=True)
            .limit(12000)
            .execute()
            .data
            or []
        )

    def recent_data_quality_issues(self) -> list[dict[str, Any]]:
        return (
            self.table("data_quality_issues")
            .select("id,symbol,table_name,field_name,issue_type,issue_message,source,detected_at")
            .order("detected_at", desc=True)
            .limit(120)
            .execute()
            .data
            or []
        )

    def count_raw_documents_by_status(self, status: str) -> int:
        return int(
            self.table("mf_raw_documents")
            .select("id", count="exact")
            .eq("parse_status", status)
            .execute()
            .count
            or 0
        )

    def count_review_queue(self) -> int:
        return int(
            self.table("mf_parse_review_queue")
            .select("id", count="exact")
            .eq("status", "pending_review")
            .execute()
            .count
            or 0
        )

    def list_pending_review_items(self, *, limit: int = 100) -> list[dict[str, Any]]:
        return (
            self.table("mf_parse_review_queue")
            .select(
                "source_document_id,amc_code,report_month,validation_issues,confidence_score,"
                "parser_version,status,sample_rows,source_url,created_at,updated_at"
            )
            .eq("status", "pending_review")
            .order("created_at")
            .limit(max(1, min(limit, 500)))
            .execute()
            .data
            or []
        )
