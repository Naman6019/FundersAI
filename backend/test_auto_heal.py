import asyncio
import logging
import sys
from app.services.auto_heal import trigger_mf_auto_heal

logging.basicConfig(level=logging.INFO, stream=sys.stdout)

async def test_auto_heal():
    scheme_code = "134014" # SBI BSE 100 ETF (currently missing AUM)
    print(f"Testing auto heal for scheme code {scheme_code}...")
    await trigger_mf_auto_heal(scheme_code)
    print("Done!")

if __name__ == "__main__":
    asyncio.run(test_auto_heal())
