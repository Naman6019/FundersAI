import asyncio


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
    assert app_main._rate_limit_group_for_request("/api/trigger-fetch", "GET") == "cron-sync-mf"
