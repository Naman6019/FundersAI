import sys
import os
import asyncio
sys.path.append(os.path.abspath('c:/Users/naman/OneDrive/Desktop/FundersAI/backend'))
from app.main import _build_holdings_overlap, _load_amc_holdings_and_sectors

async def test():
    h1, s1, date1 = await asyncio.to_thread(_load_amc_holdings_and_sectors, 122639)
    h2, s2, date2 = await asyncio.to_thread(_load_amc_holdings_and_sectors, 120596)
    
    print(f"H1 length: {len(h1)}, H2 length: {len(h2)}")
    
    comp = {
        "fund1": {"holdings": h1},
        "fund2": {"holdings": h2}
    }
    
    overlap = _build_holdings_overlap(comp)
    print("Coverage status:", overlap.get("coverage_status"))
    print("Reason:", overlap.get("reason"))
    print("Total overlap:", overlap.get("total_overlap_weight"))

asyncio.run(test())
