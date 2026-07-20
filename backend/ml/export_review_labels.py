from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from app.repositories.admin_ops_repository import AdminOpsRepository
except ModuleNotFoundError:  # Supports repository-root module execution.
    from backend.app.repositories.admin_ops_repository import AdminOpsRepository


EXPORT_FIELDS = (
    "source_document_id",
    "amc_code",
    "report_month",
    "validation_issues",
    "confidence_score",
    "parser_version",
    "status",
    "source_url",
    "created_at",
    "updated_at",
    "reviewed_at",
    "review_duration_seconds",
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Export reviewer outcomes without notes or sample document contents")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int, default=10000)
    args = parser.parse_args()
    repository = AdminOpsRepository()
    if not repository:
        raise SystemExit("supabase_unavailable")
    rows = repository.list_reviewed_review_items(limit=max(1, args.limit))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps({field: row.get(field) for field in EXPORT_FIELDS}, default=str, sort_keys=True) + "\n")
    print(json.dumps({"status": "ok", "rows": len(rows), "output": str(args.output)}))


if __name__ == "__main__":
    main()
