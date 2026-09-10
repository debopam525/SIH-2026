from __future__ import annotations

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.db import create_all
from app.core.logging import configure_logging, get_logger

log = get_logger("app")


@asynccontextmanager
async def lifespan(_: FastAPI):
    configure_logging()
    if settings.is_sqlite:
        create_all()  # dev / demo convenience; prod uses `alembic upgrade head`
    log.info("startup", env=settings.env, db=settings.database_url.split("://")[0])
    yield
    log.info("shutdown")


app = FastAPI(
    title="ECDAT API",
    version="0.1.0",
    description="Enterprise Cryptographic Discovery & Analysis Tool",
    lifespan=lifespan,
    openapi_url="/api/v1/openapi.json",
    docs_url="/docs",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_logger(request: Request, call_next):
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        method=request.method, path=request.url.path,
    )
    t0 = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log.exception("request.error")
        raise
    dt = round((time.perf_counter() - t0) * 1000, 1)
    log.info("request", status=response.status_code, ms=dt)
    response.headers["X-Response-Time-ms"] = str(dt)
    return response


@app.exception_handler(Exception)
async def unhandled(_: Request, exc: Exception):
    log.exception("unhandled")
    return JSONResponse(status_code=500, content={"detail": "Internal server error", "error": repr(exc)})


@app.get("/health", tags=["meta"])
def health() -> dict:
    return {"status": "ok", "service": "ecdat", "version": "0.1.0"}


@app.get("/api/v1/meta", tags=["meta"])
def meta() -> dict:
    return {
        "name": "ECDAT",
        "version": "0.1.0",
        "crqc_horizon_years_default": settings.crqc_horizon_years,
        "scan_types": ["source", "dependency", "config", "binary", "container"],
        "report_types": [
            "inventory", "algorithms", "vulnerability", "exposure", "recommendations",
            "migration_roadmap", "executive_summary", "full",
        ],
    }


app.include_router(api_router)
