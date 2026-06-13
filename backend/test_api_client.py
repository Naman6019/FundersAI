import asyncio
import httpx

async def test():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/chat",
            json={"messages": [{"role": "user", "content": "Compare Parag Parikh Flexi Cap and HDFC Flexi Cap"}]}
        )
        data = response.json()
        print("Intent:", data.get("intent"))
        quant_data = data.get("quant_data", {})
        overlap = quant_data.get("holdings_overlap", {})
        print("Overlap coverage status:", overlap.get("coverage_status"))
        print("Overlap reason:", overlap.get("reason"))
        print("Common holdings count:", overlap.get("common_holding_count"))
        if "comparison" in quant_data:
            for k, v in quant_data["comparison"].items():
                print(f"Fund {k}:")
                print(f"  Holdings count: {len(v.get('holdings', []))}")

asyncio.run(test())
