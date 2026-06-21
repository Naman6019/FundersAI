import os
import sys
import asyncio

sys.path.append(os.path.abspath("backend"))

from app.repositories.mutual_fund_repository import MutualFundRepository

async def test_schema():
    repo = MutualFundRepository()
    try:
        # Check if column exists, if not, we might need direct Postgres DDL.
        # Supabase Python client doesn't directly support DDL out of the box through `table.select` but we can run an RPC or raw SQL via rpc if configured.
        # Let's just fetch a row to see its keys.
        res = repo.table("mutual_fund_core_snapshot").select("*").limit(1).execute()
        if res.data:
            print(res.data[0].keys())
        else:
            print("No data.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(test_schema())
