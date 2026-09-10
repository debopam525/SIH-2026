from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_cap
from app.api.serializers import scan_to_out
from app.cbom.diff import diff_scans
from app.core.db import get_db
from app.models.scan import Scan
from app.models.user import User
from app.scanners.runner import run_scan
from app.schemas import ScanCreate, ScanListOut, ScanOut

router = APIRouter(prefix="/scans", tags=["scans"])


@router.post("", response_model=ScanOut, status_code=status.HTTP_201_CREATED)
def create_scan(
    body: ScanCreate,
    bg: BackgroundTasks,
    db: Session = Depends(get_db),
    user: User = Depends(require_cap("scan:start")),
) -> ScanOut:
    scan = Scan(
        target=body.target,
        target_kind=body.target_kind,
        scan_types=body.scan_types,
        status="queued",
        stage="queued",
        created_by=user.user_id,
        notes=body.notes,
    )
    db.add(scan)
    db.commit()
    db.refresh(scan)
    bg.add_task(run_scan, scan.scan_id)
    return scan_to_out(scan)


@router.get("", response_model=ScanListOut)
def list_scans(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    status_filter: str | None = Query(None, alias="status"),
) -> ScanListOut:
    q = select(Scan).order_by(Scan.created_at.desc())
    cq = select(func.count(Scan.scan_id))
    if status_filter:
        q = q.where(Scan.status == status_filter)
        cq = cq.where(Scan.status == status_filter)
    total = db.scalar(cq) or 0
    rows = db.scalars(q.limit(limit).offset(offset)).all()
    return ScanListOut(items=[scan_to_out(s) for s in rows], total=total)


@router.get("/{scan_id}", response_model=ScanOut)
def get_scan(scan_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> ScanOut:
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    return scan_to_out(scan)


@router.post("/{scan_id}/cancel", response_model=ScanOut)
def cancel_scan(
    scan_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_cap("scan:cancel")),
) -> ScanOut:
    scan = db.get(Scan, scan_id)
    if not scan:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    if scan.status in ("completed", "failed", "cancelled"):
        raise HTTPException(status.HTTP_409_CONFLICT, f"Scan already {scan.status}")
    scan.cancel_requested = True
    db.commit()
    db.refresh(scan)
    return scan_to_out(scan)


@router.get("/{scan_id}/diff")
def scan_diff(
    scan_id: str,
    base_scan_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> dict:
    target = db.get(Scan, scan_id)
    if not target:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Scan not found")
    if base_scan_id is None:
        prev = db.scalars(
            select(Scan)
            .where(Scan.status == "completed", Scan.created_at < target.created_at)
            .order_by(Scan.created_at.desc())
            .limit(1)
        ).first()
        base_scan_id = prev.scan_id if prev else None
    d = diff_scans(db, scan_id, base_scan_id)
    return {
        "base_scan_id": d.base_scan_id,
        "target_scan_id": d.target_scan_id,
        "added": d.added,
        "removed": d.removed,
        "changed": d.changed,
        "unchanged_count": d.unchanged_count,
        "summary": {
            "added": len(d.added),
            "removed": len(d.removed),
            "changed": len(d.changed),
            "unchanged": d.unchanged_count,
        },
    }
