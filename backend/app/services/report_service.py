from app.database import supabase

async def fetch_fund_metrics(scheme_code: int):
    core_res = supabase.table("mutual_fund_core_snapshot") \
        .select("scheme_name, aum, expense_ratio, return_1y, risk_level, fund_manager") \
            .eq("scheme_code", scheme_code) \
                .execute()
    if not core_res.data:
        raise ValueError("Fund not found")
    
    holdings_res = supabase.table("mutual_fund_holdings") \
        .select("security_name, sector, weight_pct") \
            .eq("scheme_code", scheme_code) \
                .order("weight_pct", desc=True) \
                    .limit(10) \
                        .execute()
    
    sector_res = supabase.table("mutual_fund_sectors") \
        .select("sector, weight_pct") \
            .eq("scheme_code", scheme_code) \
                    .execute()
    
    return {
        "core": core_res.data[0],
        "top_10_holdings": holdings_res.data,
        "sector_allocation": sector_res.data,
    }