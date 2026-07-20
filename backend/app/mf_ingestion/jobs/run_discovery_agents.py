from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from datetime import date, datetime
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from dotenv import load_dotenv

load_dotenv(os.path.join(BASE_DIR, ".env"))

from app.mf_ingestion.agents.discovery_agent import TOP_10_AMC_AGENT_KEYS
from app.mf_ingestion.agents.supervisor import AMCDiscoverySupervisor

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
    parser.add_argument("--max-candidates", type=int, default=1)
    parser.add_argument("--max-actions", type=int, default=12)
    parser.add_argument("--skip-download-probes", action="store_true")
    parser.add_argument("--output", help="Optional path for the complete JSON report.")
    parser.add_argument("--manifest-output", help="Optional path for the validated source manifest.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero unless every agent completes.")
    args = parser.parse_args()

    if not args.document_type and not args.all_document_types:
        parser.error("Provide either --document-type or --all-document-types")

    amcs = [item.strip().lower() for item in args.amcs.split(",") if item.strip()]
    document_types = DOCUMENT_TYPES if args.all_document_types else (args.document_type,)
    expected_month = _parse_expected_month(args.expected_month)
    supervisor = AMCDiscoverySupervisor.build(amcs, max_actions_per_agent=args.max_actions)
    result = supervisor.run(
        document_types=document_types,
        expected_month=expected_month,
        max_candidates_per_type=args.max_candidates,
        probe_downloads=not args.skip_download_probes,
    )
    payload = result.to_dict()
    rendered = json.dumps(payload, indent=2, default=str)
    logger.info(rendered)

    if args.output:
        _write_json(args.output, payload)
    if args.manifest_output:
        _write_json(args.manifest_output, payload["manifest"])

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
