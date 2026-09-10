from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.analysis.pipeline import analyze_asset
from app.api.deps import get_current_user, require_cap
from app.api.serializers import asset_to_out
from app.core.db import get_db
from app.models.application import Application
from app.models.asset import CryptographicAsset
from app.models.user import User
from app.schemas import ApplicationOut, ApplicationUpdate

router = APIRouter(prefix="/applications", tags=["applications"])

_RISK_ORDER = {"critical": 4, "high": 3, "medium": 2, "low": 1, None: 0}
_VULN_STATUSES = {"quantum-vulnerable", "broken-classical"}


def _to_out(app: Application) -> ApplicationOut:
    assets = app.assets
    cats = [a.risk.risk_category if a.risk else None for a in assets]
    max_cat = max(cats, key=lambda c: _RISK_ORDER.get(c, 0)) if cats else None
    vulnerable = sum(
        1 for a in assets
        if a.risk and a.risk.risk_category in ("critical", "high")
    )
    exposure = round(
        sum(_RISK_ORDER.get(a.risk.risk_category, 0) if a.risk else 0 for a in assets)
        * (app.business_criticality or 3) / 3,
        2,
    )
    return ApplicationOut(
        app_id=app.app_id,
        name=app.name,
        owner=app.owner,
        business_unit=app.business_unit,
        business_criticality=app.business_criticality,
        system_lifetime_years=app.system_lifetime_years,
        data_sensitivity=app.data_sensitivity,
        data_lifetime_years=app.data_lifetime_years,
        description=app.description,
        asset_count=len(assets),
        vulnerable_count=vulnerable,
        max_risk_category=max_cat,
        exposure_score=exposure,
    )


def _load(db: Session) -> list[Application]:
    return list(
        db.scalars(
            select(Application).options(
                selectinload(Application.assets).selectinload(CryptographicAsset.risk)
            )
        ).all()
    )


@router.get("", response_model=list[ApplicationOut])
def list_applications(db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> list[ApplicationOut]:
    apps = _load(db)
    outs = [_to_out(a) for a in apps]
    outs.sort(key=lambda o: o.exposure_score, reverse=True)
    return outs


@router.get("/{app_id}")
def get_application(app_id: str, db: Session = Depends(get_db), _: User = Depends(get_current_user)) -> dict:
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    assets = sorted(
        app.assets,
        key=lambda a: (_RISK_ORDER.get(a.risk.risk_category if a.risk else None, 0),
                       a.risk.weighted_score if a.risk else 0),
        reverse=True,
    )
    return {
        "application": _to_out(app).model_dump(),
        "assets": [asset_to_out(a).model_dump() for a in assets],
    }


@router.put("/{app_id}", response_model=ApplicationOut)
def update_application(
    app_id: str,
    body: ApplicationUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_cap("settings:write")),
) -> ApplicationOut:
    app = db.get(Application, app_id)
    if not app:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Application not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(app, field, value)
    db.flush()
    # Application metadata feeds the risk + mosca engines -> re-run for its assets.
    for a in app.assets:
        analyze_asset(db, a)
    db.commit()
    db.refresh(app)
    return _to_out(app)
