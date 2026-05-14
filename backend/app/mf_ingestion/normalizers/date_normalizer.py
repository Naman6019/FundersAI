from __future__ import annotations

from datetime import date, datetime
import re


_MONTH_TOKEN = re.compile(r"(?P<month>jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s\-_]+(?P<year>20\d{2})", re.IGNORECASE)


def normalize_report_month(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, date):
        return value.replace(day=1)
    raw = str(value).strip()
    if not raw:
        return None

    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%Y-%m", "%b %Y", "%B %Y"):
        try:
            parsed = datetime.strptime(raw[: max(len(fmt), 7)], fmt)
            return date(parsed.year, parsed.month, 1)
        except ValueError:
            continue

    match = _MONTH_TOKEN.search(raw)
    if not match:
        return None

    month = datetime.strptime(match.group("month")[:3], "%b").month
    return date(int(match.group("year")), month, 1)
