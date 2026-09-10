"""Run quantum -> risk -> mosca -> recommendation over a scan's assets and persist results.

Idempotent: re-running replaces prior assessments for the same assets. No randomness.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.analysis import mosca as mosca_engine
from app.analysis import quantum as quantum_engine
from app.analysis import recommendation as rec_engine
from app.analysis import risk as risk_engine
from app.analysis.risk import AppContext
from app.core.logging import get_logger
from app.core.runtime_settings import get_crqc_horizon, get_crqc_note, get_risk_weights
from app.models.application import Application
from app.models.asset import CryptographicAsset
from app.models.migration import MigrationStatus
from app.models.mosca import MoscaAssessment
from app.models.recommendation import Recommendation
from app.models.risk import RiskAssessment

log = get_logger("analysis.pipeline")

_PRIORITY_TO_READINESS = {"low": 10}


def _app_ctx(app: Application | None) -> AppContext:
    if not app:
        return AppContext()
    return AppContext(
        name=app.name,
        business_criticality=app.business_criticality,
        system_lifetime_years=app.system_lifetime_years,
        data_sensitivity=app.data_sensitivity,
        data_lifetime_years=app.data_lifetime_years,
    )


def analyze_asset(
    db: Session,
    asset: CryptographicAsset,
    *,
    weights: dict[str, float] | None = None,
    crqc_years: float | None = None,
    crqc_note: str = "",
) -> dict:
    weights = weights or get_risk_weights(db)
    crqc_years = crqc_years if crqc_years is not None else get_crqc_horizon(db)
    crqc_note = crqc_note or get_crqc_note(db)
    app = asset.application

    qv = quantum_engine.assess(
        algorithm=asset.algorithm,
        algorithm_family=asset.algorithm_family,
        key_size=asset.key_size,
        mode=asset.mode,
        protocol=asset.protocol,
        version=asset.version,
        primitive=asset.primitive,
    )

    rr = risk_engine.score(
        primitive=asset.primitive,
        algorithm_family=asset.algorithm_family,
        quantum=qv,
        app=_app_ctx(app),
        weights=weights,
    )

    mr = mosca_engine.assess(
        primitive=asset.primitive,
        crqc_horizon_years=crqc_years,
        data_lifetime_years=(app.data_lifetime_years if app and app.data_lifetime_years else None),
        crqc_note=crqc_note,
    )

    rec = rec_engine.recommend(
        algorithm=asset.algorithm,
        algorithm_family=asset.algorithm_family,
        primitive=asset.primitive,
        quantum=qv,
        risk_category=rr.risk_category,
        mosca_priority=mr.priority_result,
        business_criticality=(app.business_criticality if app else None),
    )

    # ---- upsert RiskAssessment
    ra = asset.risk or RiskAssessment(asset_id=asset.asset_id)
    ra.factors = rr.factors
    ra.weights = rr.weights
    ra.weighted_score = rr.weighted_score
    ra.risk_category = rr.risk_category
    ra.explanation = (
        rr.explanation
        + f"\n\nQuantum verdict: {qv.status} - {qv.explanation}"
    )
    if not asset.risk:
        db.add(ra)

    # ---- upsert MoscaAssessment
    ma = asset.mosca or MoscaAssessment(asset_id=asset.asset_id)
    ma.data_lifetime_years = mr.data_lifetime_years
    ma.migration_time_years = mr.migration_time_years
    ma.crqc_horizon_years = mr.crqc_horizon_years
    ma.sum_xy = mr.sum_xy
    ma.gap_years = mr.gap_years
    ma.exposed = mr.exposed
    ma.priority_result = mr.priority_result
    ma.assumptions_note = mr.assumptions_note
    if not asset.mosca:
        db.add(ma)

    # ---- upsert Recommendation
    rc = asset.recommendation or Recommendation(asset_id=asset.asset_id)
    rc.use_case = rec.use_case
    rc.current_algorithm = rec.current_algorithm
    rc.candidate_algorithm = rec.top.name
    rc.recommendation_type = rec.recommendation_type
    rc.score = rec.top.score
    rc.factor_scores = rec.top.factor_scores
    rc.rationale = rec.rationale
    rc.compatibility_notes = rec.compatibility_notes
    rc.performance_memory_notes = rec.performance_memory_notes
    rc.migration_priority = rec.migration_priority
    rc.alternatives = [
        {
            "name": alt.name,
            "recommendation_type": alt.recommendation_type,
            "score": alt.score,
            "factor_scores": alt.factor_scores,
            "notes": alt.notes,
            "migration_notes": alt.migration_notes,
        }
        for alt in rec.alternatives
    ]
    if not asset.recommendation:
        db.add(rc)

    # ---- upsert MigrationStatus (seed priority; keep human-set status/owner if present)
    ms = asset.migration or MigrationStatus(asset_id=asset.asset_id)
    ms.priority = rec.migration_priority
    if not asset.migration:
        ms.readiness = 100 if rec.recommendation_type == "no_change" else 0
        ms.status = "done" if rec.recommendation_type == "no_change" else "not_started"
        db.add(ms)

    return {
        "quantum": qv,
        "risk": rr,
        "mosca": mr,
        "recommendation": rec,
    }


def run_for_scan(db: Session, scan_id: str) -> dict:
    weights = get_risk_weights(db)
    crqc_years = get_crqc_horizon(db)
    crqc_note = get_crqc_note(db)

    assets = db.scalars(
        select(CryptographicAsset)
        .where(CryptographicAsset.scan_id == scan_id)
        .options(
            selectinload(CryptographicAsset.application),
            selectinload(CryptographicAsset.risk),
            selectinload(CryptographicAsset.mosca),
            selectinload(CryptographicAsset.recommendation),
            selectinload(CryptographicAsset.migration),
        )
    ).all()

    counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    quantum_counts: dict[str, int] = {}
    for asset in assets:
        out = analyze_asset(
            db, asset, weights=weights, crqc_years=crqc_years, crqc_note=crqc_note
        )
        counts[out["risk"].risk_category] += 1
        qs = out["quantum"].status
        quantum_counts[qs] = quantum_counts.get(qs, 0) + 1
    db.flush()
    log.info("analysis.complete", scan_id=scan_id, assets=len(assets), risk=counts)
    return {"assets": len(assets), "risk_breakdown": counts, "quantum_breakdown": quantum_counts}
