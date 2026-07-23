from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from typing import Any, Literal

AgentStatus = Literal["completed", "partial", "escalated", "failed"]
TraceStatus = Literal["ok", "warning", "error", "skipped"]
DocumentReadiness = Literal[
    "discovered",
    "link_validated",
    "probe_passed",
    "content_validated",
    "parser_smoke_passed",
    "promotable",
    "needs_review",
    "failed",
]


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


@dataclass(frozen=True)
class AgentTraceEvent:
    step: str
    status: TraceStatus
    detail: str
    document_type: str | None = None
    strategy: str | None = None
    source_url: str | None = None
    observed_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step": self.step,
            "status": self.status,
            "detail": self.detail,
            "document_type": self.document_type,
            "strategy": self.strategy,
            "source_url": self.source_url,
            "observed_at": self.observed_at,
        }


@dataclass(frozen=True)
class ValidatedDiscovery:
    amc: str
    document_type: str
    title: str
    source_url: str
    discovery_page_url: str
    expected_file_type: str
    report_month: date | None
    priority_score: int
    warnings: tuple[str, ...] = ()
    probe_status: str = "not_requested"
    readiness: DocumentReadiness = "discovered"
    month_confirmation: str = "unconfirmed"
    content_sha256: str | None = None
    content_status: str = "not_requested"
    parser_smoke_status: str = "not_requested"

    def to_dict(self) -> dict[str, Any]:
        return {
            "amc": self.amc,
            "document_type": self.document_type,
            "title": self.title,
            "source_url": self.source_url,
            "discovery_page_url": self.discovery_page_url,
            "expected_file_type": self.expected_file_type,
            "report_month": self.report_month.isoformat() if self.report_month else None,
            "priority_score": self.priority_score,
            "warnings": list(self.warnings),
            "probe_status": self.probe_status,
            "readiness": self.readiness,
            "month_confirmation": self.month_confirmation,
            "content_sha256": self.content_sha256,
            "content_status": self.content_status,
            "parser_smoke_status": self.parser_smoke_status,
        }

    def to_manifest_row(self) -> dict[str, Any]:
        return {
            "amc": self.amc,
            "document_type": self.document_type,
            "report_month": self.report_month.isoformat() if self.report_month else None,
            "source_url": self.source_url,
            "discovery_page_url": self.discovery_page_url,
            "expected_file_type": self.expected_file_type,
            "title": self.title,
            "priority_score": self.priority_score,
            "discovery_agent_status": self.readiness,
            "month_confirmation": self.month_confirmation,
            "content_sha256": self.content_sha256,
        }


@dataclass
class DiscoveryAgentResult:
    agent_id: str
    amc: str
    status: AgentStatus
    requested_document_types: tuple[str, ...]
    documents: list[ValidatedDiscovery] = field(default_factory=list)
    trace: list[AgentTraceEvent] = field(default_factory=list)
    actions_used: int = 0
    max_actions: int = 0
    started_at: str = field(default_factory=_utc_now)
    completed_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "amc": self.amc,
            "status": self.status,
            "requested_document_types": list(self.requested_document_types),
            "documents": [document.to_dict() for document in self.documents],
            "trace": [event.to_dict() for event in self.trace],
            "actions_used": self.actions_used,
            "max_actions": self.max_actions,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class DiscoverySupervisorResult:
    status: AgentStatus
    agents: list[DiscoveryAgentResult]
    started_at: str = field(default_factory=_utc_now)
    completed_at: str = field(default_factory=_utc_now)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "agents": [agent.to_dict() for agent in self.agents],
            "manifest": {
                "generated_at": self.completed_at,
                "generated_by": "fundersai_amc_discovery_supervisor_v1",
                "documents": [
                    document.to_manifest_row()
                    for agent in self.agents
                    for document in agent.documents
                ],
            },
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }
