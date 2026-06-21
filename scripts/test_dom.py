import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        print("Navigating to frontend...")
        
        # Navigate to a URL that includes the comparison. 
        # Since I don't know the exact comparison URL, I'll go to localhost:3000
        # and try to find the comparison UI or trigger it.
        await page.goto("http://localhost:3000")
        print("Page title:", await page.title())
        
        # Wait for the page to load, maybe navigate to Mutual Funds Comparison if there's a link
        content = await page.content()
        print("Body length:", len(content))
        
        # We can also check if there's a direct route for testing
        # For instance /compare or /funds/compare
        try:
            await page.goto("http://localhost:3000/api/funds/category") # Just as a test for routing
            content = await page.content()
            print("Categories api response length:", len(content))
        except Exception as e:
            pass

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
