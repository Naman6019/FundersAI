import os
import sys
import asyncio
import json

sys.path.append(os.path.abspath("backend"))

from app.services.chat_service import function_ollama_chat

async def test_enrichment():
    funds = [
        "Parag Parikh Flexi Cap Fund Direct Growth",
        "Nippon India Small Cap Fund Direct Growth"
    ]

    for fund in funds:
        print(f"Generating qualitative factors for: {fund}...")
        system_prompt = f"""You are a mutual fund analyst for FundersAI.
For the mutual fund provided, generate qualitative data factors to be displayed in a comparison canvas.
The response must be strict JSON in the following format:
{{
  "main_style": "Short description of its investing style (e.g. Diversified equity across large/mid/small caps + some global exposure)",
  "minimum_sip": "The typical minimum SIP amount (e.g. Usually ₹1,000)",
  "mandate": "Short description of the fund mandate (e.g. Must keep at least 65% in small-cap stocks)",
  "best_for": "Who is this fund best for? (e.g. Aggressive long-term growth allocation)",
  "main_risk": "What is the primary risk of this fund? (e.g. Underperformance when growth/momentum stocks rally hard)"
}}
Ensure the response is concise and objective.
"""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": fund}
        ]

        try:
            result_json = await function_ollama_chat(messages, format="json")
            if result_json:
                data = json.loads(result_json)
                print(json.dumps(data, indent=2))
            else:
                print("No response from LLM.")
        except Exception as e:
            print(f"Error: {e}")

        print("-" * 50)

if __name__ == "__main__":
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    asyncio.run(test_enrichment())
