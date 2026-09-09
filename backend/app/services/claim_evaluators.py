"""Deterministic, read-only evaluators for Fund Truth Check Phase 1."""
from __future__ import annotations

import calendar
from datetime import date, datetime, timezone
from hashlib import sha256
import re
from typing import Any, Callable
from urllib.parse import urlparse

from app.services.asset_resolver import AssetResolution
from app.services.claim_check_contract import AtomicClaim, ClaimEvidence, ClaimFreshness, ClaimMetric, ClaimOperator, ClaimStatus, ClaimVerdict
from app.services.claim_parser import ParsedClaim
from app.services.mf_metrics_service import compute_nav_metrics, normalize_nav_history
from app.services.mf_nav_freshness import assess_nav_freshness
from app.services.mfapi_service import get_stored_nav_history


AMFI_NAV_URL = "https://www.amfiindia.com/spages/NAVAll.txt"
_STATIC_FIELDS = {
    ClaimMetric.EXPENSE_RATIO: "expense_ratio", ClaimMetric.AUM: "aum", ClaimMetric.BENCHMARK: "benchmark",
    ClaimMetric.RISKOMETER: "risk_level", ClaimMetric.FUND_MANAGER: "fund_manager", ClaimMetric.INVESTMENT_OBJECTIVE: "investment_objective",
}
_NAV_METRICS = {
    ClaimMetric.CAGR: "return_3y", ClaimMetric.ROLLING_RETURN: "return_3y", ClaimMetric.SHARPE_RATIO: "sharpe_ratio",
    ClaimMetric.MAX_DRAWDOWN: "max_drawdown_1y", ClaimMetric.VOLATILITY: "volatility_1y",
}
_RISKOMETER_ORDER = {
    "very low": 1,
    "low": 2,
    "moderately low": 3,
    "moderate": 4,
    "moderately high": 5,
    "high": 6,
    "very high": 7,
}
_TRACE_FIELD = {
    "holding": "holdings",
    "holdings_concentration": "holdings",
    "portfolio_overlap": "holdings",
    "sector_exposure": "sector_allocation",
}


def _as_date(value: Any) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raw = str(value or "").strip()
    try:
        return date.fromisoformat(raw[:10]) if raw else None
    except ValueError:
        month = re.fullmatch(r"(\d{4})-(\d{2})", raw)
        if not month:
            return None
        year, number = (int(item) for item in month.groups())
        return date(year, number, calendar.monthrange(year, number)[1])


def _number(value: Any) -> float | None:
    try:
        return float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _fingerprint(*parts: Any) -> str:
    return sha256("|".join(str(part or "").strip() for part in parts).encode("utf-8")).hexdigest()


def _nested_values(payload: Any, keys: tuple[str, ...]) -> list[Any]:
    if not isinstance(payload, dict):
        return []
    result = [payload[key] for key in keys if payload.get(key) not in (None, "")]
    for child in payload.values():
        if isinstance(child, dict):
            result.extend(_nested_values(child, keys))
    return result


class OfficialEvidenceAdapter:
    """Use only dated HTTPS provenance already attached to normalized records."""

    @staticmethod
    def field_trace(row: dict[str, Any], field: str) -> dict[str, Any] | None:
        payload = row.get("provider_payload") if isinstance(row.get("provider_payload"), dict) else {}
        traces = payload.get("amc_trace") if isinstance(payload.get("amc_trace"), dict) else {}
        trace = traces.get(_TRACE_FIELD.get(field, field))
        return trace if isinstance(trace, dict) else None

    def from_row(self, row: dict[str, Any], *, field: str) -> ClaimEvidence | None:
        payload = row.get("provider_payload") if isinstance(row.get("provider_payload"), dict) else {}
        trace = self.field_trace(row, field)
        source_payload = trace or payload
        urls = [str(item) for item in _nested_values(source_payload, ("source_url", "url", "document_url"))]
        if not trace:
            urls.extend(str(row[key]) for key in ("source_url", "document_url") if row.get(key))
        source_url = next((item for item in urls if item.startswith("https://")), None)
        dates = _nested_values(source_payload, ("as_of_date", "report_month", "source_as_of_date", "document_date"))
        if not trace:
            dates.extend(row[key] for key in ("as_of_date", "report_month", "source_as_of_date") if row.get(key))
        as_of = next((item for item in (_as_date(value) for value in dates) if item), None)
        markers = [row.get("source"), *_nested_values(source_payload, ("source", "source_type", "document_type", "provenance"))]
        if trace:
            markers.append("official amc trace")
        marker = " ".join(str(item).lower() for item in markers)
        if not source_url or not as_of or not urlparse(source_url).hostname or not any(token in marker for token in ("official", "amc", "factsheet", "disclosure")):
            return None
        document_ids = _nested_values(source_payload, ("source_document_id", "document_id"))
        fingerprints = _nested_values(source_payload, ("source_fingerprint", "fingerprint", "sha256"))
        return ClaimEvidence(
            source_type="official_amc_document", source_name="Official AMC factsheet or disclosure", source_url=source_url,
            document_id=str(document_ids[0]) if document_ids else None, as_of_date=as_of.isoformat(),
            source_fingerprint=str(fingerprints[0]) if fingerprints else _fingerprint(field, source_url, document_ids[:1], as_of, source_payload.get("value")),
        )

    def from_amfi_nav(self, scheme_code: str, rows: list[dict[str, Any]]) -> ClaimEvidence | None:
        points = normalize_nav_history(rows)
        if not points:
            return None
        point = points[-1]
        return ClaimEvidence(
            source_type="amfi_nav", source_name="AMFI NAV", source_url=AMFI_NAV_URL, as_of_date=point.nav_date.isoformat(),
            source_fingerprint=_fingerprint("amfi_nav", scheme_code, point.nav_date, point.nav),
        )


class ClaimEvaluators:
    def __init__(self, repository: Any, *, nav_history_loader: Callable[[str], list[dict[str, Any]] | None] | None = None, today: Callable[[], date] | None = None, evidence_adapter: OfficialEvidenceAdapter | None = None):
        self.repository = repository
        self.nav_history_loader = nav_history_loader or self._stored_nav_history
        self.today = today or date.today
        self.evidence = evidence_adapter or OfficialEvidenceAdapter()

    @staticmethod
    def _stored_nav_history(scheme_code: str) -> list[dict[str, Any]]:
        result = get_stored_nav_history(scheme_code)
        return list(result.get("data") or []) if result.get("ok") else []

    def evaluate(self, parsed: ParsedClaim, resolutions: list[AssetResolution]) -> AtomicClaim:
        if parsed.unsupported_reason:
            return AtomicClaim(statement=parsed.statement, status=ClaimStatus.UNSUPPORTED, limitations=[parsed.unsupported_reason])
        if parsed.metric is None:
            if parsed.entity_inputs:
                return AtomicClaim(statement=parsed.statement, status=ClaimStatus.ENTITY_RESOLUTION_REQUIRED, limitations=["Resolve the referenced scheme before selecting a supported objective metric."])
            return AtomicClaim(statement=parsed.statement, status=ClaimStatus.UNSUPPORTED, limitations=["No supported objective metric was selected."])
        if not resolutions or any(not item.is_high_confidence or not item.id for item in resolutions):
            return AtomicClaim(statement=parsed.statement, metric=parsed.metric, operator=parsed.operator, status=ClaimStatus.ENTITY_RESOLUTION_REQUIRED, limitations=["Resolve every referenced scheme with high confidence before evaluating the claim."])
        if parsed.metric in _STATIC_FIELDS:
            return self._static(parsed, resolutions)
        if parsed.metric in _NAV_METRICS:
            return self._nav(parsed, resolutions)
        if parsed.metric in {ClaimMetric.HOLDS_STOCK, ClaimMetric.STOCK_EXPOSURE}:
            return self._holdings(parsed, resolutions)
        if parsed.metric is ClaimMetric.SECTOR_EXPOSURE:
            return self._sector(parsed, resolutions)
        if parsed.metric is ClaimMetric.HOLDINGS_CONCENTRATION:
            return self._concentration(parsed, resolutions)
        if parsed.metric is ClaimMetric.PORTFOLIO_OVERLAP:
            return self._overlap(parsed, resolutions)
        return self._unverifiable(parsed, "No deterministic evaluator is configured for this metric.")

    def _row(self, resolution: AssetResolution) -> dict[str, Any] | None:
        try:
            return self.repository.get_fund_by_scheme_code(resolution.id)
        except Exception:
            return None

    @staticmethod
    def _label(resolution: AssetResolution) -> str:
        return resolution.resolved_name or resolution.input

    def _freshness(self, evidence: list[ClaimEvidence], *, nav: bool = False) -> ClaimFreshness:
        dates = [item for item in (_as_date(value.as_of_date) for value in evidence) if item]
        if not dates:
            return ClaimFreshness.UNKNOWN
        if nav:
            status = assess_nav_freshness(max(dates), now=datetime.combine(self.today(), datetime.min.time(), tzinfo=timezone.utc))
            missed = status.get("missed_business_days")
            return ClaimFreshness.CURRENT if isinstance(missed, int) and missed <= 3 else ClaimFreshness.STALE
        oldest = min(dates)
        month_age = (self.today().year - oldest.year) * 12 + self.today().month - oldest.month
        return ClaimFreshness.CURRENT if month_age <= 2 else ClaimFreshness.STALE

    @staticmethod
    def _same_period(evidence: list[ClaimEvidence], *, nav: bool) -> bool:
        dates = [_as_date(item.as_of_date) for item in evidence]
        if not dates or any(item is None for item in dates):
            return False
        if nav:
            return len(set(dates)) == 1
        return len({(item.year, item.month) for item in dates if item}) == 1

    @staticmethod
    def _comparison_verdict(left: Any, right: Any, operator: ClaimOperator | None) -> ClaimVerdict | None:
        if operator is ClaimOperator.EQUAL_TO:
            return ClaimVerdict.SUPPORTED if str(left).strip().casefold() == str(right).strip().casefold() else ClaimVerdict.CONTRADICTED
        if operator is ClaimOperator.DIFFERENT_FROM:
            return ClaimVerdict.SUPPORTED if str(left).strip().casefold() != str(right).strip().casefold() else ClaimVerdict.CONTRADICTED
        left_number, right_number = _number(left), _number(right)
        if left_number is None or right_number is None:
            return None
        if operator is ClaimOperator.LOWER_THAN:
            return ClaimVerdict.SUPPORTED if left_number < right_number else ClaimVerdict.CONTRADICTED
        if operator is ClaimOperator.HIGHER_THAN:
            return ClaimVerdict.SUPPORTED if left_number > right_number else ClaimVerdict.CONTRADICTED
        return None

    @staticmethod
    def _equivalent(field: str, left: Any, right: Any) -> bool:
        left_number, right_number = _number(left), _number(right)
        if left_number is not None and right_number is not None:
            return abs(left_number - right_number) <= 1e-9
        def normalized(value: Any) -> str:
            text = " ".join(re.findall(r"[a-z0-9]+", str(value or "").casefold()))
            if field == "benchmark":
                text = re.sub(r"\bindex\b", "", text)
                text = " ".join(text.split())
            return text
        return normalized(left) == normalized(right)

    def _unverifiable(self, parsed: ParsedClaim, reason: str, *, values: dict[str, Any] | None = None, evidence: list[ClaimEvidence] | None = None, freshness: ClaimFreshness | None = None, nav: bool = False) -> AtomicClaim:
        items = evidence or []
        return AtomicClaim(statement=parsed.statement, metric=parsed.metric, operator=parsed.operator, status=ClaimStatus.EVALUATED, verdict=ClaimVerdict.UNVERIFIABLE, freshness=freshness or self._freshness(items, nav=nav), values=values or {}, evidence=items, limitations=[reason], trackable=False)

    def _definitive(self, parsed: ParsedClaim, verdict: ClaimVerdict, values: dict[str, Any], evidence: list[ClaimEvidence], *, nav: bool = False) -> AtomicClaim:
        freshness = self._freshness(evidence, nav=nav)
        valid = bool(values and evidence) and all(item.source_url and item.source_url.startswith("https://") and item.as_of_date and item.source_fingerprint for item in evidence)
        if not valid:
            return self._unverifiable(parsed, "Dated official evidence is required for a definitive verdict.", values=values, evidence=evidence, freshness=freshness, nav=nav)
        if len(evidence) > 1 and not self._same_period(evidence, nav=nav):
            return self._unverifiable(parsed, "The official evidence uses different reporting periods, so the values are not comparable.", values=values, evidence=evidence, freshness=freshness, nav=nav)
        return AtomicClaim(statement=parsed.statement, metric=parsed.metric, operator=parsed.operator, status=ClaimStatus.EVALUATED, verdict=verdict, freshness=freshness, values=values, evidence=evidence, trackable=True)

    def _static(self, parsed: ParsedClaim, resolutions: list[AssetResolution]) -> AtomicClaim:
        field, values, evidence = _STATIC_FIELDS[parsed.metric], {}, []
        for resolution in resolutions:
            row = self._row(resolution)
            if not row or row.get(field) in (None, ""):
                return self._unverifiable(parsed, f"{field} is unavailable for {self._label(resolution)}.")
            item = self.evidence.from_row(row, field=field)
            if not item:
                return self._unverifiable(parsed, f"{field} lacks dated official AMC provenance for {self._label(resolution)}.")
            trace = self.evidence.field_trace(row, field)
            if trace and trace.get("value") not in (None, "") and not self._equivalent(field, row[field], trace["value"]):
                conflict_values = {
                    self._label(resolution): {
                        "normalized_value": row[field],
                        "cited_source_value": trace["value"],
                        "as_of_date": item.as_of_date,
                    }
                }
                return self._unverifiable(
                    parsed,
                    f"{field} conflicts with its cited official AMC source for {self._label(resolution)}.",
                    values=conflict_values,
                    evidence=[item],
                )
            values[self._label(resolution)] = {"value": row[field], "as_of_date": item.as_of_date}
            evidence.append(item)
        if len(resolutions) == 1 and parsed.operator is ClaimOperator.IS:
            verdict = ClaimVerdict.SUPPORTED
        else:
            if len(resolutions) != 2:
                return self._unverifiable(parsed, "A deterministic comparison requires exactly two schemes.", values=values, evidence=evidence)
            left, right = (item["value"] for item in list(values.values())[:2])
            if parsed.metric is ClaimMetric.RISKOMETER:
                left = _RISKOMETER_ORDER.get(str(left).strip().casefold())
                right = _RISKOMETER_ORDER.get(str(right).strip().casefold())
            elif parsed.metric is ClaimMetric.BENCHMARK:
                left = " ".join(token for token in re.findall(r"[a-z0-9]+", str(left).casefold()) if token != "index")
                right = " ".join(token for token in re.findall(r"[a-z0-9]+", str(right).casefold()) if token != "index")
            verdict = self._comparison_verdict(left, right, parsed.operator)
            if verdict is None:
                return self._unverifiable(parsed, "This metric does not support the requested deterministic comparison.", values=values, evidence=evidence)
        return self._definitive(parsed, verdict, values, evidence)

    def _nav(self, parsed: ParsedClaim, resolutions: list[AssetResolution]) -> AtomicClaim:
        field = _NAV_METRICS[parsed.metric]
        if parsed.metric in {ClaimMetric.CAGR, ClaimMetric.ROLLING_RETURN}:
            field = f"return_{parsed.period_years or 3}y"
        histories = {str(resolution.id): normalize_nav_history(list(self.nav_history_loader(str(resolution.id)) or [])) for resolution in resolutions}
        if any(not points for points in histories.values()):
            return self._unverifiable(parsed, "AMFI NAV history is unavailable for one or more resolved schemes.")
        common_end = min(points[-1].nav_date for points in histories.values())
        aligned = {
            code: [{"nav_date": point.nav_date.isoformat(), "nav": point.nav} for point in points if point.nav_date <= common_end]
            for code, points in histories.items()
        }
        values, evidence = {}, []
        for resolution in resolutions:
            rows = aligned[str(resolution.id)]
            value = compute_nav_metrics(rows, risk_free_rate=0.06).get(field)
            item = self.evidence.from_amfi_nav(str(resolution.id), rows)
            if value is None or not item:
                available_evidence = [*evidence, *([item] if item else [])]
                return self._unverifiable(parsed, f"AMFI NAV history is insufficient to calculate {field} for {self._label(resolution)}.", evidence=available_evidence, nav=True)
            values[self._label(resolution)] = {"value": round(float(value), 6), "as_of_date": item.as_of_date}
            evidence.append(item)
        if len(resolutions) == 1:
            return self._definitive(parsed, ClaimVerdict.SUPPORTED, values, evidence, nav=True)
        left, right = (float(item["value"]) for item in list(values.values())[:2])
        if parsed.operator is ClaimOperator.LOWER_THAN:
            verdict = ClaimVerdict.SUPPORTED if left < right else ClaimVerdict.CONTRADICTED
        elif parsed.operator is ClaimOperator.HIGHER_THAN:
            verdict = ClaimVerdict.SUPPORTED if left > right else ClaimVerdict.CONTRADICTED
        else:
            return self._unverifiable(parsed, "The statement does not define a deterministic comparison operator.", values=values, evidence=evidence, nav=True)
        return self._definitive(parsed, verdict, values, evidence, nav=True)

    def _holdings_rows(self, resolution: AssetResolution) -> list[dict[str, Any]]:
        try:
            rows = list(self.repository.get_latest_holdings(resolution.id) or [])
        except Exception:
            return []
        latest = rows[0].get("as_of_date") if rows else None
        return [row for row in rows if row.get("as_of_date") == latest and row.get("security_name")]

    def _holdings(self, parsed: ParsedClaim, resolutions: list[AssetResolution]) -> AtomicClaim:
        if not parsed.target:
            return self._unverifiable(parsed, "Name the stock whose holding or exposure should be checked.")
        values, evidence = {}, []
        for resolution in resolutions:
            matches = [row for row in self._holdings_rows(resolution) if parsed.target.casefold() in " ".join(str(row.get(key) or "") for key in ("security_name", "isin", "sector")).casefold()]
            if not matches:
                return self._unverifiable(parsed, f"The latest official holdings rows do not confirm {parsed.target} for {self._label(resolution)}.")
            row, item = matches[0], self.evidence.from_row(matches[0], field="holding")
            if not item:
                return self._unverifiable(parsed, f"{parsed.target} lacks dated official holdings provenance for {self._label(resolution)}.")
            values[self._label(resolution)] = {"holding": row.get("security_name"), "weight_pct": _number(row.get("weight_pct")), "as_of_date": item.as_of_date}
            evidence.append(item)
        if len(resolutions) == 1 and parsed.operator in {ClaimOperator.CONTAINS, ClaimOperator.IS}:
            verdict = ClaimVerdict.SUPPORTED
        elif len(resolutions) == 2:
            weights = [item.get("weight_pct") for item in values.values()]
            verdict = self._comparison_verdict(weights[0], weights[1], parsed.operator)
            if verdict is None:
                return self._unverifiable(parsed, "This holding claim does not define a deterministic weight comparison.", values=values, evidence=evidence)
        else:
            return self._unverifiable(parsed, "A holding comparison requires one or two schemes.", values=values, evidence=evidence)
        return self._definitive(parsed, verdict, values, evidence)

    def _sector(self, parsed: ParsedClaim, resolutions: list[AssetResolution]) -> AtomicClaim:
        if not parsed.target:
            return self._unverifiable(parsed, "Name the sector whose exposure should be checked.")
        values, evidence = {}, []
        for resolution in resolutions:
            try:
                matches = [row for row in self.repository.get_sector_rows(resolution.id) or [] if parsed.target.casefold() in str(row.get("sector") or "").casefold()]
            except Exception:
                matches = []
            if not matches:
                return self._unverifiable(parsed, f"Official sector exposure is unavailable for {parsed.target} in {self._label(resolution)}.")
            row, item = matches[0], self.evidence.from_row(matches[0], field="sector_exposure")
            if not item:
                return self._unverifiable(parsed, f"{parsed.target} lacks dated official sector provenance for {self._label(resolution)}.")
            values[self._label(resolution)] = {"sector": row.get("sector"), "weight_pct": _number(row.get("weight_pct")), "as_of_date": item.as_of_date}
            evidence.append(item)
        if len(resolutions) == 1 and parsed.operator in {ClaimOperator.CONTAINS, ClaimOperator.IS}:
            verdict = ClaimVerdict.SUPPORTED
        elif len(resolutions) == 2:
            weights = [item.get("weight_pct") for item in values.values()]
            verdict = self._comparison_verdict(weights[0], weights[1], parsed.operator)
            if verdict is None:
                return self._unverifiable(parsed, "This sector claim does not define a deterministic weight comparison.", values=values, evidence=evidence)
        else:
            return self._unverifiable(parsed, "A sector comparison requires one or two schemes.", values=values, evidence=evidence)
        return self._definitive(parsed, verdict, values, evidence)

    def _concentration(self, parsed: ParsedClaim, resolutions: list[AssetResolution]) -> AtomicClaim:
        values, evidence = {}, []
        for resolution in resolutions:
            rows = self._holdings_rows(resolution)
            item = self.evidence.from_row(rows[0], field="holdings_concentration") if rows else None
            if not item:
                return self._unverifiable(parsed, f"Holdings lack dated official provenance for {self._label(resolution)}.")
            values[self._label(resolution)] = {"top_10_weight_pct": round(sum(_number(row.get("weight_pct")) or 0.0 for row in rows[:10]), 6), "as_of_date": item.as_of_date}
            evidence.append(item)
        if len(resolutions) == 1:
            verdict = ClaimVerdict.SUPPORTED
        elif len(resolutions) == 2:
            totals = [item.get("top_10_weight_pct") for item in values.values()]
            verdict = self._comparison_verdict(totals[0], totals[1], parsed.operator)
            if verdict is None:
                return self._unverifiable(parsed, "This concentration claim does not define a deterministic comparison.", values=values, evidence=evidence)
        else:
            return self._unverifiable(parsed, "A concentration comparison requires one or two schemes.", values=values, evidence=evidence)
        return self._definitive(parsed, verdict, values, evidence)

    def _overlap(self, parsed: ParsedClaim, resolutions: list[AssetResolution]) -> AtomicClaim:
        if len(resolutions) != 2:
            return self._unverifiable(parsed, "Portfolio overlap requires exactly two resolved schemes.")
        groups = [self._holdings_rows(item) for item in resolutions]
        evidence = [self.evidence.from_row(rows[0], field="portfolio_overlap") if rows else None for rows in groups]
        if not all(evidence):
            return self._unverifiable(parsed, "Both holdings disclosures need dated official provenance for overlap.")
        maps = [{str(row.get("isin") or row.get("security_name") or "").strip().casefold(): row for row in rows if str(row.get("isin") or row.get("security_name") or "").strip()} for rows in groups]
        overlap = sum(min(_number(maps[0][key].get("weight_pct")) or 0.0, _number(maps[1][key].get("weight_pct")) or 0.0) for key in set(maps[0]).intersection(maps[1]))
        values = {"entities": [self._label(item) for item in resolutions], "total_overlap_weight_pct": round(overlap, 6), "as_of_dates": [item.as_of_date for item in evidence if item]}
        return self._definitive(parsed, ClaimVerdict.SUPPORTED, values, [item for item in evidence if item])
