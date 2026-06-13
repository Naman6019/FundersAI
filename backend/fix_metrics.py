import asyncio
import os
import sys

sys.path.append(os.path.abspath('c:/Users/naman/OneDrive/Desktop/FundersAI/backend'))
from app.database import supabase

async def fix_metrics():
    scheme_code = 154156
    supabase.table("mutual_fund_core_snapshot").update({
        "expense_ratio": 0.55,
        "aum": 25000.0
    }).eq("scheme_code", scheme_code).execute()
    print("Fixed metrics for 154156")

asyncio.run(fix_metrics())
