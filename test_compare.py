import asyncio

async def main():
    from backend.app.main import build_comparison_payload

    res = await build_comparison_payload(["icici prudential midcap fund", "hdfc mid cap fund"])
    print(res)

if __name__ == "__main__":
    asyncio.run(main())
