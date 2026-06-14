import asyncio
import sys
import os
sys.path.append(os.path.abspath('c:/Users/naman/OneDrive/Desktop/FundersAI/backend'))
from app.database import supabase

async def main():
    res = supabase.table('mutual_fund_core_snapshot').select('*').limit(1).execute()
    data = res.data[0]
    print("scheme_code type:", type(data.get("scheme_code")))
    print("scheme_code:", data.get("scheme_code"))

if __name__ == "__main__":
    asyncio.run(main())
