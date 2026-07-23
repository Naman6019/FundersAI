from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Callable

from app.mf_ingestion.agents.contracts import AgentTraceEvent, DiscoveryAgentResult, ValidatedDiscovery
from app.mf_ingestion.agents.validation import (
    content_sha256,
    validate_candidate,
    validate_download,
    validate_parser_smoke,
)
from app.mf_ingestion.config import IngestionConfig, get_config
from app.mf_ingestion.downloaders.amc_downloader import AMCDownloader
from app.mf_ingestion.downloaders.base_downloader import BaseDownloader, DiscoveredDocument
from app.mf_ingestion.services.source_manifest import load_source_manifest_documents
from app.mf_ingestion.sources.registry import AMCDocumentSource, get_source

ManifestLoader = Callable[[str, AMCDocumentSource, str], list[DiscoveredDocument]]
LastKnownGoodLoader = Callable[[AMCDocumentSource, str], list[DiscoveredDocument]]
LLMRecoveryLoader = Callable[[AMCDocumentSource, str], list[DiscoveredDocument]]


class AMCLinkDiscoveryAgent:
    """Bounded specialist that discovers and validates official AMC document links."""

    expected_adapter_key: str | None = None

    def __init__(
        self,
        *,
        source: AMCDocumentSource,
        downloader: BaseDownloader,
        manifest_path: str = "",
        manifest_loader: ManifestLoader = load_source_manifest_documents,
        last_known_good_loader: LastKnownGoodLoader | None = None,
        llm_recovery_loader: LLMRecoveryLoader | None = None,
        max_actions: int = 12,
    ) -> None:
        if self.expected_adapter_key and source.adapter_key.lower() != self.expected_adapter_key:
            raise ValueError(f"{self.__class__.__name__} requires adapter_key={self.expected_adapter_key}")
        self.source = source
        self.downloader = downloader
        self.manifest_path = manifest_path
        self.manifest_loader = manifest_loader
        self.last_known_good_loader = last_known_good_loader
        self.llm_recovery_loader = llm_recovery_loader
        self.max_actions = max(max_actions, 1)

    @property
    def agent_id(self) -> str:
        return f"{self.source.adapter_key.lower()}_link_discovery_agent_v1"

    def run(
        self,
        *,
        document_types: tuple[str, ...],
        expected_month: date | None = None,
        expected_month_grace_days: int = 14,
        max_candidates_per_type: int = 1,
        probe_downloads: bool = True,
    ) -> DiscoveryAgentResult:
        started_at = datetime.now(UTC).isoformat()
        trace: list[AgentTraceEvent] = []
        accepted: list[ValidatedDiscovery] = []
        actions_used = 0
        max_candidates = max(max_candidates_per_type, 1)

        for document_type in document_types:
            if actions_used >= self.max_actions:
                trace.append(
                    AgentTraceEvent(
                        step="action_budget",
                        status="error",
                        detail=f"Agent stopped after reaching max_actions={self.max_actions}.",
                        document_type=document_type,
                    )
                )
                break

            manifest_documents: list[DiscoveredDocument] = []
            if self.manifest_path:
                actions_used += 1
                try:
                    manifest_documents = self.manifest_loader(self.manifest_path, self.source, document_type)
                    trace.append(
                        AgentTraceEvent(
                            step="discover",
                            status="ok" if manifest_documents else "skipped",
                            detail=f"Loaded {len(manifest_documents)} manifest candidate(s).",
                            document_type=document_type,
                            strategy="manifest",
                        )
                    )
                except Exception as exc:
                    trace.append(
                        AgentTraceEvent(
                            step="discover",
                            status="error",
                            detail=f"Manifest discovery failed: {exc}",
                            document_type=document_type,
                            strategy="manifest",
                        )
                    )

            dynamic_documents: list[DiscoveredDocument] = []
            if actions_used < self.max_actions:
                actions_used += 1
                try:
                    dynamic_documents = self.downloader.list_documents(document_type)
                    trace.append(
                        AgentTraceEvent(
                            step="discover",
                            status="ok" if dynamic_documents else "warning",
                            detail=f"AMC adapter returned {len(dynamic_documents)} candidate(s).",
                            document_type=document_type,
                            strategy=self.source.adapter_key.lower(),
                        )
                    )
                except Exception as exc:
                    trace.append(
                        AgentTraceEvent(
                            step="discover",
                            status="error",
                            detail=f"AMC adapter discovery failed: {exc}",
                            document_type=document_type,
                            strategy=self.source.adapter_key.lower(),
                        )
                    )

            last_known_good_documents: list[DiscoveredDocument] = []
            if self.last_known_good_loader and actions_used < self.max_actions:
                actions_used += 1
                try:
                    last_known_good_documents = self.last_known_good_loader(self.source, document_type)
                    trace.append(
                        AgentTraceEvent(
                            step="discover",
                            status="ok" if last_known_good_documents else "skipped",
                            detail=f"Loaded {len(last_known_good_documents)} last-known-good candidate(s).",
                            document_type=document_type,
                            strategy="last_known_good",
                        )
                    )
                except Exception as exc:
                    trace.append(
                        AgentTraceEvent(
                            step="discover",
                            status="warning",
                            detail=f"Last-known-good lookup failed: {exc}",
                            document_type=document_type,
                            strategy="last_known_good",
                        )
                    )

            candidates = _dedupe_candidates([*manifest_documents, *dynamic_documents, *last_known_good_documents])
            if not candidates and self.llm_recovery_loader and actions_used < self.max_actions:
                actions_used += 1
                try:
                    recovered = self.llm_recovery_loader(self.source, document_type)
                    candidates = _dedupe_candidates(recovered)
                    trace.append(
                        AgentTraceEvent(
                            step="recover",
                            status="ok" if candidates else "skipped",
                            detail=f"Bounded LLM recovery returned {len(candidates)} existing-page candidate(s).",
                            document_type=document_type,
                            strategy="bounded_llm_page_recovery",
                        )
                    )
                except Exception as exc:
                    trace.append(
                        AgentTraceEvent(
                            step="recover",
                            status="warning",
                            detail=f"Bounded LLM recovery failed: {exc}",
                            document_type=document_type,
                            strategy="bounded_llm_page_recovery",
                        )
                    )
            if not candidates:
                trace.append(
                    AgentTraceEvent(
                        step="select",
                        status="error",
                        detail="No candidate links were available; manual review is required.",
                        document_type=document_type,
                    )
                )
                trace.append(
                    AgentTraceEvent(
                        step="escalate",
                        status="error",
                        detail="Discovery produced no links; keep the last known good source and request review.",
                        document_type=document_type,
                    )
                )
                continue

            accepted_for_type = 0
            for candidate in candidates:
                if accepted_for_type >= max_candidates or actions_used >= self.max_actions:
                    break
                actions_used += 1
                errors, warnings = validate_candidate(
                    self.source,
                    candidate,
                    expected_month=expected_month,
                    expected_month_grace_days=expected_month_grace_days,
                )
                if errors:
                    trace.append(
                        AgentTraceEvent(
                            step="validate",
                            status="error",
                            detail="Candidate rejected: " + ", ".join(errors),
                            document_type=document_type,
                            strategy="deterministic_validation",
                            source_url=candidate.url,
                        )
                    )
                    continue

                probe_status = "not_requested"
                readiness = "link_validated"
                parser_smoke_status = "not_requested"
                content_status = "not_requested"
                checksum = None
                if probe_downloads:
                    if actions_used >= self.max_actions:
                        trace.append(
                            AgentTraceEvent(
                                step="probe",
                                status="skipped",
                                detail="Download probe skipped because the action budget was exhausted.",
                                document_type=document_type,
                                source_url=candidate.url,
                            )
                        )
                        break
                    actions_used += 1
                    try:
                        probe_method = getattr(self.downloader, "probe_download", None)
                        probed = (
                            probe_method(candidate)
                            if callable(probe_method)
                            else self.downloader.download(candidate)
                        )
                        probe_errors = validate_download(self.source, probed)
                    except Exception as exc:
                        probe_errors = [f"download_probe_failed:{exc}"]

                    if probe_errors:
                        trace.append(
                            AgentTraceEvent(
                                step="probe",
                                status="error",
                                detail="Candidate probe rejected: " + ", ".join(probe_errors),
                                document_type=document_type,
                                strategy="download_probe",
                                source_url=candidate.url,
                            )
                        )
                        continue
                    probe_status = "passed"
                    readiness = "probe_passed"

                    try:
                        downloaded = self.downloader.download(candidate)
                        content_errors = validate_download(self.source, downloaded)
                    except Exception as exc:
                        content_errors = [f"content_download_failed:{exc}"]

                    if content_errors:
                        trace.append(
                            AgentTraceEvent(
                                step="content_validate",
                                status="error",
                                detail="Candidate content rejected: " + ", ".join(content_errors),
                                document_type=document_type,
                                strategy="content_validation",
                                source_url=candidate.url,
                            )
                        )
                        continue

                    content_status = "passed"
                    readiness = "content_validated"
                    checksum = content_sha256(downloaded)
                    parser_errors = validate_parser_smoke(downloaded)
                    if parser_errors:
                        warnings.extend(parser_errors)
                        parser_smoke_status = "failed"
                        trace.append(
                            AgentTraceEvent(
                                step="parser_smoke",
                                status="warning",
                                detail="Candidate requires parser review: " + ", ".join(parser_errors),
                                document_type=document_type,
                                strategy="parser_smoke",
                                source_url=candidate.url,
                            )
                        )
                    else:
                        parser_smoke_status = "passed"
                        readiness = "parser_smoke_passed"
                else:
                    warnings.append("download_probe_skipped")

                if not warnings and readiness == "parser_smoke_passed":
                    readiness = "promotable"
                elif readiness != "failed":
                    readiness = "needs_review"

                accepted.append(
                    ValidatedDiscovery(
                        amc=self.source.amc_code,
                        document_type=document_type,
                        title=candidate.title,
                        source_url=candidate.url,
                        discovery_page_url=candidate.discovery_page_url,
                        expected_file_type=candidate.file_ext,
                        report_month=candidate.report_month,
                        priority_score=int(candidate.priority_score),
                        warnings=tuple(warnings),
                        probe_status=probe_status,
                        readiness=readiness,
                        month_confirmation="confirmed" if candidate.report_month else "unconfirmed",
                        content_sha256=checksum,
                        content_status=content_status,
                        parser_smoke_status=parser_smoke_status,
                    )
                )
                accepted_for_type += 1
                trace.append(
                    AgentTraceEvent(
                        step="accept",
                        status="warning" if readiness != "promotable" else "ok",
                        detail=(
                            f"Candidate {readiness}"
                            + (f" with warnings: {', '.join(warnings)}" if warnings else ".")
                        ),
                        document_type=document_type,
                        strategy="official_source_gate",
                        source_url=candidate.url,
                    )
                )

            if accepted_for_type == 0:
                trace.append(
                    AgentTraceEvent(
                        step="escalate",
                        status="error",
                        detail="No candidate passed validation; keep the last known good source and request review.",
                        document_type=document_type,
                    )
                )

        covered_types = {
            document.document_type
            for document in accepted
            if document.readiness == "promotable"
        }
        if len(covered_types) == len(set(document_types)):
            status = "completed"
        elif covered_types:
            status = "partial"
        else:
            status = "escalated"

        return DiscoveryAgentResult(
            agent_id=self.agent_id,
            amc=self.source.amc_code,
            status=status,
            requested_document_types=document_types,
            documents=accepted,
            trace=trace,
            actions_used=actions_used,
            max_actions=self.max_actions,
            started_at=started_at,
            completed_at=datetime.now(UTC).isoformat(),
        )


class HDFCLinkDiscoveryAgent(AMCLinkDiscoveryAgent):
    expected_adapter_key = "hdfc"


class AxisLinkDiscoveryAgent(AMCLinkDiscoveryAgent):
    expected_adapter_key = "axis"


class ICICILinkDiscoveryAgent(AMCLinkDiscoveryAgent):
    expected_adapter_key = "icici"


class SBILinkDiscoveryAgent(AMCLinkDiscoveryAgent):
    expected_adapter_key = "sbi"


class MiraeLinkDiscoveryAgent(AMCLinkDiscoveryAgent):
    expected_adapter_key = "mirae"


class PPFASLinkDiscoveryAgent(AMCLinkDiscoveryAgent):
    expected_adapter_key = "ppfas"


class NipponLinkDiscoveryAgent(AMCLinkDiscoveryAgent):
    expected_adapter_key = "nippon"


class KotakLinkDiscoveryAgent(AMCLinkDiscoveryAgent):
    expected_adapter_key = "kotak"


class AdityaBirlaLinkDiscoveryAgent(AMCLinkDiscoveryAgent):
    expected_adapter_key = "aditya_birla"


class UTILinkDiscoveryAgent(AMCLinkDiscoveryAgent):
    expected_adapter_key = "uti"


class DSPLinkDiscoveryAgent(AMCLinkDiscoveryAgent):
    expected_adapter_key = "dsp"


TOP_10_AMC_AGENT_KEYS = (
    "sbi",
    "mirae",
    "ppfas",
    "icici",
    "hdfc",
    "nippon",
    "kotak",
    "aditya_birla",
    "uti",
    "dsp",
)

AGENT_CLASSES: dict[str, type[AMCLinkDiscoveryAgent]] = {
    "aditya_birla": AdityaBirlaLinkDiscoveryAgent,
    "axis": AxisLinkDiscoveryAgent,
    "dsp": DSPLinkDiscoveryAgent,
    "hdfc": HDFCLinkDiscoveryAgent,
    "icici": ICICILinkDiscoveryAgent,
    "kotak": KotakLinkDiscoveryAgent,
    "mirae": MiraeLinkDiscoveryAgent,
    "nippon": NipponLinkDiscoveryAgent,
    "ppfas": PPFASLinkDiscoveryAgent,
    "sbi": SBILinkDiscoveryAgent,
    "uti": UTILinkDiscoveryAgent,
}

AGENT_KEY_ALIASES = {
    "absl": "aditya_birla",
    "aditya-birla": "aditya_birla",
    "aditya_birla_sun_life": "aditya_birla",
}


def build_discovery_agent(
    amc: str,
    *,
    config: IngestionConfig | None = None,
    max_actions: int = 12,
    last_known_good_loader: LastKnownGoodLoader | None = None,
    llm_recovery_loader: LLMRecoveryLoader | None = None,
) -> AMCLinkDiscoveryAgent:
    requested_key = str(amc or "").strip().lower()
    key = AGENT_KEY_ALIASES.get(requested_key, requested_key)
    agent_class = AGENT_CLASSES.get(key)
    if not agent_class:
        raise ValueError(f"No discovery agent configured for AMC: {amc}")
    resolved_config = config or get_config()
    source = get_source(key)
    downloader = AMCDownloader(source, resolved_config.request_timeout_seconds, resolved_config.user_agent)
    return agent_class(
        source=source,
        downloader=downloader,
        manifest_path=resolved_config.source_manifest_path,
        last_known_good_loader=last_known_good_loader,
        llm_recovery_loader=llm_recovery_loader,
        max_actions=max_actions,
    )


def _dedupe_candidates(documents: list[DiscoveredDocument]) -> list[DiscoveredDocument]:
    best_by_url: dict[str, DiscoveredDocument] = {}
    for document in documents:
        key = str(document.url or "").strip().lower()
        if not key:
            continue
        existing = best_by_url.get(key)
        if existing is None or document.priority_score > existing.priority_score:
            best_by_url[key] = document
    return sorted(best_by_url.values(), key=lambda item: item.priority_score, reverse=True)
