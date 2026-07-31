import logging
from typing import AsyncGenerator
from app.orchestrator.state import OrchestratorState
from app.orchestrator.base import BaseAgent
from app.services.chat_service import ChatRequest

logger = logging.getLogger(__name__)

class OrchestratorEngine:
    def __init__(self, agents: list[BaseAgent]):
        self.agents = agents

    async def run(self, req: ChatRequest) -> AsyncGenerator[dict, None]:
        """
        Runs the orchestrated sequence of agents.
        Yields status updates to send back to the user via SSE.
        """
        state = OrchestratorState(
            query=req.query,
            original_request=req
        )

        for agent in self.agents:
            yield {"type": "agent_start", "agent": agent.name}
            try:
                async for update in agent.run(state):
                    # update should be a dict like {"type": "status", "message": "doing stuff"}
                    yield {"type": "agent_update", "agent": agent.name, "payload": update}
                    
                    # Backwards compatibility with existing frontend status UI
                    if update.get("type") == "status" and "message" in update:
                        yield {"type": "status", "message": f"[{agent.name}] {update['message']}"}
                        
                yield {"type": "agent_complete", "agent": agent.name}
            except Exception as e:
                logger.exception(f"Agent {agent.name} failed")
                yield {"type": "agent_error", "agent": agent.name, "message": str(e)}
                break # Stop the pipeline if an agent fails

        # Once all agents complete, final response should be in state.final_response
        if state.final_response:
            # We return a dict structured similar to the original ChatService response
            final_payload = {
                "answer": state.final_response,
                "asset_type": req.asset_type,
                "context": state.context
            }
            yield {"type": "final", "payload": final_payload}
        else:
            yield {"type": "error", "message": "Failed to generate a final response."}
