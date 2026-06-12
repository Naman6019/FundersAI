import sys, os
from dotenv import load_dotenv
sys.path.insert(0, os.path.abspath('backend'))
load_dotenv('backend/.env')
load_dotenv('.env')

from app.repositories.stock_repository import StockRepository

print('--- CHECKING SUPABASE DATA COUNTS ---')
repo = StockRepository()
tables_to_check = ['stocks', 'stock_prices_daily', 'corporate_events', 'financial_statements', 'ratios_snapshot']
for table in tables_to_check:
    try:
        # We can get an approximate count by limiting to 1 with count=exact
        res = repo.supabase.table(table).select('id', count='exact').limit(1).execute()
        count = res.count if hasattr(res, 'count') else "Unknown"
        
        # also get the latest updated_at or created_at to see how fresh it is
        latest = repo.supabase.table(table).select('*').order('created_at', desc=True).limit(1).execute().data
        freshness = latest[0].get('created_at') if latest and 'created_at' in latest[0] else 'N/A'
        if freshness == 'N/A' and latest and 'date' in latest[0]:
            freshness = latest[0].get('date')
            
        print(f"Table '{table}' -> Rows: {count} | Newest Record: {freshness}")
    except Exception as e:
        print(f"Table '{table}' -> Error checking table: {e}")

