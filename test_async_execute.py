import asyncio
import sys
sys.path.append('c:/Users/naman/OneDrive/Desktop/FundersAI/backend')
from app.database import supabase

async def main():
    try:
        res = supabase.table('mutual_fund_holdings').select('as_of_date').limit(1).execute()
        print(res)
    except Exception as e:
        print('ERROR:', type(e), e)

if __name__ == "__main__":
    asyncio.run(main())
