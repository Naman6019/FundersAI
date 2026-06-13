import sys
import os
import asyncio
sys.path.append(os.path.abspath('c:/Users/naman/OneDrive/Desktop/FundersAI/backend'))
from app.database import supabase

async def test():
    scheme_code = 122639
    res1 = supabase.table("mutual_fund_holdings").select("count", count="exact").eq("scheme_code", scheme_code).execute()
    res2 = supabase.table("mutual_fund_portfolio").select("count", count="exact").eq("scheme_code", scheme_code).execute()
    print("mutual_fund_holdings count:", res1.count)
    print("mutual_fund_portfolio count:", res2.count)

asyncio.run(test())
