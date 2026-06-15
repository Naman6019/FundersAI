import sys
import os
import asyncio
sys.path.append(os.path.abspath('c:/Users/naman/OneDrive/Desktop/FundersAI/backend'))

async def main():
    from app.services.chat_service import _build_holdings_overlap
    from app.services.fund_service import FundService

    h1, date1 = await asyncio.to_thread(FundService.load_latest_fund_holdings, 122639)
    h2, date2 = await asyncio.to_thread(FundService.load_latest_fund_holdings, 120596)
    h1 = [h.model_dump() for h in h1]
    h2 = [h.model_dump() for h in h2]
    
    print(f"H1 length: {len(h1)}, H2 length: {len(h2)}")
    
    comp = {
        "fund1": {"holdings": h1},
        "fund2": {"holdings": h2}
    }
    
    overlap = _build_holdings_overlap(comp)
    print("Coverage status:", overlap.get("coverage_status"))
    print("Reason:", overlap.get("reason"))
    print("Total overlap:", overlap.get("total_overlap_weight"))

if __name__ == "__main__":
    asyncio.run(main())
