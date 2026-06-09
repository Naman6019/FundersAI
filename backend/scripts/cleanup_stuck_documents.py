import os
import sys
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase

def main():
    if not supabase:
        print("Supabase client is not configured.")
        return

    print("--- STARTING DATABASE CLEANUP SYSTEM ---")

    # 1. Update wrongly classified PPFAS factsheets
    print("\n1. Re-classifying PPFAS monthly portfolio reports from 'factsheet' to 'portfolio_disclosure'...")
    res_ppfas_fs = supabase.table("mf_raw_documents")\
        .select("id, file_name")\
        .eq("amc_code", "PPFAS")\
        .eq("document_type", "factsheet")\
        .ilike("file_name", "%portfolio%report%")\
        .execute()
    
    ppfas_fs_docs = res_ppfas_fs.data or []
    print(f"Found {len(ppfas_fs_docs)} matching PPFAS documents.")
    for doc in ppfas_fs_docs:
        print(f"Updating document {doc['id']} ({doc['file_name']})")
        supabase.table("mf_raw_documents").update({
            "document_type": "portfolio_disclosure",
            "parse_status": "needs_reparse",
            "validation_issues": []
        }).eq("id", doc["id"]).execute()

    # 2. Mark junk/unsupported files as skipped_not_supported
    print("\n2. Setting status of historical junk/unsupported files to 'skipped_not_supported'...")
    junk_filters = [
        ("%certified-moa-aoa%", "unsupported_historical_document"),
        ("%reliance-home-finance%", "unsupported_historical_document"),
        ("%manpasand-beverages%", "unsupported_historical_document"),
        ("%pms%fee%illustration%", "unsupported_historical_document"),
        ("%hdfc%amc%final%booklet%", "unsupported_historical_document"),
    ]

    total_junk_updated = 0
    for pattern, issue in junk_filters:
        res_junk = supabase.table("mf_raw_documents")\
            .select("id, file_name")\
            .ilike("file_name", pattern)\
            .execute()
        
        junk_docs = res_junk.data or []
        for doc in junk_docs:
            print(f"Marking junk/unsupported document: {doc['id']} ({doc['file_name']})")
            supabase.table("mf_raw_documents").update({
                "parse_status": "skipped_not_supported",
                "validation_issues": [issue]
            }).eq("id", doc["id"]).execute()
            total_junk_updated += 1
    print(f"Updated {total_junk_updated} junk documents.")

    # 3. Mark old ICICI quant files as skipped_not_supported
    print("\n3. Setting status of ICICI quant files to 'skipped_not_supported'...")
    res_icici_old = supabase.table("mf_raw_documents")\
        .select("id, file_name, source_url, downloaded_at")\
        .eq("amc_code", "ICICI")\
        .eq("parse_status", "needs_review")\
        .eq("document_type", "portfolio_disclosure")\
        .ilike("file_name", "%.xlsx")\
        .execute()
    
    icici_old_docs = res_icici_old.data or []
    total_icici_old_updated = 0
    for doc in icici_old_docs:
        source_text = f"{doc.get('file_name') or ''} {doc.get('source_url') or ''}".lower()
        dl_at = doc.get("downloaded_at") or ""
        if "quant" in source_text or (dl_at and dl_at < "2023-01-01"):
            print(f"Marking old ICICI document: {doc['id']} ({doc['file_name']})")
            supabase.table("mf_raw_documents").update({
                "parse_status": "skipped_not_supported",
                "validation_issues": ["skipped_irrelevant_document:icici_quant_file"]
            }).eq("id", doc["id"]).execute()
            total_icici_old_updated += 1
    print(f"Updated {total_icici_old_updated} old ICICI documents.")

    # 4. Mark legacy PPFAS 2025 .xls portfolio rows as skipped_not_supported
    print("\n4. Setting status of legacy PPFAS 2025 .xls portfolio rows to 'skipped_not_supported'...")
    res_ppfas_legacy = supabase.table("mf_raw_documents")\
        .select("id, file_name, source_url")\
        .eq("amc_code", "PPFAS")\
        .eq("parse_status", "failed")\
        .eq("document_type", "portfolio_disclosure")\
        .ilike("file_name", "%Monthly_Portfolio_Report%")\
        .execute()

    ppfas_legacy_docs = res_ppfas_legacy.data or []
    total_ppfas_legacy_updated = 0
    for doc in ppfas_legacy_docs:
        source_text = f"{doc.get('file_name') or ''} {doc.get('source_url') or ''}".lower()
        if ".xls" in source_text and "2025" in source_text:
            print(f"Marking legacy PPFAS document: {doc['id']} ({doc['file_name']})")
            supabase.table("mf_raw_documents").update({
                "parse_status": "skipped_not_supported",
                "validation_issues": ["skipped_irrelevant_document:legacy_ppfas_xls_before_supported_window"]
            }).eq("id", doc["id"]).execute()
            total_ppfas_legacy_updated += 1
    print(f"Updated {total_ppfas_legacy_updated} legacy PPFAS documents.")

    # 5. Set valid disclosures that are currently stuck in needs_review to needs_reparse
    print("\n5. Resetting valid stuck documents to 'needs_reparse' for reparsing...")
    res_stuck = supabase.table("mf_raw_documents")\
        .select("id, amc_code, file_name, parse_status")\
        .eq("parse_status", "needs_review")\
        .execute()
    
    stuck_docs = res_stuck.data or []
    print(f"Found {len(stuck_docs)} valid disclosures stuck in needs_review.")
    for doc in stuck_docs:
        print(f"Resetting valid stuck document for reparse: {doc['id']} ({doc['file_name']})")
        supabase.table("mf_raw_documents").update({
            "parse_status": "needs_reparse",
            "validation_issues": []
        }).eq("id", doc["id"]).execute()

    print("\n--- DATABASE CLEANUP SYSTEM COMPLETE ---")

if __name__ == "__main__":
    main()
