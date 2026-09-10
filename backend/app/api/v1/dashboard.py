from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.api.deps import get_current_user
from app.api.serializers import asset_to_out, scan_to_out
from app.core.db import get_db
from app.models.application import Application
from app.models.asset import CryptographicAsset
from app.models.scan import Scan
from app.models.user import User
from app.schemas import DashboardMetrics

router = APIRouter(prefix="/dashboard", tags=["dashboard"])
_RISK_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1}


@router.get("/metrics", response_model=DashboardMetrics)
def metrics(
    scan_id: str | None = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> DashboardMetrics:
    scan_id = scan_id or db.scalar(
        select(Scan.scan_id).where(Scan.status == "completed").order_by(Scan.created_at.desc()).limit(1)
    )
    recent = db.scalars(select(Scan).order_by(Scan.created_at.desc()).limit(8)).all()

    if not scan_id:
        return DashboardMetrics(
            scan_id=None, generated_at=datetime.now(UTC),
            totals={"assets": 0, "vulnerable": 0, "critical": 0, "apps_at_risk": 0,
                    "already_pqc": 0, "applications": 0},
            quantum_distribution={}, risk_distribution={}, algorithm_breakdown=[],
            family_breakdown=[], migration_priority={},
            recent_scans=[scan_to_out(s) for s in recent], top_risky_assets=[],
            confidence_distribution={},
        )

    assets = db.scalars(
        select(CryptographicAsset)
        .where(CryptographicAsset.scan_id == scan_id)
        .options(
            selectinload(CryptographicAsset.risk),
            selectinload(CryptographicAsset.recommendation),
            selectinload(CryptographicAsset.evidence),
            selectinload(CryptographicAsset.application),
        )
    ).all()

    outs = [asset_to_out(a) for a in assets]

    quantum_dist = Counter(o.quantum_status for o in outs)
    risk_dist = Counter(o.risk_category for o in outs if o.risk_category)
    conf_dist = Counter(o.detection_confidence for o in outs)
    algo_count = Counter(o.algorithm for o in outs)
    fam_count = Counter(o.algorithm_family for o in outs)
    mig_prio = Counter(o.migration_priority for o in outs if o.migration_priority)

    vulnerable = sum(1 for o in outs if o.quantum_status in ("quantum-vulnerable", "broken-classical"))
    critical = risk_dist.get("critical", 0)
    already_pqc = sum(1 for o in outs if o.algorithm_family in ("pqc-kem", "pqc-signature"))

    apps_at_risk = {
        o.application_name for o in outs
        if o.application_name and o.risk_category in ("critical", "high")
    }
    app_total = len(db.scalars(select(Application.app_id)).all())

    top = sorted(
        outs,
        key=lambda o: (_RISK_ORDER.get(o.risk_category or "", 0), o.weighted_score or 0),
        reverse=True,
    )[:10]

    def _bd(counter: Counter) -> list[dict]:
        return [{"name": k, "count": v} for k, v in counter.most_common()]

    return DashboardMetrics(
        scan_id=scan_id,
        generated_at=datetime.now(UTC),
        totals={
            "assets": len(outs),
            "vulnerable": vulnerable,
            "critical": critical,
            "apps_at_risk": len(apps_at_risk),
            "already_pqc": already_pqc,
            "applications": app_total,
        },
        quantum_distribution=dict(quantum_dist),
        risk_distribution=dict(risk_dist),
        algorithm_breakdown=_bd(algo_count),
        family_breakdown=_bd(fam_count),
        migration_priority=dict(mig_prio),
        recent_scans=[scan_to_out(s) for s in recent],
        top_risky_assets=top,
        confidence_distribution=dict(conf_dist),
    )
