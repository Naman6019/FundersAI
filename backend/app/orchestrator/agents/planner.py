from typing import AsyncGenerator
import asyncio
from app.orchestrator.base import BaseAgent
from app.orchestrator.state import OrchestratorState

class PlannerAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Planner")

    async def run(self, state: OrchestratorState) -> AsyncGenerator[dict, None]:
        yield {"type": "status", "message": "Analyzing query structure..."}
        
        from app.services.chat_service import route_query
        
        asset_type = state.original_request.asset_type
        query = state.original_request.query
        
        intent_info = await route_query(query, asset_type)
        state.context["intent_info"] = intent_info
        
        state.plan = [
            f"Determined intent: {intent_info.get('intent', 'general')}",
            "Fetch quantitative data",
            "Retrieve documents",
            "Synthesize final response"
        ]
        
        state.add_message(self.name, f"Analyzed query. Intent: {intent_info.get('intent', 'general')}", "success")
        yield {"type": "status", "message": f"Intent parsed: {intent_info.get('intent', 'general')}"}
