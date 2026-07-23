from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, date, datetime
from typing import Iterable

from app.mf_ingestion.agents.contracts import (
    AgentTraceEvent,
    DiscoveryAgentResult,
    DiscoverySupervisorResult,
)
from app.mf_ingestion.agents.discovery_agent import AMCLinkDiscoveryAgent, build_discovery_agent
from app.mf_ingestion.config import IngestionConfig, get_config


class AMCDiscoverySupervisor:
    """Runs specialist discovery agents independently and preserves per-AMC failures."""

    def __init__(self, agents: dict[str, AMCLinkDiscoveryAgent]) -> None:
        if not agents:
            raise ValueError("At least one discovery agent is required")
        self.agents = {key.lower(): agent for key, agent in agents.items()}

    @classmethod
    def build(
        cls,
        amcs: Iterable[str],
        *,
        config: IngestionConfig | None = None,
        max_actions_per_agent: int = 12,
        last_known_good_loader=None,
        llm_recovery_loader=None,
    ) -> "AMCDiscoverySupervisor":
        resolved_config = config or get_config()
        agents = {
            key: build_discovery_agent(
                key,
                config=resolved_config,
                max_actions=max_actions_per_agent,
                last_known_good_loader=last_known_good_loader,
                llm_recovery_loader=llm_recovery_loader,
            )
            for key in _normalize_amcs(amcs)
        }
        return cls(agents)

    def run(
        self,
        *,
        document_types: tuple[str, ...],
        expected_month: date | None = None,
        expected_month_grace_days: int = 14,
        max_candidates_per_type: int = 1,
        probe_downloads: bool = True,
    ) -> DiscoverySupervisorResult:
        started_at = datetime.now(UTC).isoformat()
        results_by_amc: dict[str, DiscoveryAgentResult] = {}

        with ThreadPoolExecutor(max_workers=min(len(self.agents), 4), thread_name_prefix="amc-discovery") as executor:
            futures = {
                executor.submit(
                    agent.run,
                    document_types=document_types,
                    expected_month=expected_month,
                    expected_month_grace_days=expected_month_grace_days,
                    max_candidates_per_type=max_candidates_per_type,
                    probe_downloads=probe_downloads,
                ): key
                for key, agent in self.agents.items()
            }
            for future in as_completed(futures):
                key = futures[future]
                try:
                    results_by_amc[key] = future.result()
                except Exception as exc:
                    agent = self.agents[key]
                    now = datetime.now(UTC).isoformat()
                    results_by_amc[key] = DiscoveryAgentResult(
                        agent_id=agent.agent_id,
                        amc=agent.source.amc_code,
                        status="failed",
                        requested_document_types=document_types,
                        trace=[
                            AgentTraceEvent(
                                step="supervisor",
                                status="error",
                                detail=f"Unhandled agent failure: {exc}",
                            )
                        ],
                        max_actions=agent.max_actions,
                        started_at=now,
                        completed_at=now,
                    )

        ordered_results = [results_by_amc[key] for key in self.agents]
        completed_count = sum(result.status == "completed" for result in ordered_results)
        if completed_count == len(ordered_results):
            status = "completed"
        elif completed_count or any(result.documents for result in ordered_results):
            status = "partial"
        elif any(result.status == "escalated" for result in ordered_results):
            status = "escalated"
        else:
            status = "failed"

        return DiscoverySupervisorResult(
            status=status,
            agents=ordered_results,
            started_at=started_at,
            completed_at=datetime.now(UTC).isoformat(),
        )


def _normalize_amcs(amcs: Iterable[str]) -> list[str]:
    normalized: list[str] = []
    for amc in amcs:
        key = str(amc or "").strip().lower()
        if key and key not in normalized:
            normalized.append(key)
    if not normalized:
        raise ValueError("At least one AMC key is required")
    return normalized
