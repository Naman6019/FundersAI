import logging
import asyncio
from typing import Any
from app.database import supabase
from app.services import mf_engine_service
from app.services import mfapi_service
from app.mf_ingestion.services.parsing_service import ParsingService

logger = logging.getLogger(__name__)

async def trigger_mf_auto_heal(scheme_code: Any):
    """
    Background worker that attempts to heal missing or stale mutual fund data.
    """
    scheme_code_str = str(scheme_code)
    logger.info(f"[AutoHeal] Dispatched for scheme_code: {scheme_code_str}")

    if not supabase:
        logger.warning("[AutoHeal] Supabase not initialized.")
        return

    try:
        # 1. Fetch latest snapshot from MF engine
        engine_res = mf_engine_service.get_scheme_mf_data(scheme_code_str)
        scheme_name = None
        amc_name = None
        if engine_res.get("ok") and engine_res.get("data"):
            data = engine_res["data"]
            scheme_name = data.get("scheme_name")
            amc_name = data.get("amc_name")
            
            # Minimal upsert to mutual_fund_core_snapshot to unblock user
            core_payload = {
                "scheme_code": scheme_code_str,
                "scheme_name": scheme_name,
                "amc_name": amc_name,
                "category": data.get("category"),
                "sub_category": data.get("sub_category"),
                "nav": data.get("nav"),
                "nav_date": data.get("nav_date"),
                "aum": data.get("aum"),
                "expense_ratio": data.get("expense_ratio"),
            }
            # Remove None values
            core_payload = {k: v for k, v in core_payload.items() if v is not None}
            if core_payload:
                supabase.table("mutual_fund_core_snapshot").upsert(core_payload, on_conflict="scheme_code").execute()
                logger.info(f"[AutoHeal] Upserted core snapshot for {scheme_code_str}")
        
        # Fallback if engine fails, so we can still trigger parser
        if not scheme_name or not amc_name:
            existing_res = supabase.table("mutual_fund_core_snapshot").select("scheme_name, amc_name").eq("scheme_code", scheme_code_str).limit(1).execute()
            if existing_res.data:
                scheme_name = existing_res.data[0].get("scheme_name")
                amc_name = existing_res.data[0].get("amc_name")

        # 2. Force-refresh the server-only NAV cache and active snapshot metrics.
        nav_res = mfapi_service.get_cached_nav_history(scheme_code_str, force_refresh=True)
        if nav_res.get("ok") and nav_res.get("data"):
            nav_data = nav_res["data"]
            logger.info(f"[AutoHeal] Refreshed {len(nav_data)} cached NAV points for {scheme_code_str}")
            
        # 3. Check if Holdings/AUM are still missing and run targeted PDF parser if AMC is known
        if scheme_name and amc_name:
            # We map AMC names to short codes roughly
            amc_code = None
            if "icici" in amc_name.lower(): amc_code = "icici"
            elif "hdfc" in amc_name.lower(): amc_code = "hdfc"
            elif "sbi" in amc_name.lower(): amc_code = "sbi"
            elif "mirae" in amc_name.lower(): amc_code = "mirae"
            elif "parag" in amc_name.lower(): amc_code = "ppfas"
            
            if amc_code:
                # Let's check if holdings are still missing for this scheme
                holdings_res = supabase.table("mutual_fund_holdings").select("id").eq("scheme_code", scheme_code_str).limit(1).execute()
                if not holdings_res.data:
                    logger.info(f"[AutoHeal] Holdings missing for {scheme_code_str}, triggering targeted parser...")
                    parser = ParsingService()
                    parser.parse_latest_document_for_scheme(amc_code, scheme_name)
                    logger.info(f"[AutoHeal] Parser execution finished for {scheme_code_str}")

        logger.info(f"[AutoHeal] Completed successfully for {scheme_code_str}")
        
    except Exception as exc:
        logger.error(f"[AutoHeal] Failed for {scheme_code_str}: {exc}", exc_info=True)
