import logging
import asyncio
from typing import Any
from app.database import supabase
from app.services.fund_service import FundService
from app.services import mf_engine_service

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
        # Fetch latest snapshot from MF engine
        engine_res = mf_engine_service.get_scheme_mf_data(scheme_code_str)
        if engine_res.get("ok") and engine_res.get("data"):
            data = engine_res["data"]
            # Minimal upsert to mutual_fund_core_snapshot to unblock user
            core_payload = {
                "scheme_code": scheme_code_str,
                "scheme_name": data.get("scheme_name"),
                "amc_name": data.get("amc_name"),
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

        # Invalidate caches
        FundService.get_mutual_fund_profile.cache_clear()
        FundService.get_nav_history_summary.cache_clear()
        logger.info(f"[AutoHeal] Completed successfully for {scheme_code_str}")
        
    except Exception as exc:
        logger.error(f"[AutoHeal] Failed for {scheme_code_str}: {exc}", exc_info=True)
