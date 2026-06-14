import asyncio
import sys
import os
sys.path.append(os.path.abspath('c:/Users/naman/OneDrive/Desktop/FundersAI/backend'))
from app.database import supabase

async def main():
    res = supabase.table('mutual_fund_holdings').select('as_of_date').eq('scheme_code', 122639).order('as_of_date', desc=True).limit(5).execute()
    print("as_of_date top 5:", res.data)

if __name__ == "__main__":
    asyncio.run(main())
