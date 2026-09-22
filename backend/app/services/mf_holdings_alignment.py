from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class HoldingsAlignmentResult:
    """Whether an AMFI scheme-wise disclosure payload is internally consistent."""

    is_usable: bool
    issues: list[str] = field(default_factory=list)
    isin_name_conflicts: int = 0
    null_isin_rows: int = 0
    negative_weight_rows: int = 0
    checked_isins: int = 0


# AMFI's scheme-wise disclosure endpoint returns an ISIN column that is not reliably row-aligned
# with Company_Name. In the Apr-Jun 2026 payload, 33 of 53 distinct ISINs were paired with more
# than one company — INE009A01021 (Infosys) was attached to ITC, Coal India, Voltas and others.
# Writing that through produced holdings where a stock's ISIN identified a different company,
# which silently corrupted any downstream ISIN-keyed join (portfolio overlap, family mapping).
#
# The defect is upstream and quarter-specific: Apr-Jun 2026 is misaligned while Jan-Mar 2026,
# Oct-Dec 2025 and earlier quarters are internally consistent. There is no second AMFI endpoint
# to fall back to — AMFI's own disclosure page calls this same route. So the only safe control is
# to refuse a payload whose ISIN/company pairing is self-contradictory.
#
# A correct ISIN always maps to exactly one issuer. So if a single ISIN is paired with two
# genuinely different issuer names, the column cannot be trusted for that payload at all.
#
# Name comparison must tolerate cosmetic variation, because the same issuer is printed with
# different punctuation and suffixes across rows ("RELIANCE INDUSTRIES LTD." vs "RELIANCE
# INDUSTRIES LIMITED"). Treating that as a conflict would reject clean data.
_NAME_NOISE = re.compile(
    r"\b(ltd|limited|pvt|private|co|company|corp|corporation|inc|plc|the|and|&)\b"
)

# AMFI does not use a real NULL for a missing ISIN. Some AMCs send the literal string
# "(blank)" — LIC Mutual Fund's Apr-Jun 2026 payload has 2 such rows. Treating that as a
# genuine ISIN groups unrelated companies under it and reports false corruption, so the
# sentinel must be recognised as absent.
_ISIN_SENTINELS = {"(blank)", "blank", "n/a", "na", "none", "null", "-", "--"}


def _normalise_isin(value: Any) -> str:
    isin = str(value or "").strip()
    return "" if isin.lower() in _ISIN_SENTINELS else isin


def _normalise_issuer(name: str) -> str:
    """Collapse cosmetic differences so only genuinely different issuers compare unequal."""
    lowered = str(name or "").lower().replace("&", " and ")
    collapsed = _NAME_NOISE.sub(" ", lowered)
    return re.sub(r"[^a-z0-9]+", "", collapsed)


def validate_holdings_alignment(rows: list[dict[str, Any]]) -> HoldingsAlignmentResult:
    """Reject an AMFI payload whose ISIN column contradicts its own Company_Name column.

    This is deliberately a payload-level check, not a row-level one. A misaligned payload has
    plausible-looking individual rows; it is only the cross-row relationship that exposes it.
    """
    issues: list[str] = []
    if not rows:
        return HoldingsAlignmentResult(is_usable=False, issues=["holdings_empty"])

    isin_to_names: dict[str, set[str]] = {}
    null_isin_rows = 0
    negative_weight_rows = 0

    for row in rows:
        isin = _normalise_isin(row.get("ISIN"))
        name = _normalise_issuer(row.get("Company_Name"))
        if not isin:
            null_isin_rows += 1
        elif name:
            isin_to_names.setdefault(isin, set()).add(name)

        try:
            if float(row.get("MarketValuePercentage") or 0) < 0:
                negative_weight_rows += 1
        except (TypeError, ValueError):
            issues.append("weight_not_numeric")

    # Only count an ISIN as conflicting when the names differ after normalisation.
    conflicts = sum(1 for names in isin_to_names.values() if len(names) > 1)
    checked = len(isin_to_names)

    if not checked:
        # Without any ISIN the payload cannot support ISIN-keyed joins, but a name-only
        # disclosure is still usable for display, so this is not fatal on its own.
        issues.append("isin_column_absent")

    if conflicts:
        issues.append("isin_company_name_conflict")
        return HoldingsAlignmentResult(
            is_usable=False,
            issues=sorted(set(issues)),
            isin_name_conflicts=conflicts,
            null_isin_rows=null_isin_rows,
            negative_weight_rows=negative_weight_rows,
            checked_isins=checked,
        )

    return HoldingsAlignmentResult(
        is_usable=True,
        issues=sorted(set(issues)),
        isin_name_conflicts=0,
        null_isin_rows=null_isin_rows,
        negative_weight_rows=negative_weight_rows,
        checked_isins=checked,
    )
