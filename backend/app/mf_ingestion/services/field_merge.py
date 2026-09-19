"""Field-level merge for factsheet sources covering the same scheme and month.

A scheme's factsheet data can arrive in more than one document: a PDF factsheet
and a digital (HTML) factsheet. They are complementary rather than equivalent:

* The PDF carries `risk_level` for PPFAS (the Risk-o-Meter is rendered as text),
  but no `aum`.
* The digital factsheet carries `aum`, `expense_ratio`, `benchmark` and
  `fund_manager`, but only exposes `risk_level` in months whose layout includes
  the Risk-o-Meter table.

The coverage gate (`report_mf_staging_coverage`) selects a single latest
factsheet document per AMC/month, so the two documents must not compete: their
fields are merged onto one candidate set. This module performs that merge as a
pure function so the precedence is explicit, testable, and auditable.

Precedence is per field, not per document. The first source in priority order
that supplies a non-empty value wins, and the winning source is recorded so the
provenance of every merged value is inspectable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping

# Fields merged across sources. Mirrors FACTSHEET_CORE_FIELDS.
MERGEABLE_FIELDS: tuple[str, ...] = (
    "aum",
    "expense_ratio",
    "benchmark",
    "fund_manager",
    "risk_level",
)

# Source kinds that may contribute to a merge, most preferred first.
SOURCE_KIND_PDF = "pdf"
SOURCE_KIND_DIGITAL = "digital"

# Default per-field source precedence.
#
# `aum`, `expense_ratio`, `benchmark` and `fund_manager` come from the digital
# sheet: it states AUM explicitly and its benchmark/expense values are the
# structured ones (the PDF path has produced table headers such as "Returns %"
# and "Investor Exit upon" as benchmark values).
#
# `risk_level` prefers the PDF: the digital sheet renders Risk-o-Meter as an
# image, and months without the surrounding table expose no risk text at all,
# whereas the PDF carries it as text.
DEFAULT_FIELD_PRECEDENCE: dict[str, tuple[str, ...]] = {
    "aum": (SOURCE_KIND_DIGITAL, SOURCE_KIND_PDF),
    "expense_ratio": (SOURCE_KIND_DIGITAL, SOURCE_KIND_PDF),
    "benchmark": (SOURCE_KIND_DIGITAL, SOURCE_KIND_PDF),
    "fund_manager": (SOURCE_KIND_DIGITAL, SOURCE_KIND_PDF),
    "risk_level": (SOURCE_KIND_PDF, SOURCE_KIND_DIGITAL),
}


def _present(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


@dataclass(frozen=True)
class SourceFields:
    """One document's view of a single scheme's fields."""

    source_kind: str
    values: dict[str, Any]
    source_document_id: str | None = None


@dataclass(frozen=True)
class MergedFields:
    """Merged per-field values plus their provenance."""

    values: dict[str, Any]
    field_sources: dict[str, str]
    contributing_source_kinds: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "values": dict(self.values),
            "field_sources": dict(self.field_sources),
            "contributing_source_kinds": list(self.contributing_source_kinds),
        }


def merge_scheme_fields(
    sources: Iterable[SourceFields],
    *,
    precedence: Mapping[str, tuple[str, ...]] | None = None,
) -> MergedFields:
    """Merge field values across sources using per-field precedence.

    Sources with an unrecognized kind are ignored for fields whose precedence
    does not mention them, so an unexpected document cannot silently override a
    trusted value.
    """
    rules = dict(precedence or DEFAULT_FIELD_PRECEDENCE)
    ordered = list(sources)
    by_kind: dict[str, list[SourceFields]] = {}
    for source in ordered:
        by_kind.setdefault(str(source.source_kind or "").strip().lower(), []).append(source)

    values: dict[str, Any] = {}
    field_sources: dict[str, str] = {}
    contributing: list[str] = []

    for name in MERGEABLE_FIELDS:
        for kind in rules.get(name, ()):
            winner: SourceFields | None = None
            for candidate in by_kind.get(kind, []):
                if _present(candidate.values.get(name)):
                    winner = candidate
                    break
            if winner is not None:
                values[name] = winner.values[name]
                field_sources[name] = kind
                if kind not in contributing:
                    contributing.append(kind)
                break

    return MergedFields(
        values=values,
        field_sources=field_sources,
        contributing_source_kinds=tuple(contributing),
    )
