from __future__ import annotations

import logging
import re
import time
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")
TRANSIENT_HTTP_STATUSES = frozenset({502, 503, 504, 522, 525})
_TRANSIENT_STATUS_PATTERN = re.compile(r"(?<!\d)(502|503|504|522|525)(?!\d)")


def _status_code(value: Any) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def is_transient_supabase_error(exc: BaseException) -> bool:
    """Return true only for explicitly retryable HTTP statuses."""
    response = getattr(exc, "response", None)
    candidates = (
        getattr(exc, "status_code", None),
        getattr(exc, "code", None),
        getattr(response, "status_code", None),
    )
    for candidate in candidates:
        status = _status_code(candidate)
        if status is not None:
            return status in TRANSIENT_HTTP_STATUSES

    details: list[str] = [str(exc)]
    for arg in getattr(exc, "args", ()):
        if isinstance(arg, dict):
            details.extend(str(arg.get(key) or "") for key in ("code", "message", "details", "hint"))
        else:
            details.append(str(arg))
    error_text = " ".join(details).lower()
    return bool(_TRANSIENT_STATUS_PATTERN.search(error_text))


def execute_with_retry(
    operation: Callable[[], T],
    *,
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
    sleep: Callable[[float], None] = time.sleep,
    operation_name: str = "supabase_operation",
    log: logging.Logger | None = None,
) -> T:
    """Retry a Supabase operation with bounded exponential backoff."""
    attempts = max(1, int(max_attempts))
    delay = max(0.0, float(base_delay_seconds))
    for attempt in range(1, attempts + 1):
        try:
            return operation()
        except Exception as exc:
            if attempt >= attempts or not is_transient_supabase_error(exc):
                raise
            if log:
                log.warning(
                    "%s transient Supabase failure; retrying attempt %s/%s",
                    operation_name,
                    attempt + 1,
                    attempts,
                )
            sleep(delay)
            delay *= 2
    raise RuntimeError("unreachable")
