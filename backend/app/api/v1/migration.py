from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user, require_cap
from app.core.db import get_db
from app.models.asset import CryptographicAsset
from app.models.migration import MigrationStatus
from app.models.scan import Scan
from app.models.user import User
from app.schemas import MigrationUpdate

router = APIRouter(prefix="/migration", tags=["migration"])
_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


def _latest_scan(db: Session) -> str | None:
    return db.scalar(
        select(Scan.scan_id).where(Scan.status == "completed").order_by(Scan.created_at.desc()).limit(1)
    )


@router.get("/board")
def board(
    scan_id: str | None = None,
    owner: str | None = None,
    business_unit: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    scan_id = scan_id or _latest_scan(db)
    if not scan_id:
        return {"scan_id": None, "columns": {}, "by_application": []}
    assets = db.scalars(
        select(CryptographicAsset)
        .where(CryptographicAsset.scan_id == scan_id)
        .options(
            selectinload(CryptographicAsset.migration),
            selectinload(CryptographicAsset.recommendation),
            selectinload(CryptographicAsset.risk),
            selectinload(CryptographicAsset.application),
        )
    ).all()

    columns: dict[str, list] = {"critical": [], "high": [], "medium": [], "low": []}
    app_roll: dict[str, dict] = {}
    for a in assets:
        m = a.migration
        prio = (m.priority if m else None) or "low"
        if a.application:
            if owner and a.application.owner != owner:
                continue
            if business_unit and a.application.business_unit != business_unit:
                continue
        card = {
            "asset_id": a.asset_id,
            "asset_name": a.asset_name,
            "algorithm": a.algorithm,
            "application": a.application.name if a.application else None,
            "priority": prio,
            "status": m.status if m else "not_started",
            "readiness": m.readiness if m else 0,
            "owner": m.owner if m else (a.application.owner if a.application else None),
            "recommended": a.recommendation.candidate_algorithm if a.recommendation else None,
            "recommendation_type": a.recommendation.recommendation_type if a.recommendation else None,
            "planned_target_date": m.planned_target_date.isoformat() if m and m.planned_target_date else None,
        }
        columns.setdefault(prio, []).append(card)
        key = card["application"] or "(unassigned)"
        r = app_roll.setdefault(key, {"application": key, "total": 0, "done": 0, "in_progress": 0})
        r["total"] += 1
        if card["status"] == "done":
            r["done"] += 1
        elif card["status"] == "in_progress":
            r["in_progress"] += 1

    for col in columns.values():
        col.sort(key=lambda c: c["readiness"])
    rollup = sorted(app_roll.values(), key=lambda r: r["total"], reverse=True)
    for r in rollup:
        r["progress_pct"] = round(100 * r["done"] / r["total"]) if r["total"] else 0
    return {"scan_id": scan_id, "columns": columns, "by_application": rollup}


@router.put("/{asset_id}")
def update_migration(
    asset_id: str,
    body: MigrationUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_cap("report:generate")),
) -> dict:
    a = db.get(CryptographicAsset, asset_id)
    if not a:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Asset not found")
    m = a.migration or MigrationStatus(asset_id=asset_id)
    if not a.migration:
        db.add(m)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(m, field, value)
    m.last_reviewed_at = datetime.now(UTC)
    if body.status == "done" and body.readiness is None:
        m.readiness = 100
    db.commit()
    return {
        "asset_id": asset_id,
        "status": m.status,
        "readiness": m.readiness,
        "owner": m.owner,
        "priority": m.priority,
        "planned_target_date": m.planned_target_date.isoformat() if m.planned_target_date else None,
        "last_reviewed_at": m.last_reviewed_at.isoformat(),
    }
