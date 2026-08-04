from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.mf_ingestion.automation_scope import resolve_automation_scope


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--operation", required=True, choices=("discovery", "parser_retry", "disclosure_parse", "research_index"))
    parser.add_argument("--lane", default="green", choices=("green", "approved_restricted", "validation_only"))
    parser.add_argument("--amcs", default="")
    parser.add_argument("--event-name", default="workflow_dispatch")
    parser.add_argument("--source-document-ids", default="")
    parser.add_argument("--format", default="csv", choices=("csv", "json"))
    args = parser.parse_args()

    try:
        amcs = resolve_automation_scope(
            operation=args.operation,
            lane=args.lane,
            raw_amcs=args.amcs,
            event_name=args.event_name,
            source_document_ids=args.source_document_ids,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    print(json.dumps(list(amcs)) if args.format == "json" else ",".join(amcs))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
