from __future__ import annotations

from typing import Any

from app.database import supabase as default_supabase


class MutualFundRepository:
    def __init__(self, db_client: Any = None):
        self.client = db_client if db_client is not None else default_supabase

    def __bool__(self) -> bool:
        return self.client is not None

    def table(self, name: str) -> Any:
        if self.client is None:
            raise RuntimeError("supabase_unavailable")
        return self.client.table(name)

    def count_raw_documents(self, *, status: str | None = None) -> int:
        query = self.table("mf_raw_documents").select("id", count="exact")
        if status:
            query = query.eq("parse_status", status)
        response = query.execute()
        return int(response.count or 0)

    def latest_raw_document_timestamp(self, *, status: str | None, field: str):
        query = self.table("mf_raw_documents").select(field).order(field, desc=True).limit(5)
        if status:
            query = query.eq("parse_status", status)
        for row in query.execute().data or []:
            value = row.get(field)
            if value:
                return value
        return None

    def search_mutual_funds(self, pattern: str, *, limit: int = 25) -> list[dict[str, Any]]:
        rows = (
            self.table("mutual_fund_core_snapshot")
            .select("*")
            .ilike("scheme_name", pattern)
            .limit(limit)
            .execute()
            .data
            or []
        )
        if rows:
            return rows
        return (
            self.table("mutual_funds")
            .select("*")
            .ilike("scheme_name", pattern)
            .limit(limit)
            .execute()
            .data
            or []
        )

    def get_fund_by_scheme_code(self, scheme_code: Any) -> dict[str, Any] | None:
        code = int(str(scheme_code)) if str(scheme_code).isdigit() else scheme_code
        rows = (
            self.table("mutual_fund_core_snapshot")
            .select("*")
            .eq("scheme_code", code)
            .limit(1)
            .execute()
            .data
            or []
        )
        if rows:
            return rows[0]
        rows = (
            self.table("mutual_funds")
            .select("*")
            .eq("scheme_code", code)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None

    def get_nav_history_rows(self, scheme_code: Any, *, fields: str, limit: int = 5000, desc: bool = False) -> list[dict[str, Any]]:
        code = int(str(scheme_code)) if str(scheme_code).isdigit() else scheme_code
        return (
            self.table("mutual_fund_nav_history")
            .select(fields)
            .eq("scheme_code", code)
            .order("nav_date", desc=desc)
            .limit(limit)
            .execute()
            .data
            or []
        )

    def get_nifty_price_rows(self, *, limit: int = 1100) -> list[dict[str, Any]]:
        return (
            self.table("stock_prices_daily")
            .select("close,date")
            .eq("symbol", "NIFTY")
            .order("date", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )

    def get_latest_holdings(self, scheme_code: Any) -> list[dict[str, Any]]:
        code = int(str(scheme_code)) if str(scheme_code).isdigit() else scheme_code
        return (
            self.table("mutual_fund_holdings")
            .select("as_of_date,security_name,isin,sector,weight_pct,source,provider_payload")
            .eq("scheme_code", code)
            .order("as_of_date", desc=True)
            .order("weight_pct", desc=True)
            .limit(500)
            .execute()
            .data
            or []
        )

    def get_sector_rows(self, scheme_code: Any) -> list[dict[str, Any]]:
        return (
            self.table("mutual_fund_sectors")
            .select("sector,weight_pct,stock_count,source,provider_payload,updated_at")
            .eq("scheme_code", str(scheme_code))
            .order("weight_pct", desc=True)
            .limit(50)
            .execute()
            .data
            or []
        )
