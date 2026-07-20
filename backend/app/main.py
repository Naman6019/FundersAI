from __future__ import annotations

import logging
import os
import sys

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.exceptions import AppServiceError
from app.routes.admin import router as admin_router
from app.routes.chat import router as chat_router
from app.routes.funds import router as funds_router
from app.routes.health import router as health_router
from app.routes.indianapi import router as indianapi_router
from app.routes.mf_ingestion import router as mf_ingestion_router
from app.routes.providers import router as providers_router
from app.routes.quant import router as quant_router
from app.services.rate_limit import (
    check_rate_limit,
    client_identifier_from_request,
    rate_limit_headers,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
load_dotenv(os.path.join(BASE_DIR, ".env"))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()


@app.exception_handler(AppServiceError)
async def service_exception_handler(_request: Request, exc: AppServiceError):
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled server error at %s: %s", request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal Server Error", "message": str(exc)},
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://marketmind.vercel.app",
        "https://fundersai.com",
        "https://www.fundersai.com",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _rate_limit_group_for_request(path: str, method: str) -> str | None:
    method = method.upper()
    if path == "/api/chat" and method == "POST":
        return "chat"
    if path.startswith("/api/quant/"):
        return "quant"
    if path.startswith("/api/provider/indianapi/"):
        return "quant"
    if path.startswith("/api/mf/"):
        return "mf-detail"
    if path.startswith("/api/funds/") and path.endswith("/similar"):
        return "mf-detail"
    if path.startswith("/api/funds/research"):
        return "fund-research"
    if path.startswith("/api/funds/category"):
        return "category-funds"
    if path == "/api/data-health":
        return "data-health"
    if path == "/api/trigger-fetch":
        return "cron-sync-mf"
    if path.startswith("/api/admin/mf-documents/") and method == "POST":
        return "admin-mutation"
    return None


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    group = _rate_limit_group_for_request(request.url.path, request.method)
    if group:
        identity_override = request.headers.get("x-admin-key") if group == "admin-mutation" else None
        identity = client_identifier_from_request(request, identity_override)
        try:
            result = await check_rate_limit(group, identity)
        except Exception as exc:
            logger.warning("event=rate_limit_check_failed path=%s reason=%s", request.url.path, exc)
            if group == "data-health":
                return await call_next(request)
            return JSONResponse(
                {"error": "rate_limit_unavailable", "retry_after_seconds": 60},
                status_code=503,
                headers={"Retry-After": "60"},
            )
        if not result.allowed:
            if group == "data-health" and not result.configured:
                logger.warning("event=rate_limit_unconfigured_bypassed path=%s", request.url.path)
                return await call_next(request)
            status_code = 429 if result.configured else 503
            error = "rate_limited" if result.configured else "rate_limit_unconfigured"
            return JSONResponse(
                {"error": error, "retry_after_seconds": result.retry_after_seconds},
                status_code=status_code,
                headers=rate_limit_headers(result),
            )

    return await call_next(request)


app.include_router(health_router)
app.include_router(admin_router)
app.include_router(chat_router)
app.include_router(funds_router)
app.include_router(providers_router)
app.include_router(quant_router)
app.include_router(indianapi_router)
app.include_router(mf_ingestion_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
