"""Deterministic fund slug derivation, per the fund-page design spec section 5.3.

`fund_slug(scheme_name)` strips plan and option suffixes, punctuation, and segregated-portfolio
parentheticals, producing a stable kebab-case slug.

Why this exists rather than reusing `mf_catalog_service.slug`:

The original generator was `f"{slug(scheme_name)}-{code}"`, which appended the AMFI code to a slug
that still carried "- Direct Plan - Growth Option". Every non-grandfathered scheme therefore got
a URL like `hdfc-elss-tax-saver-fund-direct-plan-growth-option-119060`. A public fund page is a
consumer-facing SEO surface, so its URL should be the fund's name, not its share-class metadata
plus a database key. The code is already carried as a page field and as schema.org
`AMFI Scheme Code`, so it does not need to be in the path.

Determinism matters as much as tidiness. Two schemes in one AMC can legitimately clean down to
the same base (a Direct and a Regular share class, or an IDCW sibling). The spec resolves that by
age — the older `first_published_at` keeps the base slug and the newcomer takes a `-<scheme_code>`
suffix — which is stable across re-runs in a way that alphabetical or insertion ordering is not.
`assign_slugs` implements that policy over a whole catalog so two rows can never be handed the
same URL.
"""
from __future__ import annotations

import re

# Share-class phrasing appears in several shapes:
#   " - Direct Plan - Growth Option"   (the AMFI eight-column form)
#   " - Direct Plan - GROWTH"          (upper-cased option)
#   " - - Direct Plan - Growth"        (a doubled separator, seen on ICICI Prudential Liquid)
#   "... IDCW Payout Option"           (option + payout marker + a trailing "Option")
_PLAN = re.compile(r"\b(direct|regular)\s+plans?\b", re.IGNORECASE)
_OPTION = re.compile(
    r"\b(growth|idcw|dividend|bonus|cumulative)\b"
    r"(?:\s+(?:payout|reinvestment|re-investment|plan|option|cumulative|growth|idcw))*",
    re.IGNORECASE,
)

# The share-class tail runs from the first dash-separated plan/option marker to the end of the
# name, so the whole tail is consumed in one match. Anchoring to the tail rather than removing
# markers globally is what preserves names like "Nippon India Growth Mid Cap Fund" and
# "SBI CHILDREN'S FUND - SAVINGS PLAN"; consuming to end-of-string is what removes repeats such
# as "... - Direct Plan - Direct Growth" and "... - Growth Option Option" without a second pass
# that could strip a legitimate word.
#
# The separator tolerates repeats and whitespace ("- -", "- "), and the marker may be preceded by
# a segregation-series token ("- SG1 Direct Growth", seen on Baroda BNP Paribas Short Term Fund),
# so `.*` is allowed before the plan word when a dash already introduced the segment.
_SHARE_CLASS_TAIL = re.compile(
    r"(?:\s*[-–—]\s*)+"
    r"(?:"
    r"(?:direct|regular)\s+plans?\b.*"
    r"|(?:growth|idcw|dividend|bonus|cumulative)\b.*"
    r"|(?:sg\d+|[a-z]{0,3}\d*)\s*(?:direct|regular)\b.*"
    r")$",
    re.IGNORECASE | re.DOTALL,
)

# A trailing parenthetical that is metadata rather than identity:
#   "(erstwhile Bluechip Fund)", "(Erstwhile known as SBI Magnum Low Duration Fund)",
#   "(formerly HDFC Top 100 Fund)", "(Non-convertible Preference Share) **",
#   "(60:40) Stable dividend 50 ETF"
# Segregated-portfolio parentheticals and footnote markers are stripped too.
_PARENTHETICAL = re.compile(r"\([^)]*\)")
_FOOTNOTE = re.compile(r"[\*#\^]+")

# A leading AMC-prefix artefact: "UTI - Money Market Fund" -> "uti-money-market-fund" is fine,
# but a bare "UTI - " segment after the AMC name would duplicate the amc_slug segment.
_LEADING_DASHES = re.compile(r"\s*[-–—]\s*")


def clean_fund_name(scheme_name: str) -> str:
    """The display portion of a scheme name, with share-class metadata removed.

    Order matters. The plan/option markers only ever appear as a *trailing* segment separated from
    the fund's name by a dash, and the tail runs to the end of the name. Cutting from the first
    such marker to the end removes every share-class repeat in one pass — "Direct Plan - Direct
    Growth", "Growth Option Option" — while leaving the identity before it verbatim.

    Removing the markers globally instead would corrupt real names: "Nippon India Growth Mid Cap
    Fund" contains "Growth" as part of its identity, and a global strip turns it into "Nippon
    India Mid Cap Fund", a different fund. Likewise "SBI CHILDREN'S FUND - SAVINGS PLAN" ends in
    "PLAN", which is the fund's own word and not share-class metadata.
    """
    text = str(scheme_name or "")
    text = _FOOTNOTE.sub(" ", text)
    text = _PARENTHETICAL.sub(" ", text)

    # A trailing whitespace-only difference after the cut is normal; strip separators either way.
    text = _SHARE_CLASS_TAIL.sub("", text)

    # Collapse a doubled or dangling separator left behind by the removal above.
    text = re.sub(r"(\s*-\s*){2,}", " - ", text)
    text = text.strip(" -–—")
    return re.sub(r"\s+", " ", text).strip()


def _kebab(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(value or "").lower().replace("&", "and")).strip("-")


def fund_slug(scheme_name: str, scheme_code: str | int | None = None, *, with_code: bool = False) -> str:
    """Kebab-case slug for a scheme name.

    `with_code` appends the AMFI code, which callers use to disambiguate a collision. It is off
    by default because the code is already a page field and does not belong in a clean URL.
    """
    base = _kebab(clean_fund_name(scheme_name))
    if not base:
        # A name that cleans to nothing must still produce a usable slug.
        base = "fund"
    if with_code and scheme_code is not None:
        return f"{base}-{scheme_code}"
    return base


def assign_slugs(
    rows: list[dict],
    *,
    taken: dict[tuple[str, str], str] | None = None,
) -> dict[str, str]:
    """Assign a unique `fund_slug` per scheme, resolving collisions by published age.

    `rows` items need `scheme_code`, `amc_slug`, `scheme_name` and optionally
    `first_published_at` (ISO string) for the age tiebreak.

    `taken` seeds the assignment with slugs already frozen in the database, keyed
    `(amc_slug, fund_slug)` to the owning `scheme_code`, so a new scheme cannot claim a URL that
    an existing published page already owns.

    Returns `{scheme_code: fund_slug}`. A scheme that must take the disambiguated form gets the
    `-<scheme_code>` suffix, which is deterministic: re-running with the same inputs produces the
    same result, and the same scheme always wins its own base slug because its code appears in
    the tiebreak rather than in the ordering.
    """
    seed = dict(taken or {})
    claimed_base: dict[tuple[str, str], list[str]] = {}

    ordered = sorted(
        rows,
        key=lambda row: (
            str(row.get("first_published_at") or ""),
            str(row.get("scheme_code")),
        ),
    )

    # Pass 1: every scheme records the base slug it wants, in age order.
    for row in ordered:
        code = str(row.get("scheme_code"))
        amc = str(row.get("amc_slug") or "")
        base = fund_slug(row.get("scheme_name"))
        claimed_base.setdefault((amc, base), []).append(code)

    # Pass 2: honour existing frozen ownership before any new claim.
    owners: dict[tuple[str, str], str] = dict(seed)
    result: dict[str, str] = {}

    for row in ordered:
        code = str(row.get("scheme_code"))
        amc = str(row.get("amc_slug") or "")
        base = fund_slug(row.get("scheme_name"))
        key = (amc, base)

        if key in owners:
            if str(owners[key]) == code:
                result[code] = base
                continue
            # Someone else owns this URL; take the deterministic disambiguated form.
            result[code] = fund_slug(row.get("scheme_name"), code, with_code=True)
            continue

        contenders = claimed_base.get(key, [])
        if len(contenders) == 1:
            owners[key] = code
            result[code] = base
            continue

        # Several schemes share a base. The first in age order keeps it; the rest are suffixed.
        winner = contenders[0]
        if code == winner:
            owners[key] = code
            result[code] = base
        else:
            result[code] = fund_slug(row.get("scheme_name"), code, with_code=True)

    # A suffixed form can itself collide with an unrelated frozen URL; verify and extend once.
    for row in ordered:
        code = str(row.get("scheme_code"))
        amc = str(row.get("amc_slug") or "")
        candidate = result[code]
        key = (amc, candidate)
        owner = owners.get(key)
        if owner is None or str(owner) == code:
            owners[key] = code
            continue
        result[code] = fund_slug(row.get("scheme_name"), f"{code}-1", with_code=True)

    return result
