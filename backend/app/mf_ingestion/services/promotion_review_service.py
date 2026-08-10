from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
from typing import Any

from app.database import supabase
from app.mf_ingestion.constants import ReportMonthWindow
from app.mf_ingestion.jobs.promote_mf_disclosures import (
    _parse_report_month,
    apply_family_invariant_propagation,
    apply_promotable_report,
    build_dry_run,
    build_family_invariant_propagation_plan,
)
from app.services.supported_amcs import supported_amc_label_from_text

AMC_KEY_ALIASES = {"absl": "aditya_birla"}
DECISIONS_TABLE = "mf_promotion_review_decisions"
ALLOWED_SCOPES = {"risk", "holdings"}
ALLOWED_RESOLUTIONS = {"use_staged", "use_live", "exclude"}


def _normalize_amc_key(value: object) -> str:
    key = str(value or "").strip().lower()
    return AMC_KEY_ALIASES.get(key, key)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_filtered(
    table: str,
    columns: str,
    *,
    filters: dict[str, Any],
    page_size: int = 1000,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    start = 0
    while True:
        query = supabase.table(table).select(columns)
        for column, value in filters.items():
            if isinstance(value, (list, tuple, set)):
                query = query.in_(column, list(value))
            else:
                query = query.eq(column, value)
        page = query.order("id").range(start, start + page_size - 1).execute().data or []
        rows.extend(page)
        if len(page) < page_size:
            return rows
        start += page_size


def _fetch_source_documents(document_ids: set) -> dict[str, dict[str, Any]]:
    ids = sorted({str(value) for value in document_ids if value})
    if not ids:
        return {}
    rows: list[dict[str, Any]] = []
    for start in range(0, len(ids), 500):
        rows.extend(
            supabase.table("mf_raw_documents")
            .select("id,amc_code,document_type,report_month,source_url,storage_bucket,storage_key,checksum")
            .in_("id", ids[start : start + 500])
            .execute()
            .data
            or []
        )
    return {str(row["id"]): row for row in rows}


def get_decisions(*, amc: str, report_month: str, scope: str) -> dict[str, dict[str, Any]]:
    """subject_key -> decision row, for the given amc/month/scope."""
    normalized_amc = _normalize_amc_key(amc)
    rows = _get_filtered(
        DECISIONS_TABLE,
        "*",
        filters={"amc_code": normalized_amc, "report_month": report_month, "scope": scope},
    )
    return {str(row["subject_key"]): row for row in rows}


def upsert_decision(
    *,
    amc: str,
    report_month: str,
    scope: str,
    subject_key: str,
    subject_label: str | None,
    resolution: str,
    decided_value: dict[str, Any],
    source_document_id: str | None,
    reviewed_by: str,
    note: str | None = None,
) -> dict[str, Any]:
    if scope not in ALLOWED_SCOPES:
        raise ValueError(f"invalid_scope:{scope}")
    if resolution not in ALLOWED_RESOLUTIONS:
        raise ValueError(f"invalid_resolution:{resolution}")
    normalized_amc = _normalize_amc_key(amc)
    payload = {
        "amc_code": normalized_amc,
        "report_month": report_month,
        "scope": scope,
        "subject_key": subject_key,
        "subject_label": subject_label,
        "resolution": resolution,
        "decided_value": decided_value,
        "source_document_id": source_document_id,
        "reviewed_by": reviewed_by,
        "note": note,
    }
    result = (
        supabase.table(DECISIONS_TABLE)
        .upsert(payload, on_conflict="amc_code,report_month,scope,subject_key")
        .execute()
    )
    return (result.data or [{}])[0]


def find_risk_conflicts(
    *, amc: str, report_month: str, min_confidence: float = 90.0
) -> list[dict[str, Any]]:
    """Fund families where the freshly staged risk_level disagrees with the currently
    live value for a same-AMC sibling scheme. Mirrors the same check the real
    promotion job runs before it will promote the `risk` scope
    (build_family_invariant_propagation_plan below) -- these rows are exactly what
    that job would list under `family_existing_conflicts` and refuse to promote."""
    normalized_amc = _normalize_amc_key(amc)
    all_candidates = _get_filtered(
        "mf_factsheet_candidates",
        "id,source_document_id,amc_code,report_month,raw_scheme_name,normalized_scheme_name,"
        "mapped_family_id,mapped_scheme_code,mapping_status,mapping_confidence,promotion_status,risk_level",
        filters={"report_month": report_month},
    )
    staged = [
        row
        for row in all_candidates
        if _normalize_amc_key(row.get("amc_code")) == normalized_amc
        and row.get("mapping_status") == "mapped"
        and row.get("mapped_family_id")
        and row.get("mapped_scheme_code")
        and float(row.get("mapping_confidence") or 0.0) >= min_confidence
        and row.get("promotion_status") != "rejected"
        and row.get("risk_level") not in (None, "")
    ]
    if not staged:
        return []

    family_ids = sorted({str(row["mapped_family_id"]) for row in staged})
    mapping_rows: list[dict[str, Any]] = []
    for start in range(0, len(family_ids), 200):
        mapping_rows.extend(
            supabase.table("mutual_fund_family_mapping")
            .select("scheme_code,family_id")
            .in_("family_id", family_ids[start : start + 200])
            .execute()
            .data
            or []
        )
    siblings_by_family: dict[str, set[str]] = defaultdict(set)
    for row in mapping_rows:
        if row.get("family_id") and row.get("scheme_code"):
            siblings_by_family[str(row["family_id"])].add(str(row["scheme_code"]))

    all_sibling_codes = sorted({code for codes in siblings_by_family.values() for code in codes})
    snapshot_by_code: dict[str, dict[str, Any]] = {}
    for start in range(0, len(all_sibling_codes), 500):
        for row in (
            supabase.table("mutual_fund_core_snapshot")
            .select("scheme_code,scheme_name,amc_name,risk_level")
            .in_("scheme_code", all_sibling_codes[start : start + 500])
            .execute()
            .data
            or []
        ):
            snapshot_by_code[str(row["scheme_code"])] = row

    documents = _fetch_source_documents({row.get("source_document_id") for row in staged})
    decisions = get_decisions(amc=normalized_amc, report_month=report_month, scope="risk")

    conflicts: list[dict[str, Any]] = []
    for row in staged:
        family_id = str(row["mapped_family_id"])
        staged_risk = " ".join(str(row["risk_level"]).lower().split())
        source_label = supported_amc_label_from_text(row.get("amc_code"))
        mismatched = []
        for scheme_code in sorted(siblings_by_family.get(family_id, set())):
            live = snapshot_by_code.get(scheme_code)
            if not live or live.get("risk_level") in (None, ""):
                continue
            if source_label and supported_amc_label_from_text(live.get("amc_name")) != source_label:
                continue
            live_risk = " ".join(str(live["risk_level"]).lower().split())
            if live_risk != staged_risk:
                mismatched.append(
                    {
                        "scheme_code": scheme_code,
                        "scheme_name": live.get("scheme_name"),
                        "live_risk_level": live["risk_level"],
                    }
                )
        if mismatched:
            document = documents.get(str(row.get("source_document_id")))
            conflicts.append(
                {
                    "family_id": family_id,
                    "staged_scheme_code": row["mapped_scheme_code"],
                    "raw_scheme_name": row.get("raw_scheme_name"),
                    "staged_risk_level": row["risk_level"],
                    "mismatched_live_schemes": mismatched,
                    "source_document_id": row.get("source_document_id"),
                    "source_url": document.get("source_url") if document else None,
                    "checksum": document.get("checksum") if document else None,
                    "decision": decisions.get(family_id),
                }
            )
    return sorted(conflicts, key=lambda item: item["family_id"])


def find_holdings_out_of_band(
    *, amc: str, report_month: str, lower: float | None = None, upper: float | None = None
) -> list[dict[str, Any]]:
    """Staged schemes whose total percent-of-AUM across their holding rows falls
    outside the accepted band (app/mf_ingestion/validators/metrics_validator.py +
    constants.py:ReportMonthWindow, currently 90-110%), or that otherwise failed row
    validation. Mirrors what the real promotion dry-run's `rejected_holding_examples` /
    `staged_holdings_below_family_coverage_threshold` checks would flag for the
    `holdings`/`sectors` scope."""
    window = ReportMonthWindow()
    lower = window.lower_bound_pct if lower is None else lower
    upper = window.upper_bound_pct if upper is None else upper
    normalized_amc = _normalize_amc_key(amc)

    all_documents = _get_filtered(
        "mf_raw_documents",
        "id,amc_code,document_type,report_month,source_url,storage_bucket,storage_key,checksum",
        filters={"report_month": report_month},
    )
    documents_by_id = {
        str(row["id"]): row
        for row in all_documents
        if _normalize_amc_key(row.get("amc_code")) == normalized_amc
    }
    document_ids = list(documents_by_id)
    if not document_ids:
        return []

    # One source_document_id per query (.eq, not .in_) -- matches the pattern
    # promote_mf_disclosures.py's _fetch_all_rows already uses for this table. An IN
    # filter across documents times out (Supabase 57014); this table has no usable
    # index for that shape of query, same root cause the runbook's "bounded AMC
    # source-document reads" fix addressed for the holdings coverage RPC.
    holdings: list[dict[str, Any]] = []
    for document_id in document_ids:
        holdings.extend(
            _get_filtered(
                "mf_scheme_holdings",
                "id,source_document_id,raw_scheme_name,mapped_scheme_code,mapped_family_id,"
                "mapping_status,mapping_confidence,validation_status,instrument_name,isin,percent_aum",
                filters={"source_document_id": document_id},
            )
        )
    if not holdings:
        return []

    by_scheme_document: dict[tuple, list[dict[str, Any]]] = defaultdict(list)
    for row in holdings:
        key = row.get("mapped_scheme_code") or row.get("raw_scheme_name")
        by_scheme_document[(key, row.get("source_document_id"))].append(row)

    per_document: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for (scheme_key, source_document_id), rows in by_scheme_document.items():
        total = 0.0
        has_value = False
        for row in rows:
            if row.get("percent_aum") is not None:
                try:
                    total += float(row["percent_aum"])
                    has_value = True
                except (TypeError, ValueError):
                    pass
        validation_statuses = {row.get("validation_status") for row in rows if row.get("validation_status")}
        out_of_band = has_value and not (lower <= total <= upper)
        if not (out_of_band or (validation_statuses - {"valid"})):
            continue
        document = documents_by_id.get(str(source_document_id))
        missing_isin = sum(1 for row in rows if not str(row.get("isin") or "").strip())
        per_document[scheme_key].append(
            {
                "mapped_family_id": rows[0].get("mapped_family_id"),
                "raw_scheme_name": rows[0].get("raw_scheme_name"),
                "total_percent_aum": round(total, 2) if has_value else None,
                "validation_statuses": sorted(validation_statuses),
                "holding_row_ids": [row.get("id") for row in rows],
                "holding_row_count": len(rows),
                "holding_rows_missing_isin": missing_isin,
                "source_document_id": source_document_id,
                "document_type": document.get("document_type") if document else None,
                "source_url": document.get("source_url") if document else None,
                "checksum": document.get("checksum") if document else None,
            }
        )

    decisions = get_decisions(amc=normalized_amc, report_month=report_month, scope="holdings")

    # Kotak (and other AMCs whose combined factsheet embeds the same holdings the
    # dedicated portfolio_disclosure file also carries) can stage the identical
    # scheme 2-3x across separate mf_raw_documents rows. Collapse to one row per
    # scheme, preferring portfolio_disclosure as the more authoritative source, and
    # note how many other documents independently show the same numbers.
    flagged: list[dict[str, Any]] = []
    for scheme_key, entries in per_document.items():
        entries_sorted = sorted(
            entries, key=lambda e: 0 if e["document_type"] == "portfolio_disclosure" else 1
        )
        primary = entries_sorted[0]
        others = entries_sorted[1:]
        flagged.append(
            {
                "scheme_key": scheme_key,
                "expected_band": [lower, upper],
                "also_staged_in_n_other_documents": len(others),
                "other_source_document_ids": [e["source_document_id"] for e in others],
                "decision": decisions.get(str(scheme_key)),
                **primary,
            }
        )
    return sorted(flagged, key=lambda item: item.get("scheme_key") or "")


def promote_risk_decision(*, decision_id: str, requested_by: str) -> dict[str, Any]:
    """Apply a recorded `use_staged` risk decision by re-checking the conflict is
    still exactly what was reviewed, then writing the staged risk_level onto the
    specific live sibling scheme codes the decision covers. Reuses
    build_family_invariant_propagation_plan / apply_family_invariant_propagation --
    the same functions the real promotion job uses for this exact propagation -- so
    this never bypasses a gate the manual workflow doesn't also apply."""
    decision_rows = supabase.table(DECISIONS_TABLE).select("*").eq("id", decision_id).limit(1).execute().data or []
    if not decision_rows:
        return {"status": "error", "reason": "decision_not_found"}
    decision = decision_rows[0]
    if decision.get("scope") != "risk":
        return {"status": "error", "reason": "decision_scope_mismatch"}
    if decision.get("resolution") == "use_live":
        supabase.table(DECISIONS_TABLE).update(
            {"promoted_at": _now_iso(), "promoted_by": requested_by, "promotion_result": {"status": "no_write_kept_live"}}
        ).eq("id", decision_id).execute()
        return {"status": "ok", "reason": "kept_live_value_no_write"}
    if decision.get("resolution") == "exclude":
        supabase.table(DECISIONS_TABLE).update(
            {"promoted_at": _now_iso(), "promoted_by": requested_by, "promotion_result": {"status": "excluded_no_write"}}
        ).eq("id", decision_id).execute()
        return {"status": "ok", "reason": "excluded_no_write"}

    family_id = str(decision["subject_key"])
    all_candidates = (
        supabase.table("mf_factsheet_candidates")
        .select("*")
        .eq("mapped_family_id", family_id)
        .eq("report_month", decision["report_month"])
        .execute()
        .data
        or []
    )
    candidates = [
        row for row in all_candidates if _normalize_amc_key(row.get("amc_code")) == decision["amc_code"]
    ]
    candidate = next((row for row in candidates if row.get("risk_level")), None)
    if not candidate:
        return {"status": "error", "reason": "staged_candidate_no_longer_present"}

    staged_risk_now = " ".join(str(candidate["risk_level"]).lower().split())
    decided_risk = " ".join(str((decision.get("decided_value") or {}).get("risk_level") or "").lower().split())
    if decided_risk and staged_risk_now != decided_risk:
        return {"status": "error", "reason": "staged_value_changed_since_review", "reviewed": decided_risk, "current": staged_risk_now}

    expected_month = _parse_report_month(str(decision["report_month"]))
    plan = build_family_invariant_propagation_plan(candidate, ["risk"], expected_month, requested_by=requested_by)

    # Any conflicting sibling not covered by this reviewed decision keeps this blocked --
    # a decision only approves the exact schemes it listed at review time.
    approved_codes = {item["scheme_code"] for item in (decision.get("decided_value") or {}).get("mismatched_live_schemes", [])}
    field_conflicts = (plan.get("conflicts") or {}).get("risk_level") or []
    unapproved = [entry for entry in field_conflicts if entry.get("scheme_code") not in approved_codes]
    if unapproved:
        return {"status": "error", "reason": "unreviewed_conflicts_remain", "unapproved": unapproved}

    result = apply_family_invariant_propagation(
        {
            **plan,
            "status": "ready",
            "fields": sorted({*(plan.get("fields") or []), "risk_level"}),
            "updates": plan.get("updates") or [
                {"scheme_code": code, "risk_level": candidate["risk_level"]} for code in approved_codes
            ],
            "conflicts": {},
        }
    )
    supabase.table(DECISIONS_TABLE).update(
        {"promoted_at": _now_iso(), "promoted_by": requested_by, "promotion_result": result}
    ).eq("id", decision_id).execute()
    return {"status": "ok", "result": result}


def promote_holdings_decision(*, decision_id: str, requested_by: str) -> dict[str, Any]:
    """Apply a recorded holdings decision. For `use_staged`, mark the specific
    reviewed rows validation_status='valid' (the exact status the promotion RPC
    filters on -- see 20260728_add_mf_thresholded_portfolio_promotion_v2.sql), then
    re-run the real build_dry_run / apply_promotable_report path for holdings+sectors
    scoped to that source document. This never bypasses the RPC's own gates -- it
    only removes the specific validation_status block the human just reviewed and
    lets the existing promotion pipeline re-evaluate everything else normally."""
    decision_rows = supabase.table(DECISIONS_TABLE).select("*").eq("id", decision_id).limit(1).execute().data or []
    if not decision_rows:
        return {"status": "error", "reason": "decision_not_found"}
    decision = decision_rows[0]
    if decision.get("scope") != "holdings":
        return {"status": "error", "reason": "decision_scope_mismatch"}
    if decision.get("resolution") in ("use_live", "exclude"):
        supabase.table(DECISIONS_TABLE).update(
            {"promoted_at": _now_iso(), "promoted_by": requested_by, "promotion_result": {"status": "excluded_no_write"}}
        ).eq("id", decision_id).execute()
        return {"status": "ok", "reason": "excluded_no_write"}

    decided_value = decision.get("decided_value") or {}
    row_ids = decided_value.get("holding_row_ids") or []
    source_document_id = decision.get("source_document_id")
    if not row_ids or not source_document_id:
        return {"status": "error", "reason": "decision_missing_row_reference"}

    current_rows = (
        supabase.table("mf_scheme_holdings")
        .select("id,percent_aum,validation_status")
        .in_("id", row_ids)
        .execute()
        .data
        or []
    )
    if len(current_rows) != len(row_ids):
        return {"status": "error", "reason": "staged_rows_changed_since_review"}

    supabase.table("mf_scheme_holdings").update({"validation_status": "valid"}).in_("id", row_ids).execute()

    # holdings and sectors promote independently (runbook rule); scoping to just
    # holdings here avoids an unrelated sectors gap blocking this specific fix.
    expected_month = _parse_report_month(str(decision["report_month"]))
    report = build_dry_run(str(source_document_id), ["holdings"], expected_month, requested_by=requested_by)
    if report.get("status") != "promotable":
        return {"status": "error", "reason": "dry_run_rejected_after_review", "report": report}

    applied = apply_promotable_report(report, ["holdings"], expected_month, requested_by=requested_by)
    supabase.table(DECISIONS_TABLE).update(
        {"promoted_at": _now_iso(), "promoted_by": requested_by, "promotion_result": {"status": "applied", "operations": applied}}
    ).eq("id", decision_id).execute()
    return {"status": "ok", "operations": applied}
