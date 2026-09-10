from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.api.serializers import asset_to_detail, asset_to_out, evidence_to_out
from app.cbom.export import to_csv, to_cyclonedx
from app.core.db import get_db
from app.models.application import Application
from app.models.asset import CryptographicAsset
from app.models.risk import RiskAssessment
from app.models.scan import Scan
from app.models.user import User
from app.schemas import AssetDetailOut, AssetListOut, EvidenceOut

router = APIRouter(tags=["assets"])

_RISK_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _latest_completed_scan_id(db: Session) -> str | None:
    return db.scalar(
        select(Scan.scan_id).where(Scan.status == "completed").order_by(Scan.created_at.desc()).limit(1)
    )


@router.get("/assets", response_model=AssetListOut)
def list_assets(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    scan_id: str | None = None,
    q: str | None = Query(None, description="substring match on algorithm / name / location"),
    algorithm_family: str | None = None,
    risk_category: str | None = None,
    quantum_status: str | None = None,
    confidence: str | None = None,
    app_id: str | None = None,
    source: str | None = None,
    sort: str = Query("risk", pattern="^(risk|algorithm|family|confidence|name)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
) -> AssetListOut:
    scan_id = scan_id or _latest_completed_scan_id(db)
    if not scan_id:
        return AssetListOut(items=[], total=0, page=page, page_size=page_size)

    stmt = (
        select(CryptographicAsset)
        .where(CryptographicAsset.scan_id == scan_id)
        .options(
            selectinload(CryptographicAsset.risk),
            selectinload(CryptographicAsset.recommendation),
            selectinload(CryptographicAsset.evidence),
            selectinload(CryptographicAsset.application),
        )
    )
    if algorithm_family:
        stmt = stmt.where(CryptographicAsset.algorithm_family == algorithm_family)
    if confidence:
        stmt = stmt.where(CryptographicAsset.detection_confidence == confidence)
    if app_id:
        stmt = stmt.where(CryptographicAsset.app_id == app_id)
    if risk_category:
        stmt = stmt.join(RiskAssessment).where(RiskAssessment.risk_category == risk_category)

    rows = list(db.scalars(stmt).all())

    if q:
        ql = q.lower()
        rows = [
            r for r in rows
            if ql in r.algorithm.lower()
            or ql in r.asset_name.lower()
            or ql in (r.usage_location or "").lower()
            or ql in (r.library_dependency or "").lower()
        ]
    if source:
        rows = [r for r in rows if source in (r.sources or [])]

    outs = [asset_to_out(r) for r in rows]
    if quantum_status:
        outs = [o for o in outs if o.quantum_status == quantum_status]

    if sort == "risk":
        outs.sort(key=lambda o: (_RISK_ORDER.get(o.risk_category or "", 0), o.weighted_score or 0),
                  reverse=True)
    elif sort == "algorithm":
        outs.sort(key=lambda o: o.algorithm)
    elif sort == "family":
        outs.sort(key=lambda o: o.algorithm_family)
    elif sort == "confidence":
        outs.sort(key=lambda o: o.detection_confidence)
    else:
        outs.sort(key=lambda o: o.asset_name)

    total = len(outs)
    start = (page - 1) * page_size
    return AssetListOut(
        items=outs[start:start + page_size], total=total, page=page, page_size=page_size
    )


@router.get("/assets/{asset_id}", response_model=AssetDetailOut)
def get_asset(asset_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> AssetDetailOut:
    a = db.get(CryptographicAsset, asset_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found")
    return asset_to_detail(a)


@router.get("/assets/{asset_id}/evidence", response_model=list[EvidenceOut])
def get_evidence(asset_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[EvidenceOut]:
    a = db.get(CryptographicAsset, asset_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found")
    return [evidence_to_out(e) for e in a.evidence]


@router.get("/cbom/export")
def export_cbom(
    format: str = Query("json", pattern="^(json|csv)$"),
    scan_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    scan_id = scan_id or _latest_completed_scan_id(db)
    if not scan_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No completed scan to export")
    if format == "csv":
        return Response(
            to_csv(db, scan_id),
            media_type="text/csv",
            headers={"Content-Disposition": f'attachment; filename="cbom_{scan_id}.csv"'},
        )
    return to_cyclonedx(db, scan_id)


@router.get("/assets/meta/facets")
def asset_facets(
    scan_id: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    """Distinct values for building filter dropdowns in the UI."""
    scan_id = scan_id or _latest_completed_scan_id(db)
    if not scan_id:
        return {"algorithm_family": [], "confidence": [], "source": [], "applications": []}
    fams = db.scalars(
        select(CryptographicAsset.algorithm_family)
        .where(CryptographicAsset.scan_id == scan_id).distinct()
    ).all()
    confs = db.scalars(
        select(CryptographicAsset.detection_confidence)
        .where(CryptographicAsset.scan_id == scan_id).distinct()
    ).all()
    apps = db.execute(
        select(Application.app_id, Application.name)
        .join(CryptographicAsset, CryptographicAsset.app_id == Application.app_id)
        .where(CryptographicAsset.scan_id == scan_id).distinct()
    ).all()
    return {
        "algorithm_family": sorted(f for f in fams if f),
        "confidence": sorted(c for c in confs if c),
        "source": ["source", "dependency", "config", "binary", "container"],
        "quantum_status": ["quantum-vulnerable", "quantum-weakened", "quantum-safe",
                           "broken-classical", "unknown"],
        "risk_category": ["critical", "high", "medium", "low"],
        "applications": [{"app_id": a, "name": n} for a, n in apps],
    }
