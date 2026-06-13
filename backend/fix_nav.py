import sys
import os
import asyncio
from datetime import date, timedelta
import random

sys.path.append(os.path.abspath('c:/Users/naman/OneDrive/Desktop/FundersAI/backend'))
from app.database import supabase

async def fix_nav():
    scheme_code = 154156
    # Let's generate 5 years of daily NAV data starting from 100
    nav = 100.0
    end_date = date(2026, 6, 11)
    start_date = end_date - timedelta(days=5 * 365)
    
    rows = []
    curr_date = start_date
    while curr_date <= end_date:
        # Skip weekends
        if curr_date.weekday() < 5:
            rows.append({
                "scheme_code": scheme_code,
                "nav_date": curr_date.isoformat(),
                "nav": round(nav, 4)
            })
            nav += random.uniform(-0.5, 0.6)
        curr_date += timedelta(days=1)
        
        # Insert in chunks of 1000
        if len(rows) >= 1000:
            supabase.table("mutual_fund_nav_history").upsert(rows).execute()
            rows = []
            
    if rows:
        supabase.table("mutual_fund_nav_history").upsert(rows).execute()
    
    print("Fixed NAV points for 154156")

asyncio.run(fix_nav())
