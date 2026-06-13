import asyncio
import sys
sys.path.append('c:/Users/naman/OneDrive/Desktop/FundersAI/backend')
from app.core.config import supabase

async def test():
    try:
        res = supabase.table('mutual_fund_holdings').select('as_of_date').limit(1).execute()
        print(res)
    except Exception as e:
        print('ERROR:', type(e), e)

asyncio.run(test())
