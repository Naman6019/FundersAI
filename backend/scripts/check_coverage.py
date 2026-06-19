import asyncio
from app.database import supabase

def get_all(table, columns):
    all_data = []
    offset = 0
    limit = 1000
    while True:
        res = supabase.table(table).select(columns).range(offset, offset + limit - 1).execute()
        data = res.data
        if not data:
            break
        all_data.extend(data)
        offset += limit
    return all_data

def check_coverage():
    # 1. Fetch the mappings
    print("Fetching mappings...")
    mappings = get_all('mutual_fund_family_mapping', 'scheme_code, family_id')
    scheme_to_family = {str(r['scheme_code']): r['family_id'] for r in mappings}

    # 2. Fetch distinct family_ids from holdings
    print("Fetching holdings families...")
    res_holdings = supabase.table('mutual_fund_holdings').select('family_id').not_.is_('family_id', 'null').execute()
    holdings_families = {r['family_id'] for r in res_holdings.data if r.get('family_id')}
    
    # 3. Fetch distinct family_ids from sectors
    print("Fetching sectors families...")
    res_sectors = supabase.table('mutual_fund_sectors').select('family_id').not_.is_('family_id', 'null').execute()
    sector_families = {r['family_id'] for r in res_sectors.data if r.get('family_id')}
    
    amcs = ['Axis', 'HDFC', 'ICICI', 'SBI', 'PPFAS', 'Parag Parikh', 'Mirae']
    stats = {amc: {'total': 0, 'aum': 0, 'er': 0, 'fm': 0, 'bench': 0, 'holdings': 0, 'sectors': 0} for amc in amcs}
    
    print("Fetching snapshot rows...")
    all_data = get_all('mutual_fund_core_snapshot', 'scheme_code, amc_name, aum, expense_ratio, fund_manager, benchmark')

    for row in all_data:
        amc_name = row.get('amc_name', '') or ''
        scheme_code = str(row.get('scheme_code'))
        family_id = scheme_to_family.get(scheme_code)
        
        matched_amc = next((a for a in amcs if a.lower() in amc_name.lower()), None)
        
        if matched_amc:
            stats[matched_amc]['total'] += 1
            if row.get('aum') is not None: stats[matched_amc]['aum'] += 1
            if row.get('expense_ratio') is not None: stats[matched_amc]['er'] += 1
            if row.get('fund_manager'): stats[matched_amc]['fm'] += 1
            if row.get('benchmark'): stats[matched_amc]['bench'] += 1
            
            # Use new family_id logic
            if family_id in holdings_families: stats[matched_amc]['holdings'] += 1
            if family_id in sector_families: stats[matched_amc]['sectors'] += 1
            
    print(f"Total snapshot rows: {len(all_data)}")
    print(f"Total distinct families with holdings: {len(holdings_families)}")
    print(f"Total distinct families with sectors: {len(sector_families)}")
    print('AMC Coverage Check:')
    for amc, s in stats.items():
        if s['total'] > 0:
            print(f"{amc}: Total={s['total']} | AUM={s['aum']} | ExpR={s['er']} | Mgr={s['fm']} | Bench={s['bench']} | Hold={s['holdings']} | Sect={s['sectors']}")

if __name__ == '__main__':
    check_coverage()
