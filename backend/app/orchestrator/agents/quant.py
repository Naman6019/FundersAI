from typing import AsyncGenerator
import asyncio
from app.orchestrator.base import BaseAgent
from app.orchestrator.state import OrchestratorState

class QuantAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Quant")

    async def run(self, state: OrchestratorState) -> AsyncGenerator[dict, None]:
        yield {"type": "status", "message": "Fetching quantitative data..."}
        
        intent_info = state.context.get("intent_info", {})
        asset_type = state.original_request.asset_type
        
        if asset_type == "stock":
            from app.services.stock_snapshot_service import get_stock_snapshot_with_freshness
            tickers = intent_info.get("ticker", [])
            if not isinstance(tickers, list):
                tickers = [tickers] if tickers else []
            
            metrics = []
            for t in tickers:
                try:
                    metrics.append(get_stock_snapshot_with_freshness(t))
                except Exception:
                    pass
            state.context["quant_metrics"] = metrics
            
        elif asset_type == "mutual_fund":
            from app.services.chat_service import MutualFundDetailService
            from fastapi import BackgroundTasks
            
            # Use background_tasks as dummy to fulfill contract
            bg = BackgroundTasks()
            mf_service = MutualFundDetailService()
            
            # Simple heuristic: if we have a resolved scheme code in the payload, use it
            # The resolver might be used earlier or we can just fetch some data
            # For this MVP agent setup, we'll assume ticker list holds scheme_codes if intent parsing succeeded
            tickers = intent_info.get("ticker", [])
            if not isinstance(tickers, list):
                tickers = [tickers] if tickers else []
                
            metrics = []
            for t in tickers:
                try:
                    # If it's an int, it's a scheme code. The intent parser often returns it as string though.
                    scheme_code = int(t)
                    details = await mf_service.get_details(scheme_code, bg)
                    metrics.append(details)
                except Exception:
                    pass
            state.context["quant_metrics"] = metrics

        state.add_message(self.name, "Quant metrics gathered successfully.", "success")
        yield {"type": "status", "message": "Quant analysis complete."}
