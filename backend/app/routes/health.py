from __future__ import annotations

from fastapi import APIRouter, Depends

from app.repositories.admin_ops_repository import AdminOpsRepository
from app.services.data_health_service import DataHealthService

router = APIRouter(tags=["health"])


def get_admin_ops_repository() -> AdminOpsRepository:
    return AdminOpsRepository()


def get_data_health_service(
    repository: AdminOpsRepository = Depends(get_admin_ops_repository),
) -> DataHealthService:
    return DataHealthService(repository)


@router.get("/")
def read_root():
    return {"message": "FundersAI API is running. Use /health for health checks."}


@router.get("/health")
@router.head("/health")
def health():
    return {"status": "ok"}


@router.get("/api/data-health")
def data_health(service: DataHealthService = Depends(get_data_health_service)):
    return service.get_data_health()
