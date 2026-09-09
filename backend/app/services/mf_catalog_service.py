"""Conservative public-page gate. No factsheet eligibility or provider metrics."""
from datetime import date, timedelta
from math import isfinite
import re

from app.services.mf_metrics_service import normalize_nav_history

METHOD_VERSION = "catalog_nav_v1"
CATEGORIES = ("Flexi Cap", "Large Cap", "Mid Cap", "Small Cap", "Large & Mid Cap", "ELSS", "Index Fund", "Sectoral/Thematic")


def slug(value):
    return re.sub(r"[^a-z0-9]+", "-", value.lower().replace("&", "and")).strip("-")


def identity_reasons(row):
    name = str(row.get("scheme_name") or "").lower()
    plan = str(row.get("plan_type") or "").lower()
    option = str(row.get("option_type") or "").lower()
    reasons = []
    if not name or not str(row.get("scheme_code") or "").isdigit():
        reasons.append("identity_missing")
    if not row.get("amc_name") or row["amc_name"].strip().lower() == "unknown":
        reasons.append("amc_unknown")
    if re.search(r"\b(regular|idcw|dividend|segregated|bonus)\b", " ".join((name, plan, option))):
        reasons.append("share_class_excluded")
    if not re.search(r"\bdirect\b", name + " " + plan) or not re.search(r"\bgrowth\b", name + " " + option):
        reasons.append("share_class_unresolved")
    return reasons


def category(value):
    normalized = re.sub(r"^(equity scheme|equity)\s*[-:]\s*", "", str(value or "").lower()).strip()
    for label in CATEGORIES:
        if normalized in {label.lower(), label.lower() + " fund"}:
            return label
    return None


def assess_history(rows, *, today=None):
    today = today or date.today()
    reasons, by_date = [], {}
    for row in rows:
        points = normalize_nav_history([row])
        if not points or not isfinite(points[0].nav):
            reasons.append("invalid_nav")
            continue
        point = points[0]
        if point.nav_date > today:
            reasons.append("future_nav")
        if point.nav_date in by_date and by_date[point.nav_date] != point.nav:
            reasons.append("conflicting_nav")
        by_date[point.nav_date] = point.nav
    points = sorted(by_date.items())
    result = {"method_version": METHOD_VERSION, "nav": None, "nav_date": None,
              "history_start": None, "observation_count": len(points),
              "cagr_1y": None, "cagr_3y": None, "cagr_5y": None}
    if not points:
        return {**result, "gate_reasons": sorted(set(reasons + ["history_missing"]))}
    end, nav = points[-1]
    result.update(nav=nav, nav_date=end.isoformat(), history_start=points[0][0].isoformat())
    if (today - end).days > 7:
        reasons.append("nav_stale")
    for years in (1, 3, 5):
        cutoff = end - timedelta(days=365 * years)
        anchors = [p for p in points if p[0] <= cutoff]
        window = ([anchors[-1]] if anchors else []) + [p for p in points if p[0] > cutoff]
        covered = bool(anchors) and (cutoff - anchors[-1][0]).days <= 7
        covered = covered and len(window) >= 250 * years
        covered = covered and all((b[0] - a[0]).days <= 7 for a, b in zip(window, window[1:]))
        if covered and not any(r in reasons for r in ("invalid_nav", "future_nav", "conflicting_nav")):
            elapsed = (end - window[0][0]).days / 365
            result[f"cagr_{years}y"] = ((nav / window[0][1]) ** (1 / elapsed) - 1) * 100
        elif years == 1:
            reasons.append("history_1y_incomplete")
    return {**result, "gate_reasons": sorted(set(reasons))}


def catalog_row(snapshot, history, existing=None, reservation=None, *, today=None, amc_slug=None):
    metrics = assess_history(history, today=today)
    label = category(snapshot.get("category"))
    reasons = identity_reasons(snapshot) + metrics.pop("gate_reasons")
    if not label:
        reasons.append("category_unresolved")
    code = str(snapshot["scheme_code"])
    # Existing and legacy URLs are permanent reservations, never eligibility overrides.
    frozen = existing or reservation or {}
    amc = frozen.get("amc_slug") or amc_slug or slug(str(snapshot.get("amc_name") or "unknown"))
    fund = frozen.get("fund_slug") or f"{slug(snapshot.get('scheme_name') or code)}-{code}"
    row = {"scheme_code": code, "amc_slug": amc, "fund_slug": fund,
           "scheme_name": snapshot.get("scheme_name") or code,
           "amc_name": snapshot.get("amc_name") or "Unknown", "category": label,
           "is_published": not reasons, "gate_reasons": sorted(set(reasons)),
           "metrics": metrics}
    return row
