from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from typing import Any
from urllib.parse import urlparse


FRESH_MARKET_CONTEXT_HOURS = 72

OFFICIAL_MARKET_DOMAINS = (
    "bseindia.com",
    "iea.org",
    "nseindia.com",
    "nsdl.co.in",
    "rbi.org.in",
    "sebi.gov.in",
)

HIGH_TRUST_NEWS_DOMAINS = (
    "ft.com",
    "reuters.com",
)


def _parse_published(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            parsed = parsedate_to_datetime(text)
        except (TypeError, ValueError, OverflowError):
            try:
                parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            except ValueError:
                return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _domain(value: Any) -> str:
    try:
        return urlparse(str(value or "")).netloc.lower().removeprefix("www.")
    except ValueError:
        return ""


def _matches_domain(domain: str, candidates: tuple[str, ...]) -> bool:
    return any(domain == candidate or domain.endswith(f".{candidate}") for candidate in candidates)


def _source_tier(source: Any, url: Any) -> str:
    domain = _domain(url)
    source_text = str(source or "").lower()
    if _matches_domain(domain, OFFICIAL_MARKET_DOMAINS):
        return "official"
    if _matches_domain(domain, HIGH_TRUST_NEWS_DOMAINS) or "reuters" in source_text or "financial times" in source_text:
        return "high_trust_news"
    return "approved_news"


def normalize_market_evidence(
    news_data: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    evidence: list[dict[str, Any]] = []
    seen: set[str] = set()

    for raw in news_data:
        if not isinstance(raw, dict):
            continue
        title = str(raw.get("title") or "").strip()
        url = str(raw.get("url") or "").strip()
        key = url.lower() or title.lower()
        if not key or key in seen:
            continue
        seen.add(key)

        published_at = _parse_published(raw.get("published") or raw.get("published_at"))
        age_hours = None
        freshness = "unknown"
        if published_at is not None:
            age_hours = round(max((current_time - published_at).total_seconds() / 3600, 0.0), 1)
            freshness = "fresh" if age_hours <= FRESH_MARKET_CONTEXT_HOURS else "stale"

        source = str(raw.get("source") or _domain(url) or "Source").strip()
        evidence.append(
            {
                "title": title,
                "source": source,
                "published": raw.get("published") or raw.get("published_at"),
                "published_at": published_at.isoformat() if published_at else None,
                "url": url,
                "context_type": raw.get("context_type") or "controlled_web_headline",
                "source_tier": _source_tier(source, url),
                "freshness": freshness,
                "age_hours": age_hours,
            }
        )

    evidence.sort(
        key=lambda item: (
            item.get("freshness") != "fresh",
            item.get("age_hours") if item.get("age_hours") is not None else float("inf"),
        )
    )
    return evidence


def market_context_status(evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        return "unavailable"
    if any(item.get("freshness") == "fresh" for item in evidence):
        return "fresh"
    if all(item.get("freshness") == "stale" for item in evidence):
        return "stale"
    return "limited"


def market_source_metadata(evidence: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "title": item.get("title"),
            "source": item.get("source"),
            "published": item.get("published"),
            "published_at": item.get("published_at"),
            "url": item.get("url"),
            "context_type": item.get("context_type"),
            "source_tier": item.get("source_tier"),
            "freshness": item.get("freshness"),
        }
        for item in evidence
    ]


def merge_market_sources(*source_groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[str] = set()
    for group in source_groups:
        for source in group:
            if not isinstance(source, dict):
                continue
            key = str(source.get("url") or source.get("title") or "").strip().lower()
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(source)
    return merged[:12]


def _evidence_markdown(evidence: list[dict[str, Any]]) -> str:
    if not evidence:
        return "- No pre-fetched approved headlines were available. Use web search before answering."

    lines: list[str] = []
    for item in evidence[:8]:
        freshness = str(item.get("freshness") or "unknown")
        published = str(item.get("published") or "date unavailable")
        source = str(item.get("source") or "Source")
        title = str(item.get("title") or "Untitled source")
        url = str(item.get("url") or "")
        link = f"[{source}]({url})" if url.startswith(("http://", "https://")) else source
        lines.append(f"- [{freshness}] {published}: {title} — {link}")
    return "\n".join(lines)


def build_market_messages(
    query: str,
    evidence: list[dict[str, Any]],
    *,
    now: datetime | None = None,
) -> list[dict[str, str]]:
    current_time = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    system_prompt = """You are FundersAI, a research-only Indian market analyst with web search.
Verify the user's premise before accepting it. For claims about wars, ceasefires, markets, oil, currencies, or foreign flows, search for the latest evidence.
Prefer Reuters for fast-moving events and official sources such as NSE, BSE, NSDL, RBI, SEBI, and IEA for market or economic data.
Do not invent a price, date, percentage, event status, or source. Cite every live factual claim with an inline markdown link.
Lead with a one-sentence answer to the user's actual question. Keep the writing natural and readable.
Use concise sections when relevant: Latest Evidence, Current View, What Would Change the View, Sectors to Watch, and Research Approach.
Correct a false or unconfirmed premise plainly. Distinguish a relief rally from a strong sustained rally.
Do not give personalized buy, sell, allocation, or timing instructions. Frame actions as research signals to monitor.
If reliable current evidence is insufficient, say exactly what is unconfirmed instead of filling gaps."""
    user_prompt = f"""Current UTC time: {current_time.isoformat()}

User question:
{query}

Pre-fetched approved headline evidence:
{_evidence_markdown(evidence)}

Search for fresher evidence where needed, reconcile conflicting reports, and answer with inline source links."""
    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]


def _premise_read(evidence: list[dict[str, Any]]) -> str:
    titles = " ".join(str(item.get("title") or "").lower() for item in evidence if item.get("freshness") == "fresh")
    ongoing_markers = (
        "breach",
        "ceasefire over",
        "failed ceasefire",
        "fresh strike",
        "new strike",
        "resumed strike",
        "tensions",
        "escalat",
    )
    easing_markers = ("peace deal", "ceasefire", "truce", "war ends", "war ended")
    if any(marker in titles for marker in ongoing_markers):
        return "The available fresh evidence indicates that a durable end is not confirmed."
    if any(marker in titles for marker in easing_markers):
        return "Recent headlines suggest easing tensions, but headlines alone do not confirm a durable settlement."
    return "The available approved evidence does not confirm that the conflict has conclusively ended."


def _fallback_source_lines(evidence: list[dict[str, Any]]) -> str:
    selected = [item for item in evidence if item.get("freshness") == "fresh"][:4] or evidence[:4]
    if not selected:
        return "- No sufficiently current approved evidence was available. Treat the view below as conditional."
    lines: list[str] = []
    for item in selected:
        source = str(item.get("source") or "Source")
        url = str(item.get("url") or "")
        title = str(item.get("title") or "Market update")
        published_at = _parse_published(item.get("published_at") or item.get("published"))
        date_label = published_at.strftime("%d %b %Y") if published_at else "date unavailable"
        link = f"[{source}]({url})" if url.startswith(("http://", "https://")) else source
        lines.append(f"- {title} ({date_label}, {link})")
    return "\n".join(lines)


def build_market_fallback(query: str, evidence: list[dict[str, Any]]) -> str:
    rally_question = "rally" in query.lower()
    heading = "Probably not a strong, sustained rally yet" if rally_question else "The market view is still conditional"
    return f"""### {heading}

{_premise_read(evidence)} A relief rally is possible, but a lasting broad-market move needs confirmation from oil, foreign flows, the rupee, and market breadth.

### Latest Evidence
{_fallback_source_lines(evidence)}

### Current View
The base case is volatile consolidation with occasional relief rallies. For India, higher crude can pressure the rupee, inflation expectations, company margins, and interest-rate expectations.

### What Would Strengthen the Rally Case
- A durable agreement rather than a temporary ceasefire headline
- Normal energy and shipping flows through the region
- Crude oil falling and remaining lower
- Foreign investor selling turning into sustained inflows
- Broad participation across sectors instead of a one-session index bounce

### Sectors to Watch
Lower oil would generally help airlines, paints, tyres, logistics, chemicals, consumer companies, banks, and oil-marketing companies. Upstream oil producers and short-term geopolitical trades may react differently.

### Research Approach
Treat one positive session as a relief signal, not confirmation. The stronger evidence would be falling crude, improving foreign flows, a stable rupee, and follow-through across several sessions."""
