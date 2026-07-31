from abc import ABC, abstractmethod
from typing import AsyncGenerator
from app.orchestrator.state import OrchestratorState

class BaseAgent(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def run(self, state: OrchestratorState) -> AsyncGenerator[dict, None]:
        """
        Executes the agent's logic.
        Yields status updates (dict) to stream back to the UI.
        Modifies the OrchestratorState in place.
        """
        pass
