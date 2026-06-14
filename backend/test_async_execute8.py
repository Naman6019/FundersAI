import asyncio
import sys
import os
sys.path.append(os.path.abspath('c:/Users/naman/OneDrive/Desktop/FundersAI/backend'))
from app.database import supabase

async def main():
    res = supabase.table('mutual_fund_holdings').select('scheme_code').limit(1).execute()
    data = res.data[0]
    print("holdings scheme_code type:", type(data.get("scheme_code")))
    print("holdings scheme_code:", data.get("scheme_code"))

    res2 = supabase.table('mutual_fund_sectors').select('scheme_code').limit(1).execute()
    data2 = res2.data[0]
    print("sectors scheme_code type:", type(data2.get("scheme_code")))
    print("sectors scheme_code:", data2.get("scheme_code"))

if __name__ == "__main__":
    asyncio.run(main())
