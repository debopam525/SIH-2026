from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import applications, assets, dashboard, migration, reports, scans, settings_routes
from app.api.v1.analysis_routes import mosca_router, rec_router, risk_router
from app.api.v1.auth import me_router
from app.api.v1.auth import router as auth_router

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth_router)
api_router.include_router(me_router)
api_router.include_router(scans.router)
api_router.include_router(assets.router)
api_router.include_router(applications.router)
api_router.include_router(risk_router)
api_router.include_router(mosca_router)
api_router.include_router(rec_router)
api_router.include_router(dashboard.router)
api_router.include_router(migration.router)
api_router.include_router(reports.router)
api_router.include_router(settings_routes.router)
