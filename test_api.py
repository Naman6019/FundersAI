import requests
import json

SUPABASE_URL = "https://luzwcyholmyxzcrspzyr.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imx1endjeWhvbG15eHpjcnNwenlyIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3NjMzMjE3NywiZXhwIjoyMDkxOTA4MTc3fQ.tHzZUVrGW0N9k36Tl312E4bPRoqKUb3piW8FxuuX2zo"

headers = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

def test():
    # 1. Check mutual_fund_core_snapshot for MidCap funds
    url = f"{SUPABASE_URL}/rest/v1/mutual_fund_core_snapshot?select=scheme_code,scheme_name,aum,expense_ratio&scheme_name=ilike.*MidCap*&limit=5"
    response = requests.get(url, headers=headers)
    print("Core snapshot MidCap:", response.json())

    # 2. Check holdings for the first scheme_code
    if response.json() and len(response.json()) > 0:
        scheme_code = response.json()[0]['scheme_code']
        url = f"{SUPABASE_URL}/rest/v1/mutual_fund_holdings?select=scheme_code,security_name,weight_pct,sector&scheme_code=eq.{scheme_code}&limit=5"
        holdings = requests.get(url, headers=headers).json()
        print(f"Holdings for {scheme_code}:", holdings)

if __name__ == "__main__":
    test()
