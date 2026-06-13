import asyncio
import sys
import os
sys.path.append(os.path.abspath('c:/Users/naman/OneDrive/Desktop/FundersAI/backend'))
from app.database import supabase

async def test():
    try:
        holdings_res = (
            supabase.table("mutual_fund_holdings")
            .select("as_of_date,security_name,isin,sector,weight_pct,source,provider_payload")
            .eq("scheme_code", 122639)
            .order("as_of_date", desc=True)
            .order("weight_pct", desc=True)
            .limit(500)
            .execute()
        )
        holding_rows = holdings_res.data or []
        print("Success, holdings count:", len(holding_rows))
    except Exception as e:
        print("ERROR IN ASYNC:", type(e), e)

asyncio.run(test())
