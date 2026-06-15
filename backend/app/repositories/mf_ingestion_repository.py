from __future__ import annotations

from typing import Any

from app.repositories.mutual_fund_repository import MutualFundRepository


class MfIngestionRepository(MutualFundRepository):
    def get_scheme_by_normalized_name(self, normalized_name: str) -> dict[str, Any] | None:
        rows = (
            self.table("mf_schemes")
            .select("id,amc_code,scheme_name,scheme_name_normalized")
            .eq("scheme_name_normalized", normalized_name)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None

    def get_scheme_holdings(self, scheme_id: Any, *, report_month: str | None, limit: int) -> list[dict[str, Any]]:
        query = (
            self.table("mf_scheme_holdings")
            .select(
                "id,report_month,instrument_name,instrument_name_normalized,isin,sector,percent_aum,"
                "source_document_id,source_url,source_row_hash,parser_version,confidence_score,validation_status"
            )
            .eq("scheme_id", scheme_id)
            .order("percent_aum", desc=True)
            .limit(limit)
        )
        if report_month:
            query = query.eq("report_month", report_month)
        return query.execute().data or []

    def get_raw_document_storage(self, source_document_id: str) -> dict[str, Any] | None:
        rows = (
            self.table("mf_raw_documents")
            .select("id,amc_code,report_month,storage_backend,storage_bucket,storage_key")
            .eq("id", source_document_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None
