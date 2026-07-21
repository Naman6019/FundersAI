import asyncio

from starlette.requests import Request
from starlette.responses import JSONResponse


def _run(coro):
    return asyncio.run(coro)


def _use_memory_limiter(monkeypatch):
    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("NODE_ENV", raising=False)
    monkeypatch.delenv("RENDER", raising=False)
    monkeypatch.delenv("RENDER_SERVICE_ID", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)


def test_chat_rate_limit_blocks_after_minute_bucket(monkeypatch):
    from app.services import rate_limit

    _use_memory_limiter(monkeypatch)
    rate_limit.reset_rate_limit_memory_for_tests()

    for _ in range(10):
        result = _run(rate_limit.check_rate_limit("chat", "client-a", now_seconds=1))
        assert result.allowed is True

    blocked = _run(rate_limit.check_rate_limit("chat", "client-a", now_seconds=1))
    assert blocked.allowed is False
    assert blocked.retry_after_seconds == 59

    headers = rate_limit.rate_limit_headers(blocked)
    assert headers["Retry-After"] == "59"
    assert headers["X-RateLimit-Limit"] == "10"
    assert headers["X-RateLimit-Remaining"] == "0"


def test_rate_limit_groups_are_separate(monkeypatch):
    from app.services import rate_limit

    _use_memory_limiter(monkeypatch)
    rate_limit.reset_rate_limit_memory_for_tests()

    for _ in range(11):
        _run(rate_limit.check_rate_limit("chat", "client-b", now_seconds=1))

    quant = _run(rate_limit.check_rate_limit("quant", "client-b", now_seconds=1))
    assert quant.allowed is True
    assert quant.remaining == 59


def test_production_without_upstash_fails_closed(monkeypatch):
    from app.services import rate_limit

    monkeypatch.setenv("RATE_LIMIT_ENABLED", "true")
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("UPSTASH_REDIS_REST_URL", raising=False)
    monkeypatch.delenv("UPSTASH_REDIS_REST_TOKEN", raising=False)
    rate_limit.reset_rate_limit_memory_for_tests()

    result = _run(rate_limit.check_rate_limit("search", "client-c", now_seconds=1))
    assert result.allowed is False
    assert result.configured is False
    assert result.retry_after_seconds == 60


def test_backend_health_route_is_not_rate_limited():
    from app import main as app_main

    assert app_main._rate_limit_group_for_request("/health", "GET") is None
    assert app_main._rate_limit_group_for_request("/", "GET") is None
    assert app_main._rate_limit_group_for_request("/api/chat", "POST") == "chat"
    assert app_main._rate_limit_group_for_request("/api/quant/stocks/compare", "GET") == "quant"
    assert app_main._rate_limit_group_for_request("/api/provider/indianapi/stocks/search", "GET") == "quant"
    assert app_main._rate_limit_group_for_request("/api/mf/122639", "GET") == "mf-detail"
    assert app_main._rate_limit_group_for_request("/api/funds/category", "GET") == "category-funds"
    assert app_main._rate_limit_group_for_request("/api/funds/category/compare", "POST") == "category-funds"
    assert app_main._rate_limit_group_for_request("/api/funds/research/search", "POST") == "fund-research"
    assert app_main._rate_limit_group_for_request("/api/funds/research/answer", "POST") == "fund-research"
    assert app_main._rate_limit_group_for_request("/api/trigger-fetch", "GET") == "cron-sync-mf"


def _request(path: str, method: str = "GET") -> Request:
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 1234),
            "scheme": "https",
            "server": ("testserver", 443),
            "query_string": b"",
        }
    )


def test_read_only_groups_fail_open_when_rate_limit_backend_raises(monkeypatch):
    from app import main as app_main

    async def unavailable(*_args, **_kwargs):
        raise TimeoutError("upstash timeout")

    async def downstream(_request):
        return JSONResponse({"ok": True}, status_code=200)

    monkeypatch.setattr(app_main, "check_rate_limit", unavailable)

    for path in (
        "/api/quant/stocks/NIFTY/price-history",
        "/api/mf/118955",
        "/api/funds/category",
        "/api/data-health",
    ):
        response = _run(app_main.rate_limit_middleware(_request(path), downstream))
        assert response.status_code == 200


def test_sensitive_groups_fail_closed_when_rate_limit_backend_raises(monkeypatch):
    from app import main as app_main

    async def unavailable(*_args, **_kwargs):
        raise TimeoutError("upstash timeout")

    async def downstream(_request):
        raise AssertionError("sensitive request must not reach the route")

    monkeypatch.setattr(app_main, "check_rate_limit", unavailable)

    for path, method in (
        ("/api/chat", "POST"),
        ("/api/funds/research/answer", "POST"),
        ("/api/trigger-fetch", "GET"),
        ("/api/admin/mf-documents/retry", "POST"),
    ):
        response = _run(app_main.rate_limit_middleware(_request(path, method), downstream))
        assert response.status_code == 503


def test_rate_limit_error_status_reads_http_status():
    from app import main as app_main

    response = type("Response", (), {"status_code": 401})()
    error = type("ProviderError", (Exception,), {"response": response})("unauthorized")

    assert app_main._rate_limit_error_status(error) == 401
    assert app_main._rate_limit_error_status(TimeoutError()) is None
