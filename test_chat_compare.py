import asyncio
from backend.app.services.chat_service import generate_chat_response

class MockRequest:
    def __init__(self, query, comparison_view_mode):
        self.query = query
        self.research_depth = "standard"
        self.explanation_mode = "standard"
        self.comparison_view_mode = comparison_view_mode
        self.model = "openrouter"

async def main():
    req = MockRequest("Parag Parikh Flexi Cap Direct vs Nippon India Small Cap Direct", "chat")
    res = await generate_chat_response(req)
    print("----- CHAT RESPONSE -----")
    print(res.get("answer"))

if __name__ == "__main__":
    asyncio.run(main())
