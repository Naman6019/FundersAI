from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

class AgentMessage(BaseModel):
    agent_name: str
    content: str
    status: Literal["running", "success", "error"] = "running"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class OrchestratorState(BaseModel):
    query: str
    original_request: Any  # Will hold ChatRequest
    plan: List[str] = Field(default_factory=list)
    messages: List[AgentMessage] = Field(default_factory=list)
    context: Dict[str, Any] = Field(default_factory=dict)
    final_response: Optional[str] = None
    
    def add_message(self, agent_name: str, content: str, status: Literal["running", "success", "error"] = "running", metadata: Dict[str, Any] = None):
        msg = AgentMessage(
            agent_name=agent_name,
            content=content,
            status=status,
            metadata=metadata or {}
        )
        self.messages.append(msg)
        return msg
