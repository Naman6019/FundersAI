from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass(frozen=True)
class RateLimitWindow:
    name: str
    limit: int
    seconds: int


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    configured: bool
    limit: int
    remaining: int
    reset_seconds: int
    retry_after_seconds: int


# Mirrors the "reports" group in backend/app/services/rate_limit.py so the two
# services agree on how expensive report generation is allowed to be per caller.
RATE_LIMIT_GROUPS: dict[str, list[RateLimitWindow]] = {
    "reports": [
        RateLimitWindow("minute", 2, 60),
        RateLimitWindow("day", 10, 86400),
    ],
}

_memory_store: dict[str, tuple[int, float]] = {}


def _enabled() -> bool:
    return os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


def _upstash_config() -> tuple[str, str, bool]:
    url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip().strip("'\"").rstrip("/")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip().strip("'\"")
    return url, token, bool(url and token)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def client_identifier_from_headers(raw_identity: str | None) -> str:
    """Hash whatever identity we were handed — ideally the authenticated
    X-User-Id, falling back to the first hop of X-Forwarded-For if a caller
    somehow lacks one."""
    forwarded_ips = str(raw_identity or "").split(",")
    raw = forwarded_ips[0].strip() if forwarded_ips and forwarded_ips[0] else "unknown"
    return _hash(raw or "unknown")


def _window_key(group: str, identity: str, window: RateLimitWindow, now_seconds: int) -> str:
    bucket = now_seconds // window.seconds
    return f"rl:{group}:{identity}:{window.name}:{bucket}"


def _seconds_until_reset(window: RateLimitWindow, now_seconds: int) -> int:
    next_reset = ((now_seconds // window.seconds) + 1) * window.seconds
    return max(next_reset - now_seconds, 1)


async def _read_memory_window(group: str, identity: str, window: RateLimitWindow, now_seconds: int) -> tuple[int, int, RateLimitWindow]:
    key = _window_key(group, identity, window, now_seconds)
    reset_seconds = _seconds_until_reset(window, now_seconds)
    now_monotonic = time.monotonic()
    count, expires_at = _memory_store.get(key, (0, 0.0))
    if expires_at <= now_monotonic:
        count = 0
    count += 1
    _memory_store[key] = (count, now_monotonic + reset_seconds)
    return count, reset_seconds, window


async def _read_upstash_window(group: str, identity: str, window: RateLimitWindow, now_seconds: int) -> tuple[int, int, RateLimitWindow]:
    url, token, _configured = _upstash_config()
    key = _window_key(group, identity, window, now_seconds)
    reset_seconds = _seconds_until_reset(window, now_seconds)
    async with httpx.AsyncClient(timeout=3.0) as client:
        response = await client.post(
            f"{url}/pipeline",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            json=[
                ["INCR", key],
                ["EXPIRE", key, reset_seconds + 5],
            ],
        )
        response.raise_for_status()
        payload: Any = response.json()
    count = int((payload or [{}])[0].get("result") or 0)
    return count, reset_seconds, window


async def check_rate_limit(group: str, identity: str, *, now_seconds: int | None = None) -> RateLimitResult:
    windows = RATE_LIMIT_GROUPS.get(group)
    if not _enabled() or not windows:
        return RateLimitResult(True, True, 0, 0, 0, 0)

    _url, _token, configured = _upstash_config()
    current_seconds = now_seconds if now_seconds is not None else int(time.time())

    try:
        reads = [
            await (
                _read_upstash_window(group, identity, window, current_seconds)
                if configured
                else _read_memory_window(group, identity, window, current_seconds)
            )
            for window in windows
        ]
    except Exception:
        # If Upstash is unreachable, fail closed for this expensive, LLM-backed
        # endpoint rather than letting requests through unmetered.
        return RateLimitResult(False, True, windows[0].limit, 0, 60, 60)

    most_limited = min(reads, key=lambda item: item[2].limit - item[0])
    blocked = [item for item in reads if item[0] > item[2].limit]
    allowed = not blocked
    retry_after = max((item[1] for item in blocked), default=0)

    count, reset_seconds, window = most_limited
    return RateLimitResult(
        allowed=allowed,
        configured=True,
        limit=window.limit,
        remaining=max(window.limit - count, 0),
        reset_seconds=reset_seconds,
        retry_after_seconds=retry_after,
    )


def rate_limit_headers(result: RateLimitResult) -> dict[str, str]:
    headers = {
        "X-RateLimit-Limit": str(result.limit),
        "X-RateLimit-Remaining": str(result.remaining),
        "X-RateLimit-Reset": str(result.reset_seconds),
    }
    if not result.allowed:
        headers["Retry-After"] = str(result.retry_after_seconds)
    return headers
