import asyncio
import sys
import os
sys.path.append(os.path.abspath('c:/Users/naman/OneDrive/Desktop/FundersAI/backend'))
from app.database import supabase

async def main():
    res = supabase.table('mutual_fund_core_snapshot').select('*').eq('scheme_code', '122639').execute()
    print("Snapshot matches for 122639:", len(res.data))
    
    res2 = supabase.table('mutual_funds').select('*').eq('scheme_code', 122639).execute()
    print("Mutual funds matches for 122639:", len(res2.data))

if __name__ == "__main__":
    asyncio.run(main())
