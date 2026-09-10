from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.analysis.pipeline import run_for_scan
from app.api.deps import get_current_user, require_cap
from app.core.db import get_db
from app.core.kb import risk_defaults
from app.core.runtime_settings import (
    get_crqc_horizon,
    get_crqc_note,
    get_risk_weights,
    set_crqc,
    set_risk_weights,
)
from app.models.scan import Scan
from app.models.user import User
from app.schemas import MoscaAssumption, RiskWeights

router = APIRouter(prefix="/settings", tags=["settings"])


def _rescore_all(db: Session) -> int:
    scans = db.scalars(select(Scan.scan_id).where(Scan.status == "completed")).all()
    for sid in scans:
        run_for_scan(db, sid)
    return len(scans)


@router.get("/risk-weights", response_model=RiskWeights)
def read_risk_weights(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> RiskWeights:
    return RiskWeights(weights=get_risk_weights(db))


@router.put("/risk-weights", response_model=RiskWeights)
def update_risk_weights(
    body: RiskWeights,
    db: Session = Depends(get_db),
    _: User = Depends(require_cap("settings:write")),
) -> RiskWeights:
    weights = set_risk_weights(db, body.weights)
    _rescore_all(db)
    db.commit()
    return RiskWeights(weights=weights)


@router.get("/risk-weights/defaults")
def risk_weight_defaults(_: User = Depends(get_current_user)) -> dict:
    d = risk_defaults()
    return {"weights": d["weights"], "bands": d["bands"], "normalizers": d["normalizers"],
            "neutral_default": d["neutral_default"]}


@router.get("/mosca-assumption")
def read_mosca_assumption(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    return {"crqc_horizon_years": get_crqc_horizon(db), "note": get_crqc_note(db)}


@router.put("/mosca-assumption")
def update_mosca_assumption(
    body: MoscaAssumption,
    db: Session = Depends(get_db),
    _: User = Depends(require_cap("settings:write")),
) -> dict:
    set_crqc(db, body.crqc_horizon_years, body.note)
    scans = _rescore_all(db)
    db.commit()
    return {
        "crqc_horizon_years": get_crqc_horizon(db),
        "note": get_crqc_note(db),
        "rescored_scans": scans,
    }
