import os
import sys
import asyncio
import json

sys.path.append(os.path.abspath("backend"))

from app.repositories.mutual_fund_repository import MutualFundRepository

async def check_payload():
    repo = MutualFundRepository()
    res = repo.table("mutual_fund_core_snapshot").select("scheme_name, provider_payload").eq("scheme_code", "120503").limit(1).execute()
    # 120503 is Parag Parikh Flexi Cap
    if res.data:
        print(f"Scheme: {res.data[0]['scheme_name']}")
        print(f"Payload: {json.dumps(res.data[0]['provider_payload'], indent=2)}")
    else:
        print("No data.")

if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(check_payload())
