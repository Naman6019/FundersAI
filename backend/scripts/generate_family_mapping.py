import asyncio
import re
import os
import sys

# Add backend dir to path so we can import app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import supabase

def clean_scheme_name(name: str) -> str:
    """Removes variant-specific noise from scheme names to generate a root family name."""
    if not name:
        return ""
    
    # Base cleanup
    n = name.lower()
    n = n.replace("smallcap", "small cap")
    n = n.replace("midcap", "mid cap")
    n = n.replace("largecap", "large cap")
    n = n.replace("bluechip", "blue chip")
    
    # Remove common variants
    remove_phrases = [
        r'\bdirect plan\b', r'\bdirect\b',
        r'\bregular plan\b', r'\bregular\b',
        r'\bgrowth plan\b', r'\bgrowth\b',
        r'\bidcw\b', r'\bdividend\b', r'\breinvestment\b', r'\bpayout\b',
        r'\binstitutional plan\b', r'\binstitutional\b',
        r'\bbonus\b', r'\boption\b', r'\bplan\b', r'\bhalf yearly\b', r'\bquarterly\b', r'\bmonthly\b'
    ]
    
    for phrase in remove_phrases:
        n = re.sub(phrase, '', n)
        
    # Clean up punctuation and extra spaces
    n = re.sub(r'[^a-z0-9\s]', ' ', n)
    n = " ".join(n.split())
    
    return n

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
