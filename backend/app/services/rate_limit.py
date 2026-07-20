from __future__ import annotations

import hashlib
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx
from starlette.requests import Request


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


RATE_LIMIT_GROUPS: dict[str, list[RateLimitWindow]] = {
    "chat": [
        RateLimitWindow("minute", 10, 60),
    ],
    "quant": [
        RateLimitWindow("minute", 60, 60),
        RateLimitWindow("day", 1000, 86400),
    ],
    "mf-detail": [
        RateLimitWindow("minute", 60, 60),
        RateLimitWindow("day", 1000, 86400),
    ],
    "category-funds": [
        RateLimitWindow("minute", 60, 60),
        RateLimitWindow("day", 1000, 86400),
    ],
    "fund-research": [
        RateLimitWindow("minute", 10, 60),
        RateLimitWindow("day", 200, 86400),
    ],
    "search": [
        RateLimitWindow("minute", 30, 60),
        RateLimitWindow("day", 500, 86400),
    ],
    "data-health": [
        RateLimitWindow("minute", 30, 60),
        RateLimitWindow("day", 500, 86400),
    ],
    "cron-sync-mf": [
        RateLimitWindow("hour", 2, 3600),
    ],
    "admin-mutation": [
        RateLimitWindow("minute", 20, 60),
    ],
}

_memory_store: dict[str, tuple[int, float]] = {}


def _enabled() -> bool:
    return os.getenv("RATE_LIMIT_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}


def _upstash_config() -> tuple[str, str, bool]:
    url = os.getenv("UPSTASH_REDIS_REST_URL", "").strip().rstrip("/")
    token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "").strip()
    return url, token, bool(url and token)


def _is_production() -> bool:
    env_values = [
        os.getenv("APP_ENV", ""),
        os.getenv("ENVIRONMENT", ""),
        os.getenv("NODE_ENV", ""),
        os.getenv("RENDER_ENV", ""),
    ]
    return any(value.strip().lower() == "production" for value in env_values) or bool(
        os.getenv("RENDER") or os.getenv("RENDER_SERVICE_ID")
    )


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:24]


def client_identifier_from_request(request: Request, override: str | None = None) -> str:
    if override:
        return _hash(str(override))
        
    cf_ip = str(request.headers.get("cf-connecting-ip") or "").strip()
    real_ip = str(request.headers.get("x-real-ip") or "").strip()
    
    forwarded_ips = str(request.headers.get("x-forwarded-for") or "").split(",")
    forwarded = forwarded_ips[-1].strip() if forwarded_ips and forwarded_ips[0] else ""

    raw = (
        cf_ip
        or real_ip
        or forwarded
        or (request.client.host if request.client else "")
        or "unknown"
    )
    return _hash(raw)


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


async def check_rate_limit(
    group: str,
    identity: str,
    *,
    now_seconds: int | None = None,
) -> RateLimitResult:
    windows = RATE_LIMIT_GROUPS.get(group)
    if not _enabled() or not windows:
        return RateLimitResult(True, True, 0, 0, 0, 0)

    _url, _token, configured = _upstash_config()
    use_memory = not configured and not _is_production()
    if not configured and not use_memory:
        return RateLimitResult(False, False, 0, 0, 60, 60)

    current_seconds = now_seconds if now_seconds is not None else int(time.time())
    reads = [
        await (
            _read_memory_window(group, identity, window, current_seconds)
            if use_memory
            else _read_upstash_window(group, identity, window, current_seconds)
        )
        for window in windows
    ]
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


def reset_rate_limit_memory_for_tests() -> None:
    _memory_store.clear()
