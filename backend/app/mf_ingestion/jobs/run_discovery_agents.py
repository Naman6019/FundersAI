from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.database import supabase
from app.mf_ingestion.agents.discovery_agent import TOP_10_AMC_AGENT_KEYS
from app.mf_ingestion.agents.history import (
    build_discovery_diff,
    build_source_configuration_candidates,
    load_last_known_good_documents,
    load_recent_document_observations,
)
from app.mf_ingestion.agents.llm_recovery import BoundedLLMPageRecovery
from app.mf_ingestion.agents.persistence import persist_discovery_run
from app.mf_ingestion.agents.supervisor import AMCDiscoverySupervisor
from app.mf_ingestion.config import get_config
from app.mf_ingestion.storage.r2_store import R2Store

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DOCUMENT_TYPES = ("factsheet", "portfolio_disclosure")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run bounded official AMC link-discovery agents.")
    parser.add_argument(
        "--amcs",
        default=",".join(TOP_10_AMC_AGENT_KEYS),
        help="Comma-separated specialist agent keys; defaults to the configured top ten AMCs.",
    )
    parser.add_argument("--document-type", choices=DOCUMENT_TYPES)
    parser.add_argument("--all-document-types", action="store_true")
    parser.add_argument("--expected-month", help="Expected report month in YYYY-MM format.")
    parser.add_argument("--expected-month-grace-days", type=int, default=14)
    parser.add_argument("--max-candidates", type=int, default=3)
    parser.add_argument("--max-actions", type=int, default=12)
    parser.add_argument("--skip-download-probes", action="store_true")
    parser.add_argument("--output", help="Optional path for the complete JSON report.")
    parser.add_argument("--manifest-output", help="Optional path for the validated source manifest.")
    parser.add_argument("--persist-run", action="store_true", help="Persist the report to R2 and its summary to Supabase.")
    parser.add_argument("--run-id", help="Stable run identifier; defaults to a generated UUID.")
    parser.add_argument("--trigger-source", default="local_cli", help="Run source recorded in the persisted summary.")
    parser.add_argument("--minimum-completed", type=int, default=0, help="Exit non-zero when fewer agents complete.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless every agent completes.")
    args = parser.parse_args()

    if not args.document_type and not args.all_document_types:
        parser.error("Provide either --document-type or --all-document-types")

    amcs = [item.strip().lower() for item in args.amcs.split(",") if item.strip()]
    if args.minimum_completed < 0 or args.minimum_completed > len(amcs):
        parser.error("--minimum-completed must be between zero and the requested AMC count")
    document_types = DOCUMENT_TYPES if args.all_document_types else (args.document_type,)
    expected_month = _parse_expected_month(args.expected_month)
    last_known_good_loader = None
    previous_documents: list[dict] = []
    if args.persist_run and supabase is not None:
        last_known_good_loader = lambda source, document_type: load_last_known_good_documents(
            supabase,
            source,
            document_type,
        )
        try:
            previous_documents = load_recent_document_observations(
                supabase,
                amcs=amcs,
                document_types=document_types,
            )
        except Exception as exc:
            logger.warning("Unable to load discovery history: %s", exc)
    config = get_config()
    llm_recovery_loader = BoundedLLMPageRecovery(
        enabled=config.discovery_llm_recovery_enabled,
        model=config.discovery_llm_recovery_model,
    )
    supervisor = AMCDiscoverySupervisor.build(
        amcs,
        max_actions_per_agent=args.max_actions,
        last_known_good_loader=last_known_good_loader,
        llm_recovery_loader=llm_recovery_loader,
    )
    result = supervisor.run(
        document_types=document_types,
        expected_month=expected_month,
        expected_month_grace_days=max(args.expected_month_grace_days, 0),
        max_candidates_per_type=args.max_candidates,
        probe_downloads=not args.skip_download_probes,
    )
    payload = result.to_dict()
    run_id = str(args.run_id or uuid4()).strip()
    payload["run"] = {
        "run_id": run_id,
        "trigger_source": args.trigger_source,
        "expected_month": expected_month.isoformat() if expected_month else None,
        "expected_month_grace_days": max(args.expected_month_grace_days, 0),
        "requested_amcs": amcs,
        "document_types": list(document_types),
    }
    payload["manifest"]["run_id"] = run_id
    current_documents = list(payload["manifest"].get("documents") or [])
    payload["diff"] = build_discovery_diff(previous_documents, current_documents)
    payload["source_configuration_candidates"] = build_source_configuration_candidates(
        [*previous_documents, *current_documents]
    )
    rendered = json.dumps(payload, indent=2, default=str)
    logger.info(rendered)

    if args.output:
        _write_json(args.output, payload)
    if args.manifest_output:
        _write_json(args.manifest_output, payload["manifest"])

    if args.persist_run:
        r2_store = R2Store(
            endpoint=config.r2_endpoint,
            access_key_id=config.r2_access_key_id,
            secret_access_key=config.r2_secret_access_key,
            raw_bucket=config.r2_raw_bucket,
            cold_bucket=config.r2_cold_bucket,
            signed_url_ttl_seconds=config.r2_signed_url_ttl_seconds,
        )
        summary = persist_discovery_run(
            payload,
            run_id=run_id,
            trigger_source=args.trigger_source,
            expected_month=expected_month.isoformat() if expected_month else None,
            requested_amcs=amcs,
            document_types=document_types,
            r2_store=r2_store,
            r2_bucket=config.r2_cold_bucket,
            supabase_client=supabase,
        )
        logger.info("Persisted discovery run: %s", json.dumps(summary, default=str))

    completed_count = sum(agent.status == "completed" for agent in result.agents)
    if completed_count < args.minimum_completed:
        logger.error(
            "Discovery completion gate failed: completed=%s minimum=%s",
            completed_count,
            args.minimum_completed,
        )
        return 1

    return 1 if args.strict and result.status != "completed" else 0


def _parse_expected_month(value: str | None) -> date | None:
    if not value:
        return None
    try:
        parsed = datetime.strptime(value.strip(), "%Y-%m")
    except ValueError as exc:
        raise SystemExit("--expected-month must use YYYY-MM") from exc
    return date(parsed.year, parsed.month, 1)


def _write_json(raw_path: str, payload: object) -> None:
    path = Path(raw_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
