from __future__ import annotations

from fastapi import APIRouter, Depends, Header, Query

from app.repositories.admin_ops_repository import AdminOpsRepository
from app.services.admin_service import AdminDocumentReviewAction, AdminService

router = APIRouter(prefix="/api/admin", tags=["admin"])


def get_admin_ops_repository() -> AdminOpsRepository:
    return AdminOpsRepository()


def get_admin_service(repository: AdminOpsRepository = Depends(get_admin_ops_repository)) -> AdminService:
    return AdminService(repository)


@router.get("/ops-overview")
def admin_ops_overview(
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    service: AdminService = Depends(get_admin_service),
):
    return service.ops_overview(x_admin_key)


@router.post("/mf-documents/{document_id}/request-reparse")
def admin_request_mf_document_reparse(
    document_id: str,
    payload: AdminDocumentReviewAction | None = None,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    service: AdminService = Depends(get_admin_service),
):
    return service.request_reparse(document_id, payload, x_admin_key)


@router.post("/mf-documents/{document_id}/resolve")
def admin_resolve_mf_document_review(
    document_id: str,
    payload: AdminDocumentReviewAction | None = None,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    service: AdminService = Depends(get_admin_service),
):
    return service.resolve_review(document_id, payload, x_admin_key)


@router.post("/mf-documents/{document_id}/skip")
def admin_skip_mf_document_review(
    document_id: str,
    payload: AdminDocumentReviewAction | None = None,
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    service: AdminService = Depends(get_admin_service),
):
    return service.skip_review(document_id, payload, x_admin_key)


@router.get("/mf-resolver-debug")
def admin_mf_resolver_debug(
    query: str = Query(..., min_length=2),
    horizon: str = Query("3Y", pattern="^(1Y|3Y|5Y)$"),
    limit: int = Query(20, ge=5, le=50),
    x_admin_key: str | None = Header(default=None, alias="X-Admin-Key"),
    service: AdminService = Depends(get_admin_service),
):
    return service.resolver_debug(query, horizon, limit, x_admin_key)
