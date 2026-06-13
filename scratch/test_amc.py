import asyncio
import os
import sys
from dotenv import load_dotenv
from supabase import create_client

sys.path.append(os.path.join(os.path.dirname(__file__), "..", "backend"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "backend", ".env"))

supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_SERVICE_KEY")
supabase = create_client(supabase_url, supabase_key)

def _load_amc_holdings_and_sectors(scheme_code_value):
    if not supabase or scheme_code_value in (None, ""):
        return [], [], None
    scheme_code_str = str(scheme_code_value)
    try:
        holdings_res = (
            supabase.table("mutual_fund_holdings")
            .select("as_of_date,security_name,isin,sector,weight_pct,source,provider_payload")
            .eq("scheme_code", int(scheme_code_str) if scheme_code_str.isdigit() else scheme_code_str)
            .order("as_of_date", desc=True)
            .order("weight_pct", desc=True)
            .limit(500)
            .execute()
        )
        holding_rows = holdings_res.data or []
        print(f"Fetched {len(holding_rows)} rows from DB for {scheme_code_value}")
    except Exception as e:
        print(f"Exception: {e}")
        holding_rows = []

    latest_as_of = None
    holdings = []
    for row in holding_rows:
        as_of = row.get("as_of_date")
        if latest_as_of is None:
            latest_as_of = as_of
        if as_of != latest_as_of:
            continue
        holdings.append(
            {
                "security_name": row.get("security_name"),
                "isin": row.get("isin"),
                "sector": row.get("sector"),
                "weight_pct": row.get("weight_pct"),
            }
        )
    return holdings, [], latest_as_of

h, s, d = _load_amc_holdings_and_sectors(122639)
print(f"Result holdings len: {len(h)}")
print(f"Result latest_as_of: {d}")
if h:
    print(h[0])
