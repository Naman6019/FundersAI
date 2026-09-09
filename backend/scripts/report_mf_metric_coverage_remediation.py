from __future__ import annotations

"""Create a read-only, approval-gated promotion manifest for metric coverage gaps."""

import argparse
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Callable

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.database import supabase
from app.mf_ingestion.sources.registry import get_source_by_code
from app.services.mf_metric_target_service import supported_metric_targets


PAGE_SIZE = 1000
IN_QUERY_BATCH_SIZE = 250
FIELD_SPECS = (
    ("benchmark", "benchmark", "benchmark"),
    ("risk", "risk_level", "risk"),
)
OPEN_PROMOTION_STATUSES = {"staged", "partially_promoted"}
METRIC_COVERAGE_MINIMUM = 0.95


def _text(value: object) -> str:
    return str(value or "").strip()


def _has_value(value: object) -> bool:
    return bool(_text(value))


def _normalized_value(value: object) -> str:
    return " ".join(_text(value).lower().split())


def _chunks(values: list[str], size: int = IN_QUERY_BATCH_SIZE) -> list[list[str]]:
    return [values[start : start + size] for start in range(0, len(values), size)]


def _fetch_rows_in(
    client: Any,
    table: str,
    columns: str,
    *,
    column: str,
    values: list[str],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for batch in _chunks(values):
        offset = 0
        while True:
            page = (
                client.table(table)
                .select(columns)
                .in_(column, batch)
                .range(offset, offset + PAGE_SIZE - 1)
                .execute()
                .data
                or []
            )
            rows.extend(row for row in page if isinstance(row, dict))
            if len(page) < PAGE_SIZE:
                break
            offset += PAGE_SIZE
    return rows


def _candidate_matches_target(candidate: dict[str, Any], target: dict[str, Any]) -> bool:
    try:
        confidence = float(candidate.get("mapping_confidence") or 0)
    except (TypeError, ValueError):
        confidence = 0.0
    selected_candidate_id = _text(target.get("candidate_id"))
    selected_source_document_id = _text(target.get("source_document_id"))
    return (
        candidate.get("mapping_status") == "mapped"
        and confidence >= 90.0
        and (not selected_candidate_id or _text(candidate.get("id")) == selected_candidate_id)
        and (
            not selected_source_document_id
            or _text(candidate.get("source_document_id")) == selected_source_document_id
        )
        and _text(candidate.get("report_month")) == _text(target.get("report_month"))
        and _text(candidate.get("amc_code")).lower()
        == _text(target.get("amc_code")).lower()
        and _text(candidate.get("mapped_family_id")) == _text(target.get("family_id"))
        and _text(candidate.get("promotion_status")).lower() != "rejected"
    )


def _candidate_evidence_issues(
    *,
    candidate: dict[str, Any],
    target: dict[str, Any],
    mapping_by_code: dict[str, str],
    document_by_id: dict[str, dict[str, Any]],
    source_lookup: Callable[[str], Any],
) -> list[str]:
    issues: list[str] = []
    scheme_code = _text(candidate.get("mapped_scheme_code"))
    if mapping_by_code.get(scheme_code) != _text(target.get("family_id")):
        issues.append("mapping_changed")

    status = _text(candidate.get("promotion_status")).lower()
    if status == "needs_review":
        issues.append("candidate_needs_review")
    elif status not in OPEN_PROMOTION_STATUSES:
        issues.append("candidate_not_open_for_promotion")

    try:
        source = source_lookup(_text(candidate.get("amc_code")))
    except ValueError:
        source = None
    if not source:
        issues.append("source_unknown")
    elif not bool(getattr(source, "promotion_enabled", False)):
        issues.append("promotion_disabled")

    source_document_id = _text(candidate.get("source_document_id"))
    document = document_by_id.get(source_document_id)
    if not document:
        issues.append("source_document_missing")
        return issues
    if not _has_value(candidate.get("report_month")):
        issues.append("candidate_report_month_missing")
    if _text(document.get("amc_code")).lower() != _text(candidate.get("amc_code")).lower():
        issues.append("source_document_amc_mismatch")
    if _text(document.get("report_month")) != _text(candidate.get("report_month")):
        issues.append("source_document_report_month_mismatch")
    if _text(document.get("parse_status")).lower() not in {"parsed", "parsed_partial"}:
        issues.append("source_not_parsed")
    if _text(document.get("storage_backend")).lower() != "r2":
        issues.append("source_not_r2_backed")
    if not _has_value(document.get("checksum")) or not _has_value(document.get("storage_key")):
        issues.append("source_evidence_missing")
    if document.get("checksum") != candidate.get("checksum"):
        issues.append("candidate_checksum_mismatch")
    if document.get("storage_key") != candidate.get("storage_key"):
        issues.append("candidate_storage_key_mismatch")
    if not _has_value(candidate.get("id")):
        issues.append("candidate_id_missing")
    return sorted(set(issues))


def _coverage_gate_projection(
    *,
    target_by_code: dict[str, dict[str, Any]],
    core_by_code: dict[str, dict[str, Any]],
    conditional_scheme_codes: dict[str, set[str]],
) -> dict[str, Any]:
    """Report a conditional 95% projection without treating staged data as live."""
    total = len(target_by_code)
    required_count = math.ceil(total * METRIC_COVERAGE_MINIMUM)
    fields: dict[str, dict[str, Any]] = {}
    for label, core_column, _ in FIELD_SPECS:
        live_scheme_codes = {
            scheme_code
            for scheme_code in target_by_code
            if _has_value(core_by_code.get(scheme_code, {}).get(core_column))
        }
        promotable_scheme_codes = conditional_scheme_codes.get(label, set()) - live_scheme_codes
        projected_count = len(live_scheme_codes | promotable_scheme_codes)
        fields[label] = {
            "current_count": len(live_scheme_codes),
            "current_coverage": round(len(live_scheme_codes) / total, 6) if total else 0.0,
            "required_additional_count": max(0, required_count - len(live_scheme_codes)),
            "conditional_manual_promotion_count": len(promotable_scheme_codes),
            "conditional_projected_count": projected_count,
            "conditional_projected_coverage": round(projected_count / total, 6) if total else 0.0,
            "conditional_projected_gate_passes": total > 0 and projected_count >= required_count,
        }
    return {
        "minimum_coverage": METRIC_COVERAGE_MINIMUM,
        "supported_mapped_total": total,
        "required_count": required_count,
        "fields": fields,
        "all_fields_can_pass_with_current_manifest": total > 0
        and all(
            field["conditional_projected_gate_passes"]
            for field in fields.values()
        ),
        "condition": (
            "Projection is conditional: every listed batch must pass the existing dry-run "
            "and receive manual typed approval before any runtime write."
        ),
    }


def build_metric_coverage_remediation(
    *,
    targets: list[dict[str, Any]],
    core_by_code: dict[str, dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    mapping_by_code: dict[str, str],
    document_by_id: dict[str, dict[str, Any]],
    source_lookup: Callable[[str], Any] = get_source_by_code,
) -> dict[str, Any]:
    """Return only candidates that still need the existing manual promotion flow.

    This deliberately does not treat a staged value as runtime evidence. The
    manifest is input for a `Promote MF Disclosures` dry-run; that workflow
    revalidates the complete candidate and source-document gates before writing.
    """
    target_by_code = {
        _text(row.get("scheme_code")): row
        for row in targets
        if _has_value(row.get("scheme_code"))
    }
    if not target_by_code:
        return {
            "status": "error",
            "issues": ["no_supported_mapped_schemes"],
            "supported_mapped_total": 0,
            "fields": {},
            "promotion_review_batches": [],
            "safety": {
                "writes_runtime_data": False,
                "lowers_coverage_thresholds": False,
                "treats_staged_values_as_live_evidence": False,
                "requires_existing_promotion_dry_run": True,
            },
        }
    candidates_by_code: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for candidate in candidate_rows:
        scheme_code = _text(candidate.get("mapped_scheme_code"))
        target = target_by_code.get(scheme_code)
        if target and _candidate_matches_target(candidate, target):
            candidates_by_code[scheme_code].append(candidate)

    field_reports: dict[str, dict[str, Any]] = {
        label: {
            "missing_live_count": 0,
            "manual_review_candidate_count": 0,
            "blocked_counts": Counter(),
        }
        for label, _, _ in FIELD_SPECS
    }
    conditional_scheme_codes = {label: set() for label, _, _ in FIELD_SPECS}
    # (source document, candidate id, scheme code) -> exact unpromoted scopes.
    proposals: dict[tuple[str, str, str], set[str]] = defaultdict(set)

    for scheme_code, target in sorted(target_by_code.items()):
        core = core_by_code.get(scheme_code, {})
        current_candidates = candidates_by_code.get(scheme_code, [])
        for label, core_column, promotion_scope in FIELD_SPECS:
            report = field_reports[label]
            if _has_value(core.get(core_column)):
                continue
            report["missing_live_count"] += 1

            with_value = [
                candidate
                for candidate in current_candidates
                if _has_value(candidate.get(core_column))
            ]
            if not with_value:
                report["blocked_counts"]["candidate_value_missing"] += 1
                continue

            technical_candidates: list[dict[str, Any]] = []
            blocked_reasons: set[str] = set()
            for candidate in with_value:
                promoted_scopes = {
                    _text(scope).lower() for scope in (candidate.get("promoted_scopes") or [])
                }
                if promotion_scope in promoted_scopes:
                    blocked_reasons.add("previously_promoted_missing_runtime_field")
                    continue
                issues = _candidate_evidence_issues(
                    candidate=candidate,
                    target=target,
                    mapping_by_code=mapping_by_code,
                    document_by_id=document_by_id,
                    source_lookup=source_lookup,
                )
                if issues:
                    blocked_reasons.update(issues)
                    continue
                technical_candidates.append(candidate)

            if not technical_candidates:
                for reason in sorted(blocked_reasons or {"candidate_not_promotable"}):
                    report["blocked_counts"][reason] += 1
                continue

            values = {_normalized_value(candidate.get(core_column)) for candidate in technical_candidates}
            if len(values) != 1:
                report["blocked_counts"]["conflicting_current_candidate_values"] += 1
                continue
            source_document_ids = {
                _text(candidate.get("source_document_id")) for candidate in technical_candidates
            }
            if len(source_document_ids) != 1:
                # The coverage target does not identify which same-month document
                # should win. Require a human to select one rather than guessing.
                report["blocked_counts"]["multiple_current_source_documents"] += 1
                continue

            candidate = max(
                technical_candidates,
                key=lambda row: (_text(row.get("updated_at")), _text(row.get("id"))),
            )
            proposal_key = (
                _text(candidate.get("source_document_id")),
                _text(candidate.get("id")),
                scheme_code,
            )
            proposals[proposal_key].add(promotion_scope)
            conditional_scheme_codes[label].add(scheme_code)
            report["manual_review_candidate_count"] += 1

    batches: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    scope_order = {"benchmark": 0, "risk": 1}
    for (source_document_id, candidate_id, scheme_code), scopes in proposals.items():
        ordered_scopes = tuple(sorted(scopes, key=scope_order.__getitem__))
        candidate = next(
            candidate
            for candidate in candidates_by_code[scheme_code]
            if _text(candidate.get("id")) == candidate_id
        )
        key = (source_document_id, ordered_scopes)
        batch = batches.setdefault(
            key,
            {
                "workflow": "Promote MF Disclosures",
                "source_document_id": source_document_id,
                "amc_code": _text(candidate.get("amc_code")),
                "expected_month": _text(candidate.get("report_month"))[:7],
                "scopes": list(ordered_scopes),
                "candidate_ids": [],
                "affected_scheme_codes": [],
                "apply": False,
                "note": "Run a dry-run first; the existing workflow revalidates every gate before any write.",
            },
        )
        batch["candidate_ids"].append(candidate_id)
        batch["affected_scheme_codes"].append(scheme_code)

    for report in field_reports.values():
        report["blocked_counts"] = dict(sorted(report["blocked_counts"].items()))
    promotion_review_batches = []
    for batch in batches.values():
        batch["candidate_ids"].sort()
        batch["affected_scheme_codes"].sort()
        promotion_review_batches.append(batch)
    promotion_review_batches.sort(
        key=lambda batch: (
            batch["amc_code"],
            batch["expected_month"],
            batch["source_document_id"],
            batch["scopes"],
        )
    )

    missing_total = sum(
        int(report["missing_live_count"]) for report in field_reports.values()
    )
    return {
        "status": "healthy" if missing_total == 0 else "action_required",
        "supported_mapped_total": len(target_by_code),
        "fields": field_reports,
        "coverage_gate_projection": _coverage_gate_projection(
            target_by_code=target_by_code,
            core_by_code=core_by_code,
            conditional_scheme_codes=conditional_scheme_codes,
        ),
        "promotion_review_batches": promotion_review_batches,
        "safety": {
            "writes_runtime_data": False,
            "lowers_coverage_thresholds": False,
            "treats_staged_values_as_live_evidence": False,
            "requires_existing_promotion_dry_run": True,
        },
    }


def collect_metric_coverage_remediation(client: Any) -> dict[str, Any]:
    targets = supported_metric_targets(client)
    target_codes = sorted(
        {_text(row.get("scheme_code")) for row in targets if _has_value(row.get("scheme_code"))}
    )
    if not target_codes:
        return build_metric_coverage_remediation(
            targets=[],
            core_by_code={},
            candidate_rows=[],
            mapping_by_code={},
            document_by_id={},
        )

    core_rows = _fetch_rows_in(
        client,
        "mutual_fund_core_snapshot",
        "scheme_code,benchmark,risk_level",
        column="scheme_code",
        values=target_codes,
    )
    candidate_rows = _fetch_rows_in(
        client,
        "mf_factsheet_candidates",
        "id,source_document_id,amc_code,report_month,mapped_scheme_code,mapped_family_id,"
        "mapping_status,mapping_confidence,promotion_status,promoted_scopes,benchmark,risk_level,"
        "checksum,storage_key,updated_at",
        column="mapped_scheme_code",
        values=target_codes,
    )
    mapping_rows = _fetch_rows_in(
        client,
        "mutual_fund_family_mapping",
        "scheme_code,family_id",
        column="scheme_code",
        values=target_codes,
    )
    source_document_ids = sorted(
        {
            _text(row.get("source_document_id"))
            for row in candidate_rows
            if _has_value(row.get("source_document_id"))
        }
    )
    document_rows = _fetch_rows_in(
        client,
        "mf_raw_documents",
        "id,amc_code,report_month,parse_status,storage_backend,checksum,storage_key",
        column="id",
        values=source_document_ids,
    )
    return build_metric_coverage_remediation(
        targets=targets,
        core_by_code={
            _text(row.get("scheme_code")): row
            for row in core_rows
            if _has_value(row.get("scheme_code"))
        },
        candidate_rows=candidate_rows,
        mapping_by_code={
            _text(row.get("scheme_code")): _text(row.get("family_id"))
            for row in mapping_rows
            if _has_value(row.get("scheme_code")) and _has_value(row.get("family_id"))
        },
        document_by_id={
            _text(row.get("id")): row
            for row in document_rows
            if _has_value(row.get("id"))
        },
    )


def _write_payload(path: str, payload: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Report read-only promotion batches for missing benchmark and risk coverage."
    )
    parser.add_argument("--output", default="mf-metric-coverage-remediation-health.json")
    args = parser.parse_args(argv)

    if not supabase:
        payload = {"status": "error", "issues": ["supabase_not_configured"]}
        _write_payload(args.output, payload)
        print(json.dumps(payload, indent=2))
        return 2
    try:
        payload = collect_metric_coverage_remediation(supabase)
    except Exception:
        payload = {"status": "error", "issues": ["coverage_remediation_report_failed"]}
        _write_payload(args.output, payload)
        print(json.dumps(payload, indent=2))
        return 2

    _write_payload(args.output, payload)
    print(json.dumps(payload, indent=2, default=str))
    return 2 if payload.get("status") == "error" else 0


if __name__ == "__main__":
    raise SystemExit(main())
