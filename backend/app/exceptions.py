from __future__ import annotations


class AppServiceError(Exception):
    status_code = 500
    detail = "service_error"

    def __init__(self, detail: str | None = None):
        super().__init__(detail or self.detail)
        self.detail = detail or self.detail


class EntityNotFoundError(AppServiceError):
    status_code = 404
    detail = "entity_not_found"


class BadRequestError(AppServiceError):
    status_code = 400
    detail = "bad_request"


class AmbiguousEntityError(AppServiceError):
    status_code = 400
    detail = "ambiguous_entity"


class UnsupportedEntityError(AppServiceError):
    status_code = 400
    detail = "unsupported_entity"


class UpstreamProviderError(AppServiceError):
    status_code = 503
    detail = "upstream_provider_error"


class DataUnavailableError(AppServiceError):
    status_code = 503
    detail = "data_unavailable"


class AuthorizationError(AppServiceError):
    status_code = 403
    detail = "authorization_required"


class ConflictError(AppServiceError):
    status_code = 409
    detail = "conflict"
