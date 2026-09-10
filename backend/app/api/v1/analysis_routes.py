"""/risk, /mosca, /recommendations endpoints (grouped; all read from persisted assessments)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.api.serializers import _mosca_dict, _rec_dict, _risk_dict
from app.core.db import get_db
from app.core.runtime_settings import get_crqc_horizon, get_crqc_note
from app.models.asset import CryptographicAsset
from app.models.risk import RiskAssessment
from app.models.scan import Scan
from app.models.user import User

risk_router = APIRouter(prefix="/risk", tags=["risk"])
mosca_router = APIRouter(prefix="/mosca", tags=["mosca"])
rec_router = APIRouter(prefix="/recommendations", tags=["recommendations"])


def _latest_scan(db: Session) -> str | None:
    return db.scalar(
        select(Scan.scan_id).where(Scan.status == "completed").order_by(Scan.created_at.desc()).limit(1)
    )


@risk_router.get("/summary")
def risk_summary(
    scan_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    scan_id = scan_id or _latest_scan(db)
    if not scan_id:
        return {"scan_id": None, "by_category": {}, "total_assessed": 0, "average_score": 0}
    rows = db.execute(
        select(RiskAssessment.risk_category, func.count(), func.avg(RiskAssessment.weighted_score))
        .join(CryptographicAsset, CryptographicAsset.asset_id == RiskAssessment.asset_id)
        .where(CryptographicAsset.scan_id == scan_id)
        .group_by(RiskAssessment.risk_category)
    ).all()
    by_cat = {c: {"count": n, "avg_score": round(avg or 0, 3)} for c, n, avg in rows}
    total = sum(v["count"] for v in by_cat.values())
    overall = db.scalar(
        select(func.avg(RiskAssessment.weighted_score))
        .join(CryptographicAsset, CryptographicAsset.asset_id == RiskAssessment.asset_id)
        .where(CryptographicAsset.scan_id == scan_id)
    )
    return {
        "scan_id": scan_id,
        "by_category": by_cat,
        "total_assessed": total,
        "average_score": round(overall or 0, 3),
    }


@risk_router.get("/{asset_id}")
def get_risk(asset_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    a = _asset(db, asset_id)
    if not a.risk:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No risk assessment for this asset")
    d = _risk_dict(a)
    d["asset_id"] = a.asset_id
    d["asset_name"] = a.asset_name
    return d


@mosca_router.get("/{asset_id}")
def get_mosca(asset_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    a = _asset(db, asset_id)
    if not a.mosca:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No Mosca assessment for this asset")
    d = _mosca_dict(a)
    d["asset_id"] = a.asset_id
    d["crqc_horizon_years_current_setting"] = get_crqc_horizon(db)
    d["crqc_note"] = get_crqc_note(db)
    return d


@rec_router.get("")
def list_recommendations(
    scan_id: str | None = None,
    migration_priority: str | None = None,
    recommendation_type: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    limit: int = Query(200, ge=1, le=1000),
) -> dict:
    scan_id = scan_id or _latest_scan(db)
    if not scan_id:
        return {"scan_id": None, "items": []}
    rows = db.scalars(
        select(CryptographicAsset)
        .where(CryptographicAsset.scan_id == scan_id)
        .options(selectinload(CryptographicAsset.recommendation))
    ).all()
    items = []
    for a in rows:
        if not a.recommendation:
            continue
        if migration_priority and a.recommendation.migration_priority != migration_priority:
            continue
        if recommendation_type and a.recommendation.recommendation_type != recommendation_type:
            continue
        d = _rec_dict(a)
        d.update({"asset_id": a.asset_id, "asset_name": a.asset_name,
                  "algorithm_family": a.algorithm_family, "primitive": a.primitive})
        items.append(d)
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    items.sort(key=lambda d: order.get(d["migration_priority"], 0), reverse=True)
    return {"scan_id": scan_id, "items": items[:limit], "total": len(items)}


@rec_router.get("/{asset_id}")
def get_recommendation(asset_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    a = _asset(db, asset_id)
    if not a.recommendation:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No recommendation for this asset")
    d = _rec_dict(a)
    d.update({"asset_id": a.asset_id, "asset_name": a.asset_name})
    return d


def _asset(db: Session, asset_id: str) -> CryptographicAsset:
    a = db.get(CryptographicAsset, asset_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found")
    return a
