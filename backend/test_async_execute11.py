import asyncio
import sys
import os
sys.path.append(os.path.abspath('c:/Users/naman/OneDrive/Desktop/FundersAI/backend'))
from app.database import supabase

def _load_amc_holdings_and_sectors(scheme_code_value):
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
    except Exception:
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
                "as_of_date": as_of,
                "source": row.get("source"),
                "provider_payload": row.get("provider_payload"),
            }
        )
    return holdings

async def main():
    h = await asyncio.to_thread(_load_amc_holdings_and_sectors, 122639)
    print("final length:", len(h))
    if h:
        print("first item:", h[0])

if __name__ == "__main__":
    asyncio.run(main())
