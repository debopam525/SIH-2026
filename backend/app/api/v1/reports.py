from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_cap
from app.core.config import settings
from app.core.db import get_db
from app.models.report import Report
from app.models.scan import Scan
from app.models.user import User
from app.reports.generator import build_report, render_csv, render_json, render_pdf
from app.schemas import ReportOut, ReportRequest

router = APIRouter(prefix="/reports", tags=["reports"])

_MEDIA = {"json": "application/json", "csv": "text/csv", "pdf": "application/pdf",
          "html": "text/html"}


def _to_out(r: Report) -> ReportOut:
    return ReportOut(
        report_id=r.report_id, type=r.type, format=r.format, scan_id=r.scan_id,
        created_at=r.created_at, size_bytes=r.size_bytes, filename=r.filename,
    )


@router.post("/generate", response_model=ReportOut, status_code=status.HTTP_201_CREATED)
def generate_report(
    body: ReportRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_cap("report:generate")),
) -> ReportOut:
    scan_id = body.scan_id or db.scalar(
        select(Scan.scan_id).where(Scan.status == "completed").order_by(Scan.created_at.desc()).limit(1)
    )
    if not scan_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No completed scan available")

    report = build_report(db, body.type, scan_id)
    fmt = body.format
    if fmt == "json":
        payload, fmt = render_json(report), "json"
    elif fmt == "csv":
        payload, fmt = render_csv(report), "csv"
    else:
        payload, fmt = render_pdf(report)

    ts = report["meta"]["generated_at"].replace(":", "").replace("-", "")[:15]
    filename = f"ecdat_{body.type}_{scan_id}_{ts}.{fmt}"
    out_path = settings.reports_dir / filename
    out_path.write_bytes(payload)

    row = Report(
        type=body.type, format=fmt, scan_id=scan_id, filename=filename,
        path=str(out_path), size_bytes=len(payload), created_by=user.user_id,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _to_out(row)


@router.get("", response_model=list[ReportOut])
def list_reports(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[ReportOut]:
    rows = db.scalars(select(Report).order_by(Report.created_at.desc()).limit(100)).all()
    return [_to_out(r) for r in rows]


@router.get("/types")
def report_types(_: User = Depends(get_current_user)) -> dict:
    return {
        "types": [
            {"id": "inventory", "name": "Cryptographic Inventory"},
            {"id": "algorithms", "name": "Algorithm / Version / Protocol Report"},
            {"id": "vulnerability", "name": "Quantum Vulnerability & Risk Analysis"},
            {"id": "exposure", "name": "Sensitive-Data Exposure Analysis"},
            {"id": "recommendations", "name": "PQC Recommendation Report"},
            {"id": "migration_roadmap", "name": "Migration Priority Roadmap"},
            {"id": "executive_summary", "name": "Executive Summary"},
            {"id": "full", "name": "Full Combined Report"},
        ],
        "formats": ["json", "csv", "pdf"],
        "note": "PDF requires the optional 'weasyprint' dependency; otherwise an HTML file is produced.",
    }


@router.get("/{report_id}/download")
def download_report(
    report_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)
) -> FileResponse:
    r = db.get(Report, report_id)
    if not r or not Path(r.path).exists():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Report not found")
    return FileResponse(r.path, media_type=_MEDIA.get(r.format, "application/octet-stream"),
                        filename=r.filename)
