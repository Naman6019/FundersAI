from typing import AsyncGenerator
import asyncio
from app.orchestrator.base import BaseAgent
from app.orchestrator.state import OrchestratorState

class SynthesisAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Synthesis")

    async def run(self, state: OrchestratorState) -> AsyncGenerator[dict, None]:
        yield {"type": "status", "message": "Drafting final response..."}
        
        from app.services.chat_service import synthesis_response
        
        query = state.original_request.query
        intent_info = state.context.get("intent_info", {})
        quant_data = state.context.get("quant_metrics")
        research_depth = state.original_request.research_depth or "standard"
        explanation_mode = getattr(state.original_request, "explanation_mode", None)
        comparison_view_mode = getattr(state.original_request, "comparison_view_mode", "canvas")
        
        try:
            answer = await synthesis_response(
                query=query,
                intent_info=intent_info,
                quant_data=quant_data,
                news_data=[],
                screening_results=None,
                research_depth=research_depth,
                explanation_mode=explanation_mode,
                comparison_view_mode=comparison_view_mode
            )
            state.final_response = answer
        except Exception as e:
            state.final_response = f"Failed to synthesize response: {str(e)}"
            
        state.add_message(self.name, "Final response drafted.", "success")
        yield {"type": "status", "message": "Drafting complete."}
