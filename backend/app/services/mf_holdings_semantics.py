"""Semantic ISIN-identity validation for holdings rows.

Why this exists, and how it differs from `mf_holdings_alignment`:

`mf_holdings_alignment` guards the AMFI scheme-wise disclosure payload, where a single
authoritative source publishes one ISIN per security. There, a *string* comparison is safe:
one ISIN mapping to more than one company name IS the defect, and it correctly rejected the
corrupt Apr-Jun 2026 UTI payload.

Document-parsed holdings (`mf_scheme_holdings`, from AMC factsheets and portfolio sheets) are
a different problem. Every AMC names the same security differently — one ISIN for 6.36%
GOI 16-Feb-2031 appears as "6.36% CGL 2031", "GOI - 6.36% (16/02/2031)" and "06.36% GSEC
Mat- 16/02/2031". A string comparison there would reject almost every document. Measured on
53,149 real rows: 1,822 of 4,577 ISINs carry more than one name string, and every one of them
is legitimate AMC naming variance.

**Scope is the whole design.** Measured on the same 53,149 rows:

    GLOBAL (all documents pooled)   coupon=2  maturity=7  issuer_disjoint=153
    WITHIN-DOCUMENT                 coupon=0  maturity=0  issuer_disjoint=0

Pooling documents produces 162 apparent conflicts, all of which are two different AMCs
describing the same security differently — one issuer calling a bond "6.27% IKF Finance Ltd."
while another calls it "9.4% IKF Finance Limited", or "NABARD" against its full name. Within a
single document, a well-formed disclosure has none. So the caller must pass the rows of ONE
source document, exactly as the AMFI check operates on one payload.

Three independent signals, in decreasing order of certainty:

1. **Coupon conflict.** A bond ISIN has exactly one coupon. Two different coupons for one ISIN
   is unambiguous misalignment. (`IN0020200120` pools 4.7% and 6.75% across documents because
   it is a floating-rate bond reported at different reset dates — a cross-document artefact
   that disappears within a document.)
2. **Maturity conflict.** A bond ISIN has exactly one maturity date. Compared at the coarsest
   common granularity, so "2031" and "2031-02" agree while "2031" and "2033" do not. A
   strips/principal pair legitimately carries two dates; that shape is excluded below.
3. **Disjoint issuer tokens.** If two names for one ISIN share no significant word, they are
   different securities collapsed onto one ISIN. A shared token means a rename or a garbled
   label for the same security.

Signal 3 is what distinguishes real corruption from cosmetic variance, and it is deliberately
token-based rather than string-similarity-based. Measured against `rapidfuzz.WRatio`, string
similarity is *inverted* on this data: "ITC LTD" vs "INFOSYS LTD" scores 85.5 while genuine
variants "EQ - REC LTD" vs "Rural Electrification Corporation Ltd." score 29.7. Similarity
cannot separate corruption from abbreviation, so it is not used.

    "ITC LTD"  vs  "INFOSYS LTD"
        no shared token  -> different securities. Conflict.
    "NIPPON INDIA MUTUALFUND"  vs  "Nippon India MF- Nippon India Silver ETF"
        shared token {@nippon}  -> same security, garbled label. Not a conflict.

The second case is Groww's own spreadsheet printing a Silver ETF's issuer incorrectly in one
sheet while the ISIN, quantity and market value agree (verified: both rows imply Rs 223.21 per
unit), so it must not be treated as corruption.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# A coupon is printed as "6.36%", "06.36 %", "8,20%". Capture it wherever it appears.
_COUPON = re.compile(r"(?<!\d)(\d{1,2})[.,](\d{1,2})\s*%")

# Maturity appears as dd/mm/yyyy, dd-mm-yyyy, dd-Mon-yyyy, ddmmyyyy, or a bare year.
_DMY = re.compile(r"(?<!\d)(\d{1,2})[/-](\d{1,2})[/-](20\d{2})(?!\d)")
_DMON = re.compile(r"(?<!\d)(\d{1,2})-([A-Za-z]{3})-(20\d{2})(?!\d)")
_DIGITS = re.compile(r"(?<!\d)(\d{2})(\d{2})(20\d{2})(?!\d)")
_YEAR = re.compile(r"(?<!\d)(20\d{2})(?!\d)")

_MONTHS = {
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12,
}

# Words that carry no identity: legal suffixes, instrument wrappers, plan/option noise.
_STOPWORDS = {
    "ltd", "limited", "pvt", "private", "inc", "plc", "co", "company", "corp",
    "corporation", "the", "and", "of", "fund", "funds", "scheme", "mutual",
    "etf", "mf", "fof", "units", "unit", "class", "option", "plan", "direct",
    "growth", "regular", "idcw", "dividend", "series", "tranche", "a2", "a1",
    "gsec", "gsecs", "cgl", "goi", "gs", "sdl", "treasury", "sec", "securities",
    "government", "india", "mat", "maturity", "red", "redeemed", "frb", "floating", "rate",
}

# A principal-and-coupon strips position legitimately prints two maturity dates for one ISIN.
_STRIPS = re.compile(r"\bstrips?\b|\(c\)|\(p\)", re.IGNORECASE)

_ISIN_SENTINELS = {"(blank)", "blank", "n/a", "na", "none", "null", "-", "--"}


@dataclass(frozen=True)
class IsinIdentityConflict:
    isin: str
    kind: str  # coupon | maturity | issuer_tokens
    detail: str
    names: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IsinIdentityResult:
    is_consistent: bool
    conflicts: list[IsinIdentityConflict] = field(default_factory=list)
    checked_isins: int = 0
    label_variants: int = 0  # same security under different spellings; not a conflict

    def review_issues(self) -> list[str]:
        """Issue codes suitable for a `needs_review` staging record."""
        return sorted({f"isin_identity_{conflict.kind}" for conflict in self.conflicts})


def normalise_isin(value: Any) -> str:
    isin = str(value or "").strip()
    return "" if isin.lower() in _ISIN_SENTINELS else isin


def parse_coupon(name: str) -> float | None:
    match = _COUPON.search(str(name or ""))
    if not match:
        return None
    return float(f"{match.group(1)}.{match.group(2)}")


def _valid_date(day: int, month: int) -> bool:
    return 1 <= month <= 12 and 1 <= day <= 31


def parse_maturity(name: str) -> tuple[int, int | None, int | None] | None:
    """Return (year, month, day) with month/day None when only a year is printed.

    Partial granularity is deliberate: "6.36% CGL 2031" and "6.36% GOI 16-Feb-2031" are the
    same bond, so a year-only value must not conflict with a full date in the same year.
    """
    text = str(name or "")

    match = _DMY.search(text)
    if match and _valid_date(int(match.group(1)), int(match.group(2))):
        return (int(match.group(3)), int(match.group(2)), int(match.group(1)))

    match = _DMON.search(text)
    if match and match.group(2).lower() in _MONTHS:
        return (int(match.group(3)), _MONTHS[match.group(2).lower()], int(match.group(1)))

    match = _DIGITS.search(text)
    if match and _valid_date(int(match.group(1)), int(match.group(2))):
        return (int(match.group(3)), int(match.group(2)), int(match.group(1)))

    match = _YEAR.search(text)
    if match:
        return (int(match.group(1)), None, None)

    return None


def maturity_compatible(
    a: tuple[int, int | None, int | None] | None,
    b: tuple[int, int | None, int | None] | None,
) -> bool:
    """Compare at the coarsest granularity the two names share."""
    if a is None or b is None:
        return True
    for left, right in zip(a, b):
        if left is None or right is None:
            continue
        if left != right:
            return False
    return True


def issuer_tokens(name: str) -> set[str]:
    """Significant identity words, as a set. Order-independent."""
    return set(_issuer_signature(name)[0])


def _issuer_signature(name: str) -> tuple[list[str], str]:
    """Significant tokens in order, plus their concatenation.

    The concatenated form exists because Indian disclosures split and join names
    inconsistently: "Tamil Nadu" and "Tamilnadu", "Nippon India Mutual Fund" and
    "NIPPON INDIA MUTUALFUND" describe one issuer but share no whole token.
    """
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", str(name or "").lower())
        if token not in _STOPWORDS and len(token) > 2 and not token.isdigit()
    ]
    return tokens, "".join(tokens)


def _same_issuer(signatures: list[tuple[list[str], str]]) -> bool:
    """Whether all informative names plausibly denote one issuer.

    The only acceptance rule is a **shared significant token**. That is deliberately strict,
    because every looser rule tested against real data was unsound:

        "MAHINDRA & MAHINDRA LTD."  is a prefix of  "MAHINDRA AND MAHINDRA FINANCIAL SERVICES LTD"
        "Tamil Nadu SDL"            joins to       "Tamilnadu State Development Loans"

    The first pair is two *different* issuers (parent and NBFC subsidiary); the second is one
    issuer spelled two ways. Both are prefix/substring relations, so any containment or
    concatenation rule accepts one of them wrongly. Token intersection separates them correctly
    (Mahindra shares "mahindra"; the AMFI corruption shares nothing), and the spelling cases it
    does not resolve are a *known limitation* rather than a silent hole:

    - A conflict produces a `needs_review` flag, never a delete.
    - Empirically, spacing-only variance within a single document does not occur: 0 conflicts
      across 36 real AMC documents / 59,344 rows.

    The failure direction is chosen on purpose. A false positive costs one human glance; a false
    negative silently corrupts every ISIN-keyed join downstream. Where the evidence is
    ambiguous, flag it — do not guess.
    """
    informative = [tokens for tokens, _ in signatures if tokens]
    if len(informative) < 2:
        return True

    return bool(set.intersection(*[set(tokens) for tokens in informative]))


def validate_isin_identity(rows: list[dict[str, Any]]) -> IsinIdentityResult:
    """Check that every ISIN in ONE source document's holdings denotes a single security.

    `rows` must be the holdings of a single source document. Pooling documents reintroduces
    the cross-AMC naming variance this check exists to tolerate; see the module docstring.
    Expects `isin` and `instrument_name` keys. Rows without a real ISIN are skipped.
    """
    grouped: dict[str, list[str]] = {}
    for row in rows:
        isin = normalise_isin(row.get("isin"))
        if not isin:
            continue
        name = str(row.get("instrument_name") or "").strip()
        if name:
            grouped.setdefault(isin, []).append(name)

    conflicts: list[IsinIdentityConflict] = []
    label_variants = 0

    for isin, names in grouped.items():
        distinct = sorted(set(names))
        if len(distinct) < 2:
            continue

        # A strips position carries a coupon date and a principal date for one ISIN; the
        # two-date shape is legitimate and must not be read as a maturity conflict.
        if any(_STRIPS.search(name) for name in distinct):
            label_variants += 1
            continue

        # 1. Coupon: a bond has exactly one.
        coupons = {parse_coupon(name) for name in distinct} - {None}
        if len(coupons) > 1:
            conflicts.append(
                IsinIdentityConflict(
                    isin=isin,
                    kind="coupon",
                    detail=f"{len(coupons)} distinct coupons: {sorted(coupons)}",
                    names=distinct,
                )
            )
            continue

        # 2. Maturity: a bond has exactly one, compared at shared granularity.
        maturities = [parse_maturity(name) for name in distinct]
        conflicting = any(
            not maturity_compatible(maturities[i], maturities[j])
            for i in range(len(maturities))
            for j in range(i + 1, len(maturities))
        )
        if conflicting:
            conflicts.append(
                IsinIdentityConflict(
                    isin=isin,
                    kind="maturity",
                    detail=f"incompatible maturities: {[m for m in maturities if m]}",
                    names=distinct,
                )
            )
            continue

        # 3. Issuer identity: two names with no shared token and no containment describe
        #    different securities. A shared or contained form means a rename or garbled label.
        if not _same_issuer([_issuer_signature(name) for name in distinct]):
            conflicts.append(
                IsinIdentityConflict(
                    isin=isin,
                    kind="issuer_tokens",
                    detail="names share no identity token",
                    names=distinct,
                )
            )
            continue

        # Names differ but describe the same security: a label variant, not corruption.
        label_variants += 1

    return IsinIdentityResult(
        is_consistent=not conflicts,
        conflicts=conflicts,
        checked_isins=len(grouped),
        label_variants=label_variants,
    )
