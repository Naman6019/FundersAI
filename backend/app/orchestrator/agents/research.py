from typing import AsyncGenerator
import asyncio
from app.orchestrator.base import BaseAgent
from app.orchestrator.state import OrchestratorState

class ResearchAgent(BaseAgent):
    def __init__(self):
        super().__init__(name="Research")

    async def run(self, state: OrchestratorState) -> AsyncGenerator[dict, None]:
        yield {"type": "status", "message": "Querying vector database..."}
        
        asset_type = state.original_request.asset_type
        if asset_type == "mutual_fund":
            from app.services.chat_service import get_mf_repository
            from app.services.document_retrieval_service import DocumentRetrievalService
            from app.workflows.fund_research_graph import run_fund_research_workflow
            
            repo = get_mf_repository()
            retrieval_service = DocumentRetrievalService.configured(repo)
            
            # Use a background thread for the synchronous research workflow
            query = state.original_request.query
            official_result = await asyncio.to_thread(
                run_fund_research_workflow,
                retrieval_service,
                query=query,
                filters={},
                limit=3,
            )
            
            state.context["documents"] = official_result.get("documents", [])
            yield {"type": "status", "message": "Retrieving official AMC documents..."}
        else:
            state.context["documents"] = []

        state.add_message(self.name, "Retrieved documents for analysis.", "success")
        yield {"type": "status", "message": "Research complete."}
