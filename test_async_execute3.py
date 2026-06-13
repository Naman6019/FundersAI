import asyncio
import sys
import os
sys.path.append(os.path.abspath('c:/Users/naman/OneDrive/Desktop/FundersAI/backend'))
from app.main import get_mf_history_df

async def test():
    try:
        hist = await get_mf_history_df(122639)
        print("Success, history count:", len(hist))
    except Exception as e:
        print("ERROR IN ASYNC:", type(e), e)

asyncio.run(test())
