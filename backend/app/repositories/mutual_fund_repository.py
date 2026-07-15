from __future__ import annotations

from typing import Any

from app.database import supabase as default_supabase


def _clean_variant_value(value: Any) -> str | None:
    if value in (None, ""):
        return None
    text = str(value).strip()
    return text or None


def _infer_plan_type(scheme_name: str) -> str | None:
    name = scheme_name.lower()
    if "direct" in name:
        return "Direct"
    if "regular" in name:
        return "Regular"
    return None


def _infer_option_type(scheme_name: str) -> str | None:
    name = scheme_name.lower()
    if "growth" in name:
        return "Growth"
    if "idcw" in name or "dividend" in name:
        return "IDCW"
    return None


def _with_normalized_variant_fields(row: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(row)
    scheme_name = str(normalized.get("scheme_name") or "")
    normalized["plan_type"] = _clean_variant_value(normalized.get("plan_type")) or _infer_plan_type(scheme_name)
    normalized["option_type"] = _clean_variant_value(normalized.get("option_type")) or _infer_option_type(scheme_name)
    return normalized


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

    def search_mutual_funds(
        self,
        pattern: str,
        *,
        limit: int = 25,
        plan_type: str | None = None,
        option_type: str | None = None,
    ) -> list[dict[str, Any]]:
        query_snapshot = self.table("mutual_fund_core_snapshot").select("*").ilike("scheme_name", pattern)
        if plan_type:
            query_snapshot = query_snapshot.ilike("scheme_name", f"%{plan_type}%")
        if option_type:
            query_snapshot = query_snapshot.ilike("scheme_name", f"%{option_type}%")

        rows = query_snapshot.limit(limit).execute().data or []
        if rows:
            return [_with_normalized_variant_fields(row) for row in rows]

        query_mf = self.table("mutual_funds").select("*").ilike("scheme_name", pattern)
        if plan_type:
            query_mf = query_mf.ilike("scheme_name", f"%{plan_type}%")
        if option_type:
            query_mf = query_mf.ilike("scheme_name", f"%{option_type}%")

        return [_with_normalized_variant_fields(row) for row in query_mf.limit(limit).execute().data or []]

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
            return _with_normalized_variant_fields(rows[0])
        rows = (
            self.table("mutual_funds")
            .select("*")
            .eq("scheme_code", code)
            .limit(1)
            .execute()
            .data
            or []
        )
        return _with_normalized_variant_fields(rows[0]) if rows else None

    def list_core_snapshot_rows(self, *, category: str | None = None, limit: int = 5000) -> list[dict[str, Any]]:
        """Return the stable numeric snapshot fields used by research ML features."""
        fields = (
            "scheme_code,scheme_name,amc_name,category,sub_category,nav_date,last_updated,"
            "return_1m,return_3m,return_6m,return_1y,return_3y,return_5y,"
            "volatility_1y,max_drawdown_1y,expense_ratio,aum,alpha,beta,sharpe_ratio,risk_level"
        )
        query = self.table("mutual_fund_core_snapshot").select(fields)
        if category:
            query = query.eq("category", category)
        rows = query.order("scheme_code").limit(max(1, min(limit, 5000))).execute().data or []
        return [_with_normalized_variant_fields(row) for row in rows]

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

    def get_family_id_for_scheme(self, scheme_code: Any) -> str | None:
        if scheme_code in (None, ""):
            return None
        code = str(scheme_code).strip()
        if not code:
            return None
        rows = (
            self.table("mutual_fund_family_mapping")
            .select("family_id")
            .eq("scheme_code", code)
            .limit(1)
            .execute()
            .data
            or []
        )
        value = rows[0].get("family_id") if rows else None
        return str(value) if value not in (None, "") else None

    def get_latest_holdings(self, scheme_code: Any) -> list[dict[str, Any]]:
        try:
            family_id = self.get_family_id_for_scheme(scheme_code)
        except Exception:
            family_id = None
        if family_id:
            rows = (
                self.table("mutual_fund_holdings")
                .select("as_of_date,security_name,isin,sector,weight_pct,source,provider_payload")
                .eq("family_id", family_id)
                .order("as_of_date", desc=True)
                .order("weight_pct", desc=True)
                .limit(500)
                .execute()
                .data
                or []
            )
            if rows:
                return rows
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
        try:
            family_id = self.get_family_id_for_scheme(scheme_code)
        except Exception:
            family_id = None
        if family_id:
            rows = (
                self.table("mutual_fund_sectors")
                .select("sector,weight_pct,stock_count,source,provider_payload,updated_at")
                .eq("family_id", family_id)
                .order("weight_pct", desc=True)
                .limit(50)
                .execute()
                .data
                or []
            )
            if rows:
                return rows
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
