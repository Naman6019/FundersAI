import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_SERVICE_KEY") or os.environ.get("SUPABASE_KEY", "")
supabase: Client = create_client(url, key)

async def fetch_multiple_fund_metrics(scheme_codes: list[int]):
    core_response = supabase.table("mutual_fund_core_snapshot") \
        .select("scheme_code, scheme_name, amc_name, category, sub_category, nav, return_1m, return_6m, return_1y, return_3y, return_5y, expense_ratio, aum, benchmark, risk_level, alpha, beta, sharpe_ratio, fund_manager") \
            .in_("scheme_code", scheme_codes) \
                .execute()
    sector_response = supabase.table("mutual_fund_sectors") \
        .select("scheme_code, sector, weight_pct") \
            .in_("scheme_code", scheme_codes) \
                .execute()
    holdings_response = supabase.table("mutual_fund_holdings") \
        .select("scheme_code, security_name, sector, weight_pct") \
            .in_("scheme_code", scheme_codes) \
                .order("weight_pct", desc=True) \
                    .execute()
    final_data = {}
    for code in scheme_codes:
        final_data[code] = {
            "core": next((item for item in core_response.data if str(item["scheme_code"]) == str(code)), None),
            "sectors": [item for item in sector_response.data if str(item["scheme_code"]) == str(code)],
            "top_holdings": [item for item in holdings_response.data if str(item["scheme_code"]) == str(code)][:10]
        }
    return final_data