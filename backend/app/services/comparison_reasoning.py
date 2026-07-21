from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _confidence_label(score: float) -> str:
    if score >= 0.75:
        return "High"
    if score >= 0.45:
        return "Medium"
    return "Low"


def _winner_object(
    asset_type: str,
    entities: list[str],
    scores: dict[str, float],
    coverage: dict[str, float],
) -> dict[str, Any]:
    valid = [(name, score) for name, score in scores.items() if coverage.get(name, 0.0) > 0]
    if len(valid) < 2:
        entity = valid[0][0] if valid else None
        return {
            "entity_id": entity,
            "entity_name": entity,
            "asset_type": asset_type,
            "status": "insufficient_data",
            "score_delta": 0.0,
        }

    ordered = sorted(valid, key=lambda item: item[1], reverse=True)
    top_name, top_score = ordered[0]
    second_score = ordered[1][1]
    delta = round(top_score - second_score, 4)
    if delta < 0.05:
        return {
            "entity_id": None,
            "entity_name": None,
            "asset_type": asset_type,
            "status": "tie",
            "score_delta": delta,
        }
    return {
        "entity_id": top_name,
        "entity_name": top_name,
        "asset_type": asset_type,
        "status": "winner",
        "score_delta": delta,
    }


def _normalize(values: dict[str, float], higher_is_better: bool) -> dict[str, float]:
    if not values:
        return {}
    minimum = min(values.values())
    maximum = max(values.values())
    if maximum == minimum:
        return {name: 0.5 for name in values}
    if higher_is_better:
        return {name: (value - minimum) / (maximum - minimum) for name, value in values.items()}
    return {name: (maximum - value) / (maximum - minimum) for name, value in values.items()}

def _has_discriminative_signal(values: dict[str, float]) -> bool:
    if len(values) < 2:
        return False
    unique_values = {round(v, 10) for v in values.values()}
    return len(unique_values) > 1


def _factor_scores_stock(comparison: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, float], dict[str, float]]:
    factors: list[dict[str, Any]] = []
    totals: dict[str, float] = {name: 0.0 for name in comparison}
    weights_used: dict[str, float] = {name: 0.0 for name in comparison}
    specs = [
        ("Valuation (P/E)", "fundamentals.pe", 0.2, False),
        ("Quality (ROE)", "fundamentals.roe", 0.2, True),
        ("Growth (Profit 3Y)", "fundamentals.profit_growth_3y", 0.2, True),
        ("Risk (Debt/Equity)", "fundamentals.debt_to_equity", 0.2, False),
        ("Freshness", "source_summary.stale", 0.2, False),
    ]

    for label, path, weight, higher_is_better in specs:
        raw: dict[str, float] = {}
        for entity, payload in comparison.items():
            if path == "source_summary.stale":
                stale = bool((payload.get("source_summary") or {}).get("stale"))
                raw[entity] = 1.0 if stale else 0.0
                continue
            node: Any = payload
            for part in path.split("."):
                node = node.get(part) if isinstance(node, dict) else None
            value = _to_float(node)
            if value is not None:
                raw[entity] = value

        if len(raw) < 1:
            continue
        has_signal = _has_discriminative_signal(raw)
        normalized = _normalize(raw, higher_is_better=higher_is_better) if has_signal else {name: 0.5 for name in raw}
        winner = None
        if has_signal and normalized:
            ordered = sorted(normalized.items(), key=lambda item: item[1], reverse=True)
            winner = ordered[0][0] if len(ordered) == 1 or (ordered[0][1] - ordered[1][1]) > 1e-6 else None
        factors.append(
            {
                "factor": label,
                "weight": weight,
                "winner": winner,
                "scores": {name: round(score, 4) for name, score in normalized.items()},
                "coverage": round(len(raw) / max(len(comparison), 1), 4),
            }
        )
        if has_signal:
            for entity, score in normalized.items():
                totals[entity] += score * weight
                weights_used[entity] += weight

    return factors, totals, weights_used


def _factor_scores_mf(
    comparison: dict[str, dict[str, Any]],
    downside_focus: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, float], dict[str, float], dict[str, Any]]:
    factors: list[dict[str, Any]] = []
    totals: dict[str, float] = {name: 0.0 for name in comparison}
    weights_used: dict[str, float] = {name: 0.0 for name in comparison}

    has_holdings = any(bool((payload.get("holdings") or [])) for payload in comparison.values())
    holdings_reasoning = {"status": "enabled" if has_holdings else "blocked", "reason": None}
    if not has_holdings:
        holdings_reasoning["reason"] = "Holdings-based reasoning unavailable. Holdings sync pending."

    if downside_focus:
        specs = [
            ("Downside (Max Drawdown 1Y)", "max_drawdown_1y", 0.4, False),
            ("Risk (Volatility 1Y)", "volatility_1y", 0.2, False),
            ("Returns (3Y)", "return_3y", 0.2, True),
            ("Cost (Expense Ratio)", "expense_ratio", 0.15, False),
            ("Freshness", "stale", 0.05, False),
        ]
    else:
        specs = [
            ("Returns (3Y)", "return_3y", 0.3, True),
            ("Risk (Volatility 1Y)", "volatility_1y", 0.2, False),
            ("Downside (Max Drawdown 1Y)", "max_drawdown_1y", 0.2, False),
            ("Cost (Expense Ratio)", "expense_ratio", 0.15, False),
            ("Freshness", "stale", 0.15, False),
        ]

    for label, field, weight, higher_is_better in specs:
        raw: dict[str, float] = {}
        for entity, payload in comparison.items():
            if field == "stale":
                stale = bool((payload.get("source_summary") or {}).get("stale"))
                raw[entity] = 1.0 if stale else 0.0
                continue
            value = _to_float(payload.get(field))
            if value is not None:
                raw[entity] = value
        if len(raw) < 1:
            continue
        has_signal = _has_discriminative_signal(raw)
        normalized = _normalize(raw, higher_is_better=higher_is_better) if has_signal else {name: 0.5 for name in raw}
        winner = None
        if has_signal and normalized:
            ordered = sorted(normalized.items(), key=lambda item: item[1], reverse=True)
            winner = ordered[0][0] if len(ordered) == 1 or (ordered[0][1] - ordered[1][1]) > 1e-6 else None
        factors.append(
            {
                "factor": label,
                "weight": weight,
                "winner": winner,
                "scores": {name: round(score, 4) for name, score in normalized.items()},
                "coverage": round(len(raw) / max(len(comparison), 1), 4),
            }
        )
        if has_signal:
            for entity, score in normalized.items():
                totals[entity] += score * weight
                weights_used[entity] += weight

    return factors, totals, weights_used, holdings_reasoning


def _data_limitations(asset_type: str, comparison: dict[str, dict[str, Any]]) -> list[str]:
    limitations: list[str] = []
    for entity, payload in comparison.items():
        quality = payload.get("data_quality") or {}
        missing_fields = quality.get("missing_fields") or []
        if missing_fields:
            limitations.append(f"{entity}: missing {', '.join(missing_fields[:8])}")
        if asset_type == "mutual_fund" and not payload.get("holdings"):
            limitations.append(f"{entity}: holdings data missing")
    return limitations


def _strengths_tradeoffs(factors: list[dict[str, Any]], winner_id: str | None) -> tuple[list[str], list[str]]:
    strengths: list[str] = []
    tradeoffs: list[str] = []
    for factor in factors:
        factor_name = factor.get("factor")
        factor_winner = factor.get("winner")
        if not factor_name:
            continue
        if winner_id and factor_winner == winner_id:
            strengths.append(f"{winner_id} leads on {factor_name}.")
        elif factor_winner:
            tradeoffs.append(f"{factor_winner} leads on {factor_name}.")
    return strengths[:6], tradeoffs[:6]


def _freshness_snapshot(comparison: dict[str, dict[str, Any]]) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for entity, payload in comparison.items():
        summary = payload.get("source_summary") or {}
        snapshot[entity] = {
            "source": summary.get("metadata") or payload.get("source"),
            "stale": bool(summary.get("stale")),
            "price_date": summary.get("price_date"),
            "snapshot_last_updated": summary.get("snapshot_last_updated"),
            "nav_date": payload.get("nav_date"),
        }
    return snapshot


def _risk_item(
    entity: str,
    label: str,
    level: str,
    evidence: str,
    confidence: str = "Medium",
    kind: str = "risk",
) -> dict[str, Any]:
    return {
        "entity": entity,
        "label": label,
        "level": level,
        "evidence": evidence,
        "confidence": confidence,
        "kind": kind,
    }


def _data_gap_item(entity: str, label: str, evidence: str) -> dict[str, Any]:
    return _risk_item(entity, label, "Not available", evidence, "Low", "data_gap")


def _build_stock_risk_analysis(comparison: dict[str, dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for entity, payload in comparison.items():
        fundamentals = payload.get("fundamentals") if isinstance(payload.get("fundamentals"), dict) else {}
        quality = payload.get("data_quality") if isinstance(payload.get("data_quality"), dict) else {}
        source = payload.get("source_summary") if isinstance(payload.get("source_summary"), dict) else {}

        debt = _to_float(fundamentals.get("debt_to_equity"))
        if debt is None:
            items.append(_data_gap_item(entity, "Debt risk", "Debt/equity is missing."))
        elif debt >= 2:
            items.append(_risk_item(entity, "Debt risk", "High", f"Debt/equity is {debt:.2f}."))
        elif debt >= 1:
            items.append(_risk_item(entity, "Debt risk", "Medium", f"Debt/equity is {debt:.2f}."))

        pe = _to_float(fundamentals.get("pe"))
        profit_growth = _to_float(fundamentals.get("profit_growth_3y"))
        if pe is None:
            items.append(_data_gap_item(entity, "Valuation risk", "P/E ratio is missing."))
        elif pe >= 60:
            items.append(_risk_item(entity, "Valuation risk", "High", f"P/E ratio is {pe:.2f}."))
        elif pe >= 35:
            items.append(_risk_item(entity, "Valuation risk", "Medium", f"P/E ratio is {pe:.2f}."))

        if profit_growth is None:
            items.append(_data_gap_item(entity, "Earnings trend", "3Y profit growth is missing."))
        elif profit_growth < 0:
            items.append(_risk_item(entity, "Earnings trend", "High", f"3Y profit growth is {profit_growth:.2f}%."))

        margin = _to_float(fundamentals.get("net_profit_margin") or fundamentals.get("operating_margin"))
        if margin is not None and margin < 5:
            items.append(_risk_item(entity, "Margin pressure", "Medium", f"Latest margin is {margin:.2f}%."))

        missing_fields = quality.get("missing_fields") if isinstance(quality.get("missing_fields"), list) else []
        if missing_fields:
            items.append(_data_gap_item(entity, "Data availability", f"Missing fields: {', '.join(str(field) for field in missing_fields[:5])}."))
        if source.get("stale"):
            items.append(_risk_item(entity, "Freshness risk", "Medium", str(source.get("stale_warning") or "Source data may be stale."), "Medium"))

    return {
        "asset_type": "stock",
        "items": items,
        "summary": "Deterministic stock risk signals with unavailable metrics labeled separately as data gaps.",
    }


def _build_mf_risk_analysis(comparison: dict[str, dict[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for entity, payload in comparison.items():
        quality = payload.get("data_quality") if isinstance(payload.get("data_quality"), dict) else {}
        source = payload.get("source_summary") if isinstance(payload.get("source_summary"), dict) else {}

        risk_level = str(payload.get("risk_level") or "").strip()
        if risk_level:
            level = "High" if "high" in risk_level.lower() else "Medium"
            items.append(_risk_item(entity, "Official risk label", level, f"AMC risk label is {risk_level}.", "High"))
        else:
            items.append(_data_gap_item(entity, "Official risk label", "AMC risk label is missing."))

        volatility = _to_float(payload.get("volatility_1y"))
        if volatility is None:
            items.append(_data_gap_item(entity, "Volatility", "1Y volatility is missing."))
        elif volatility >= 20:
            items.append(_risk_item(entity, "Volatility", "High", f"1Y volatility is {volatility:.2f}%."))
        elif volatility >= 12:
            items.append(_risk_item(entity, "Volatility", "Medium", f"1Y volatility is {volatility:.2f}%."))

        drawdown = _to_float(payload.get("max_drawdown_1y"))
        if drawdown is None:
            items.append(_data_gap_item(entity, "Drawdown", "1Y max drawdown is missing."))
        elif abs(drawdown) >= 20:
            items.append(_risk_item(entity, "Drawdown", "High", f"1Y max drawdown is {abs(drawdown):.2f}%."))
        elif abs(drawdown) >= 10:
            items.append(_risk_item(entity, "Drawdown", "Medium", f"1Y max drawdown is {abs(drawdown):.2f}%."))

        expense = _to_float(payload.get("expense_ratio"))
        if expense is None:
            items.append(_data_gap_item(entity, "Cost risk", "Expense ratio is missing."))
        elif expense >= 1.5:
            items.append(_risk_item(entity, "Cost risk", "High", f"Expense ratio is {expense:.2f}%."))
        elif expense >= 1:
            items.append(_risk_item(entity, "Cost risk", "Medium", f"Expense ratio is {expense:.2f}%."))

        return_3y = _to_float(payload.get("return_3y"))
        if return_3y is None:
            items.append(_data_gap_item(entity, "Performance risk", "3Y return is missing."))
        elif return_3y < 0:
            items.append(_risk_item(entity, "Performance risk", "Medium", f"3Y return is {return_3y:.2f}%."))

        if not payload.get("holdings"):
            items.append(_data_gap_item(entity, "Concentration risk", "Holdings data is missing."))
        if source.get("stale"):
            items.append(_risk_item(entity, "Freshness risk", "Medium", "Latest NAV or source data may be stale.", "Medium"))

        missing_fields = quality.get("missing_fields") if isinstance(quality.get("missing_fields"), list) else []
        if missing_fields:
            items.append(_data_gap_item(entity, "Data availability", f"Missing fields: {', '.join(str(field) for field in missing_fields[:5])}."))

    return {
        "asset_type": "mutual_fund",
        "items": items,
        "summary": "Deterministic mutual fund risk signals with unavailable metrics labeled separately as data gaps.",
    }


def build_stock_why_better(comparison: dict[str, dict[str, Any]]) -> dict[str, Any]:
    entities = list(comparison.keys())
    factors, totals, weights_used = _factor_scores_stock(comparison)
    normalized_scores = {
        entity: (totals[entity] / weights_used[entity]) if weights_used[entity] > 0 else 0.0
        for entity in entities
    }
    coverage = {entity: min(weights_used[entity], 1.0) for entity in entities}
    winner = _winner_object("stock", entities, normalized_scores, coverage)
    limitations = _data_limitations("stock", comparison)
    winner_name = winner.get("entity_name")
    strengths, tradeoffs = _strengths_tradeoffs(factors, winner_name)
    top_score = max(normalized_scores.values()) if normalized_scores else 0.0
    confidence_score = min(top_score * max(max(coverage.values(), default=0.0), 0.2), 1.0)
    label = _confidence_label(confidence_score)
    verdict_context = "Deterministic comparison based on available local data for selected factors and selected period; not a universal investment verdict."

    if winner.get("status") == "insufficient_data":
        summary = "Insufficient local data to determine a reliable winner."
    elif winner.get("status") == "tie":
        summary = "Both entities are close on the selected deterministic factors."
    else:
        summary = f"{winner_name} ranks higher on the selected deterministic factors."

    return {
        "winner": winner,
        "confidence": {"score": round(confidence_score, 4), "label": label},
        "summary": summary,
        "factor_results": factors,
        "strengths": strengths,
        "tradeoffs": tradeoffs,
        "data_limitations": limitations,
        "source_freshness": _freshness_snapshot(comparison),
        "risk_analysis": _build_stock_risk_analysis(comparison),
        "verdict_context": verdict_context,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def build_mf_why_better(comparison: dict[str, dict[str, Any]], downside_focus: bool = False) -> dict[str, Any]:
    entities = list(comparison.keys())
    factors, totals, weights_used, holdings_reasoning = _factor_scores_mf(comparison, downside_focus=downside_focus)
    normalized_scores = {
        entity: (totals[entity] / weights_used[entity]) if weights_used[entity] > 0 else 0.0
        for entity in entities
    }
    coverage = {entity: min(weights_used[entity], 1.0) for entity in entities}
    winner = _winner_object("mutual_fund", entities, normalized_scores, coverage)
    limitations = _data_limitations("mutual_fund", comparison)
    if holdings_reasoning.get("status") == "blocked" and holdings_reasoning.get("reason"):
        limitations.append(str(holdings_reasoning["reason"]))
    winner_name = winner.get("entity_name")
    strengths, tradeoffs = _strengths_tradeoffs(factors, winner_name)
    top_score = max(normalized_scores.values()) if normalized_scores else 0.0
    confidence_score = min(top_score * max(max(coverage.values(), default=0.0), 0.2), 1.0)
    label = _confidence_label(confidence_score)
    verdict_context = "Deterministic comparison based on available local NAV/risk/cost factors for selected funds; not a universal investment verdict."

    if winner.get("status") == "insufficient_data":
        summary = "Insufficient local data to determine a reliable winner."
        research_notes = []
    else:
        categories = {}
        for entity, payload in comparison.items():
            cat = str(payload.get("category") or payload.get("sub_category") or "Unknown").strip()
            if cat and cat.lower() != "unknown":
                categories[entity] = cat
                
        unique_categories = set(cat.lower() for cat in categories.values())
        research_notes = []
        
        if len(unique_categories) > 1:
            diff_text = " vs ".join([f"{entity} ({cat})" for entity, cat in categories.items()])
            summary = f"Different mandates detected: {diff_text}. Direct comparison may be misleading."
            research_notes.append({
                "title": "Different fund mandates",
                "content": f"These funds use different investment strategies or asset classes ({diff_text}). They should be judged on how well they fulfill their specific mandates, rather than purely against each other."
            })
        elif len(unique_categories) == 1:
            cat_name = list(categories.values())[0]
            summary = f"Both funds share a {cat_name} mandate, making direct comparison more valid."
            research_notes.append({
                "title": f"Shared mandate ({cat_name})",
                "content": f"Both funds share the same {cat_name} mandate, making direct comparison of returns, downside control, and portfolio quality highly relevant."
            })
        else:
            summary = "Direct comparison based on available data."
            
        research_notes.append({
            "title": "Return-only limitation",
            "content": "A direct return-only comparison may be misleading. A better comparison should include rolling returns, volatility, drawdown, Sharpe ratio, expense ratio, AUM, and asset-allocation history."
        })
        
        research_notes.append({
            "title": "Deterministic comparison",
            "content": "This is a deterministic comparison based on available local data and quantitative factors. It is not a universal investment verdict and should be combined with qualitative research."
        })

    return {
        "winner": winner,
        "confidence": {"score": round(confidence_score, 4), "label": label},
        "summary": summary,
        "query_focus": {"downside_focus": downside_focus},
        "factor_results": factors,
        "strengths": strengths,
        "tradeoffs": tradeoffs,
        "data_limitations": limitations,
        "source_freshness": _freshness_snapshot(comparison),
        "risk_analysis": _build_mf_risk_analysis(comparison),
        "verdict_context": verdict_context,
        "holdings_based_reasoning": holdings_reasoning,
        "research_notes": research_notes,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
