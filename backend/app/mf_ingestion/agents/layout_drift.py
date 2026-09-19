"""Layout-drift detection for official AMC factsheet documents.

Official AMC factsheets change shape without notice: label text is reworded,
sections are added or dropped, and a field can silently stop extracting. The
2026-08 vs 2026-07 PPFAS digital factsheets are a concrete example -- the
Risk-o-Meter table exists in August but is absent entirely in July, so
`risk_level` yield drops from 6/7 to 0/7.

The parser does not fail loudly in that situation: it returns a record with the
field left as None, the candidate is staged with a gap, and only the downstream
coverage gate notices. This module makes the drop observable at the point the
document is parsed, so discovery can record a drift signal and route the
document to review instead of silently degrading.

Design constraints:

* Pure and deterministic -- no network, no database, no clock. Callers pass in
  parsed records and a previously observed baseline.
* Conservative -- a field that was already absent in the baseline is not
  treated as drift. Pre-existing gaps (for example `aum` in the PDF path) must
  not raise an alert on every run.
* Never auto-repairs. It reports what changed so a human can decide.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

# Fields the factsheet pipeline is expected to surface per scheme.
FACTSHEET_CORE_FIELDS: tuple[str, ...] = (
    "aum",
    "expense_ratio",
    "benchmark",
    "fund_manager",
    "risk_level",
)

# A baseline field at or above this yield ratio is considered "established":
# drift alerts are only raised for fields the previous layout supplied reliably.
BASELINE_ESTABLISHED_RATIO = 0.5

# A current field below this yield ratio is considered "lost".
CURRENT_LOST_RATIO = 0.5

# Minimum records before a yield ratio is meaningful.
MIN_RECORDS_FOR_SIGNAL = 2

DRIFT_REASON_FIELD_LOST = "field_yield_lost"
DRIFT_REASON_RECORD_COUNT_DROP = "record_count_drop"


@dataclass(frozen=True)
class LayoutFingerprint:
    """Per-document observation of what a layout actually produced."""

    document_kind: str
    record_count: int
    field_counts: dict[str, int]
    extra: dict[str, Any] = field(default_factory=dict)

    def ratio(self, name: str) -> float:
        if self.record_count <= 0:
            return 0.0
        return self.field_counts.get(name, 0) / self.record_count

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_kind": self.document_kind,
            "record_count": self.record_count,
            "field_counts": dict(sorted(self.field_counts.items())),
            "field_ratios": {
                name: round(self.ratio(name), 4) for name in sorted(self.field_counts)
            },
            **({"extra": self.extra} if self.extra else {}),
        }


@dataclass(frozen=True)
class LayoutDriftReport:
    """Comparison of a current fingerprint against a baseline."""

    drifted: bool
    reasons: tuple[str, ...]
    missing_fields: tuple[str, ...]
    lost_fields: tuple[str, ...]
    current: LayoutFingerprint
    baseline: LayoutFingerprint | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "drifted": self.drifted,
            "reasons": list(self.reasons),
            "missing_fields": list(self.missing_fields),
            "lost_fields": list(self.lost_fields),
            "current": self.current.to_dict(),
            "baseline": self.baseline.to_dict() if self.baseline else None,
        }

    def evidence(self) -> dict[str, Any]:
        """Compact form for discovery `evidence` jsonb."""
        return {
            "drifted": self.drifted,
            "reasons": list(self.reasons),
            "lost_fields": list(self.lost_fields),
            "current_field_ratios": self.current.to_dict()["field_ratios"],
            "baseline_field_ratios": (
                self.baseline.to_dict()["field_ratios"] if self.baseline else None
            ),
        }


def _value_present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def build_layout_fingerprint(
    records: Iterable[Any],
    *,
    document_kind: str,
    extra: Mapping[str, Any] | None = None,
) -> LayoutFingerprint:
    """Measure which core fields a parsed document actually produced.

    `records` may be `FactsheetRecord` instances or plain mappings; both are
    supported so the same helper works for the deterministic parser and for any
    extractor output.
    """
    rows = list(records)
    counts = {name: 0 for name in FACTSHEET_CORE_FIELDS}
    for row in rows:
        for name in FACTSHEET_CORE_FIELDS:
            value = row.get(name) if isinstance(row, Mapping) else getattr(row, name, None)
            if _value_present(value):
                counts[name] += 1
    return LayoutFingerprint(
        document_kind=str(document_kind or "unknown").strip().lower(),
        record_count=len(rows),
        field_counts=counts,
        extra=dict(extra or {}),
    )


def detect_layout_drift(
    current: LayoutFingerprint,
    baseline: LayoutFingerprint | None,
    *,
    baseline_established_ratio: float = BASELINE_ESTABLISHED_RATIO,
    current_lost_ratio: float = CURRENT_LOST_RATIO,
    min_records: int = MIN_RECORDS_FOR_SIGNAL,
) -> LayoutDriftReport:
    """Compare a layout observation to the last known-good baseline.

    Drift is reported when a field the baseline supplied reliably has since
    collapsed, or when the document yields materially fewer records. A baseline
    of `None` (first observation) never reports drift.
    """
    if baseline is None:
        return LayoutDriftReport(
            drifted=False,
            reasons=(),
            missing_fields=(),
            lost_fields=(),
            current=current,
            baseline=None,
        )

    # Different document kinds legitimately expose different fields: the digital
    # HTML factsheet carries AUM but renders Risk-o-Meter as an image, while the
    # PDF carries risk_level but no AUM. Comparing across kinds would report
    # drift on every run, so the two are never compared directly.
    if (
        current.document_kind
        and baseline.document_kind
        and current.document_kind != baseline.document_kind
    ):
        return LayoutDriftReport(
            drifted=False,
            reasons=(),
            missing_fields=(),
            lost_fields=(),
            current=current,
            baseline=baseline,
        )

    if current.record_count < min_records or baseline.record_count < min_records:
        # Not enough signal to judge; avoid noisy alerts on tiny documents.
        return LayoutDriftReport(
            drifted=False,
            reasons=(),
            missing_fields=(),
            lost_fields=(),
            current=current,
            baseline=baseline,
        )

    lost_fields: list[str] = []
    missing_fields: list[str] = []
    for name in FACTSHEET_CORE_FIELDS:
        baseline_ratio = baseline.ratio(name)
        current_ratio = current.ratio(name)
        if baseline_ratio >= baseline_established_ratio and current_ratio < current_lost_ratio:
            lost_fields.append(name)
        if current_ratio <= 0.0:
            missing_fields.append(name)

    reasons: list[str] = []
    if lost_fields:
        reasons.append(DRIFT_REASON_FIELD_LOST)

    record_drop = current.record_count < baseline.record_count
    if record_drop:
        reasons.append(DRIFT_REASON_RECORD_COUNT_DROP)

    return LayoutDriftReport(
        drifted=bool(reasons),
        reasons=tuple(reasons),
        missing_fields=tuple(missing_fields),
        lost_fields=tuple(lost_fields),
        current=current,
        baseline=baseline,
    )
