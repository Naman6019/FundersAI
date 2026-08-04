from types import SimpleNamespace

import pytest

from app.supabase_retry import execute_with_retry, is_transient_supabase_error


class ApiError(Exception):
    def __init__(self, payload=None, *, status_code=None):
        super().__init__(payload)
        self.status_code = status_code


@pytest.mark.parametrize("status", [502, 503, 504, 522, 525])
def test_retryable_http_statuses(status):
    assert is_transient_supabase_error(ApiError("temporary", status_code=status)) is True


def test_cloudflare_html_error_is_retryable():
    exc = ApiError({"message": "<title>funders.supabase.co | 522: Connection timed out</title>"})
    assert is_transient_supabase_error(exc) is True


@pytest.mark.parametrize("status", [400, 401, 403, 404, 409, 422])
def test_permanent_http_statuses_are_not_retryable(status):
    assert is_transient_supabase_error(ApiError("permanent", status_code=status)) is False


def test_postgres_validation_error_is_not_retryable():
    exc = ApiError({"code": "23505", "message": "duplicate key value violates unique constraint"})
    assert is_transient_supabase_error(exc) is False


@pytest.mark.parametrize("code", ["PGRST000", "PGRST001", "PGRST002", "PGRST003"])
def test_postgrest_errors_without_allowed_http_status_are_not_retryable(code):
    assert is_transient_supabase_error(ApiError({"code": code, "message": "database unavailable"})) is False


def test_execute_retries_with_bounded_exponential_backoff():
    attempts = []
    sleeps = []

    def operation():
        attempts.append(1)
        if len(attempts) < 3:
            raise ApiError("gateway timeout", status_code=504)
        return SimpleNamespace(data=[{"ok": True}])

    result = execute_with_retry(
        operation,
        max_attempts=3,
        base_delay_seconds=0.25,
        sleep=sleeps.append,
    )

    assert result.data == [{"ok": True}]
    assert len(attempts) == 3
    assert sleeps == [0.25, 0.5]


def test_execute_does_not_retry_permanent_error():
    attempts = []

    def operation():
        attempts.append(1)
        raise ApiError("conflict", status_code=409)

    with pytest.raises(ApiError):
        execute_with_retry(operation, max_attempts=3, sleep=lambda _seconds: None)

    assert len(attempts) == 1
