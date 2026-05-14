from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.database import supabase

router = APIRouter(prefix="/api/internal/mf", tags=["mf-ingestion"])


@router.get("/schemes/{scheme_name}/holdings")
def get_scheme_holdings(
    scheme_name: str,
    report_month: str | None = Query(default=None, description="YYYY-MM-01"),
    limit: int = Query(default=250, ge=1, le=5000),
):
    if not supabase:
        raise HTTPException(status_code=500, detail="Supabase client not initialized")

    normalized = scheme_name.strip().lower()
    scheme_result = (
        supabase.table("mf_schemes")
        .select("id,amc_code,scheme_name,scheme_name_normalized")
        .eq("scheme_name_normalized", normalized)
        .limit(1)
        .execute()
    )
    if not scheme_result.data:
        raise HTTPException(status_code=404, detail="Scheme not found")

    scheme = scheme_result.data[0]

    query = (
        supabase.table("mf_scheme_holdings")
        .select(
            "id,report_month,instrument_name,instrument_name_normalized,isin,sector,percent_aum,"
            "source_document_id,source_url,source_row_hash,parser_version,confidence_score,validation_status"
        )
        .eq("scheme_id", scheme["id"])
        .order("percent_aum", desc=True)
        .limit(limit)
    )
    if report_month:
        query = query.eq("report_month", report_month)

    rows = query.execute().data or []
    return {
        "scheme": scheme,
        "report_month": report_month,
        "holdings": rows,
        "count": len(rows),
    }
