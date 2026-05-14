from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.database import supabase


class ReviewService:
    def enqueue_document_review(
        self,
        source_document_id: str,
        amc_code: str,
        report_month: str | None,
        source_url: str | None,
        validation_issues: list[str],
        confidence_score: float,
        parser_version: str,
        sample_rows: list[dict[str, Any]],
    ) -> None:
        if not supabase:
            return

        payload = {
            "source_document_id": source_document_id,
            "amc_code": amc_code,
            "report_month": report_month,
            "source_url": source_url,
            "validation_issues": validation_issues,
            "confidence_score": confidence_score,
            "parser_version": parser_version,
            "status": "pending_review",
            "sample_rows": sample_rows,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        supabase.table("mf_parse_review_queue").insert(payload).execute()
