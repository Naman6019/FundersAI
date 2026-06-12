import asyncio
from backend.app.main import supabase

async def check_db():
    res = supabase.table("mutual_fund_core_snapshot").select("scheme_code,scheme_name,aum,expense_ratio").ilike("scheme_name", "%midcap%").limit(5).execute()
    print("Snapshot rows matching midcap:", res.data)
    
    res = supabase.table("mutual_fund_holdings").select("scheme_code,security_name,weight_pct").limit(5).execute()
    print("Holdings sample:", res.data)

if __name__ == "__main__":
    asyncio.run(check_db())
