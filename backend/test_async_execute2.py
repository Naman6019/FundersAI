import asyncio
import sys
import os
sys.path.append(os.path.abspath('.'))
from app.services.fund_service import FundService

async def main():
    try:
        hist = FundService.get_mf_history(122639)
        print("Success, history count:", len(hist))
    except Exception as e:
        print("ERROR IN ASYNC:", type(e), e)

if __name__ == "__main__":
    asyncio.run(main())
