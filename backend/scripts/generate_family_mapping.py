import asyncio
import re
import os
import sys

# Add backend dir to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import supabase

_REMOVABLE_WORDS = {
    'direct', 'regular', 'retail', 'growth', 'idcw', 'dividend', 'reinvestment', 'payout',
    'payment', 'institutional', 'bonus', 'option', 'plan', 'of', 'daily', 'weekly',
    'half', 'yearly', 'annual', 'quarterly', 'monthly',
}


def _base_cleanup(n: str) -> str:
    n = n.lower()
    n = n.replace("smallcap", "small cap")
    n = n.replace("midcap", "mid cap")
    n = n.replace("largecap", "large cap")
    n = n.replace("bluechip", "blue chip")
    return n


def clean_scheme_name(name: str) -> str:
    """Removes variant-specific noise from scheme names to generate a root family name.

    Plan/option noise words like "regular", "growth", "direct" only ever function as
    noise at the *end* of a scheme name (AMFI's "<Scheme Name> - <Plan> - <Option>"
    convention, e.g. "... - Growth - Regular Plan"). Stripping them unconditionally is
    wrong when a word like "Regular" is part of the scheme's own brand name (e.g.
    "Regular Savings Fund") rather than a trailing plan qualifier -- that collapsed
    genuinely different schemes into one family and made them inherit each other's
    benchmark/risk values (GitHub issue #2). Peeling recognized qualifier words off the
    *end* of the token list, one at a time, until a real word is hit handles this
    correctly regardless of whether the source separates the qualifier suffix with a
    spaced hyphen ("Fund - Direct Plan"), an unspaced one ("Fund-Direct Growth", as used
    inconsistently in mutual_fund_core_snapshot), or no separator at all.
    """
    if not name:
        return ""

    n = _base_cleanup(name)
    # Clean up punctuation into spaces before tokenizing.
    n = re.sub(r'[^a-z0-9\s]', ' ', n)
    tokens = n.split()
    while len(tokens) > 1 and tokens[-1] in _REMOVABLE_WORDS:
        tokens.pop()

    return " ".join(tokens)

def generate_family_id(clean_name: str) -> str:
    return clean_name.replace(" ", "-")

def get_all_snapshots():
    all_data = []
    offset = 0
    limit = 1000
    while True:
        res = supabase.table('mutual_fund_core_snapshot').select('scheme_code, scheme_name, amc_name, category').range(offset, offset + limit - 1).execute()
        data = res.data
        if not data:
            break
        all_data.extend(data)
        offset += limit
    return all_data

def process_and_insert():
    print("Fetching snapshots...")
    snapshots = get_all_snapshots()
    print(f"Fetched {len(snapshots)} snapshots.")
    
    mappings = []
    for row in snapshots:
        scheme_code = str(row.get('scheme_code'))
        scheme_name = row.get('scheme_name') or ""
        
        cleaned = clean_scheme_name(scheme_name)
        if not cleaned:
            continue
            
        family_id = generate_family_id(cleaned)
        
        # Simple confidence: if it's very short, low confidence
        confidence = 0.9
        if len(cleaned.split()) < 2:
            confidence = 0.5
            
        mappings.append({
            'scheme_code': scheme_code,
            'family_id': family_id,
            'confidence': confidence,
            'source': 'auto-group-script-v1'
        })
        
    print(f"Generated {len(mappings)} mappings. Upserting to database in batches...")
    
    # Upsert in batches of 500
    batch_size = 500
    for i in range(0, len(mappings), batch_size):
        batch = mappings[i:i + batch_size]
        try:
            supabase.table('mutual_fund_family_mapping').upsert(batch, on_conflict='scheme_code').execute()
            print(f"Upserted batch {i//batch_size + 1}/{(len(mappings) + batch_size - 1)//batch_size}")
        except Exception as e:
            print(f"Error upserting batch {i}: {e}")

if __name__ == '__main__':
    process_and_insert()
    print("Done!")
