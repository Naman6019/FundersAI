from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import date
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

load_dotenv(BACKEND / ".env")
load_dotenv(ROOT / ".env")

from app.database import supabase
from app.mf_ingestion.parsers.base_parser import ParseContext
from app.mf_ingestion.parsers.factsheet_parser import filter_factsheet_records_for_amc
from app.mf_ingestion.parsers.holdings_parser import HoldingsParser
from app.mf_ingestion.services.parsing_service import ParsingService
from app.mf_ingestion.sources.registry import get_source_by_code


def _parse_list(raw: str) -> list[str]:
    return [value.strip() for value in raw.split(",") if value.strip()]


def _factsheet_summary(records: list[Any]) -> dict[str, Any]:
    fields = ("aum", "expense_ratio", "benchmark", "fund_manager", "risk_level")
    record_count = len(records)
    field_counts = {
        field: sum(1 for record in records if getattr(record, field, None) not in (None, ""))
        for field in fields
    }
    return {
        "record_count": record_count,
        "field_counts": field_counts,
        "field_coverage_percent": {
            field: round((count / record_count) * 100.0, 2) if record_count else 0.0
            for field, count in field_counts.items()
        },
        "missing_sample_schemes": {
            field: [
                str(record.scheme_name)
                for record in records
                if getattr(record, field, None) in (None, "")
            ][:8]
            for field in fields
        },
        "sample_schemes": [str(record.scheme_name) for record in records[:5]],
    }


def _portfolio_summary(batch: Any) -> dict[str, Any]:
    records = list(batch.records)
    return {
        "record_count": len(records),
        "holding_count": sum(len(record.holdings) for record in records),
        "sector_count": len(
            {
                str(row.get("sector")).strip()
                for record in records
                for row in record.holdings
                if str(row.get("sector") or "").strip()
            }
        ),
        "successful_sources": batch.successful_sources,
        "empty_sources": batch.empty_sources,
        "failed_sources": batch.failed_sources,
        "diagnostics": [diagnostic.to_dict() for diagnostic in batch.diagnostics],
        "sample_schemes": [str(record.scheme_name) for record in records[:5]],
    }


def _aggregate_results(results: list[dict[str, Any]]) -> dict[str, Any]:
    by_amc: dict[str, dict[str, Any]] = {}
    for item in results:
        amc = str(item.get("amc") or "unknown")
        summary = by_amc.setdefault(
            amc,
            {
                "documents": 0,
                "passed_documents": 0,
                "failed_documents": 0,
                "factsheet_records": 0,
                "factsheet_field_counts": {
                    "aum": 0,
                    "expense_ratio": 0,
                    "benchmark": 0,
                    "fund_manager": 0,
                    "risk_level": 0,
                },
                "portfolio_records": 0,
                "holdings": 0,
                "sectors": 0,
                "failed_document_samples": [],
            },
        )
        summary["documents"] += 1
        passed = item.get("status") == "passed"
        summary["passed_documents"] += int(passed)
        summary["failed_documents"] += int(not passed)
        if item.get("document_type") == "factsheet":
            summary["factsheet_records"] += int(item.get("record_count") or 0)
            for field, count in (item.get("field_counts") or {}).items():
                if field in summary["factsheet_field_counts"]:
                    summary["factsheet_field_counts"][field] += int(count or 0)
        else:
            summary["portfolio_records"] += int(item.get("record_count") or 0)
            summary["holdings"] += int(item.get("holding_count") or 0)
            summary["sectors"] += int(item.get("sector_count") or 0)
        if not passed and len(summary["failed_document_samples"]) < 10:
            summary["failed_document_samples"].append(
                {
                    "source_document_id": item.get("source_document_id"),
                    "document_type": item.get("document_type"),
                    "reason": item.get("reason"),
                    "source_url": item.get("source_url"),
                }
            )

    for summary in by_amc.values():
        record_count = summary["factsheet_records"]
        summary["factsheet_field_coverage_percent"] = {
            field: round((count / record_count) * 100.0, 2) if record_count else 0.0
            for field, count in summary["factsheet_field_counts"].items()
        }
    return by_amc


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only full-parser smoke test for R2-backed AMC documents.")
    parser.add_argument("--amcs", required=True, help="Comma-separated AMC codes or adapter keys.")
    parser.add_argument("--report-month", required=True, help="Exact report month in YYYY-MM-DD form.")
    parser.add_argument(
        "--statuses",
        default="all",
        help="Comma-separated parse statuses, or 'all' for every exact-month raw document.",
    )
    parser.add_argument("--limit-per-amc", type=int, default=10)
    parser.add_argument(
        "--save-dir",
        help="Optional local directory for retaining the downloaded raw documents used by the smoke pass.",
    )
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args()

    if not supabase:
        print(json.dumps({"status": "error", "reason": "supabase_not_configured"}))
        return 1

    service = ParsingService()
    statuses = [] if args.statuses.strip().lower() == "all" else _parse_list(args.statuses)
    report_month = date.fromisoformat(args.report_month)
    results: list[dict[str, Any]] = []
    failures = 0

    for requested_amc in _parse_list(args.amcs):
        source = get_source_by_code(requested_amc)
        query = (
            supabase.table("mf_raw_documents")
            .select("*")
            .in_("amc_code", [source.amc_code, source.amc_code.lower(), source.adapter_key])
            .eq("report_month", args.report_month)
            .order("downloaded_at", desc=False)
            .limit(max(1, args.limit_per_amc))
        )
        if statuses:
            query = query.in_("parse_status", statuses)
        rows = query.execute().data or []
        for document in rows:
            resolved_path, temporary_path = service._resolve_document_path(document)
            item: dict[str, Any] = {
                "source_document_id": document.get("id"),
                "amc": source.adapter_key,
                "document_type": document.get("document_type"),
                "report_month": document.get("report_month"),
                "parse_status": document.get("parse_status"),
                "source_url": document.get("source_url"),
                "storage_key": document.get("storage_key"),
            }
            try:
                if not resolved_path:
                    item.update(status="failed", reason="raw_file_unavailable")
                    failures += 1
                else:
                    if args.save_dir:
                        save_dir = Path(args.save_dir).resolve()
                        save_dir.mkdir(parents=True, exist_ok=True)
                        suffix = Path(resolved_path).suffix or ".bin"
                        saved_path = save_dir / (
                            f"{source.adapter_key}-{document.get('document_type')}-"
                            f"{document.get('id')}{suffix}"
                        )
                        shutil.copy2(resolved_path, saved_path)
                        item["saved_path"] = str(saved_path)

                if not resolved_path:
                    pass
                elif str(document.get("document_type") or "").lower() == "factsheet":
                    records = filter_factsheet_records_for_amc(
                        service.factsheet_parser.parse(
                            resolved_path,
                            ParseContext(
                                source_document_id=str(document.get("id")),
                                source_url=str(document.get("source_url") or ""),
                                report_month=report_month,
                            ),
                        ),
                        source.amc_code,
                    )
                    summary = _factsheet_summary(records)
                    item.update(status="passed" if records else "failed", **summary)
                    failures += int(not records)
                else:
                    adapter = service.adapters[source.adapter_key]
                    batch = HoldingsParser(adapter).parse_batch(
                        resolved_path,
                        ParseContext(
                            source_document_id=str(document.get("id")),
                            source_url=str(document.get("source_url") or ""),
                            report_month=report_month,
                        ),
                    )
                    summary = _portfolio_summary(batch)
                    item.update(status="passed" if batch.records else "failed", **summary)
                    failures += int(not batch.records)
            except Exception as exc:
                item.update(status="failed", reason=f"{type(exc).__name__}:{exc}")
                failures += 1
            finally:
                if temporary_path:
                    Path(temporary_path).unlink(missing_ok=True)
            results.append(item)

    status = "passed" if results and failures == 0 else "partial" if results else "failed"
    payload: dict[str, Any] = {
        "status": status,
        "failures": failures,
        "summary_by_amc": _aggregate_results(results),
    }
    if not args.summary_only:
        payload["documents"] = results
    print(json.dumps(payload, indent=2, default=str))
    return 0 if status == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
