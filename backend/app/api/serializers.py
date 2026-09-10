"""ORM -> Pydantic serializers shared across routers."""
from __future__ import annotations

from app.analysis import quantum as quantum_engine
from app.models.asset import CryptographicAsset
from app.models.scan import Scan
from app.schemas import AssetDetailOut, AssetOut, EvidenceOut, ScanOut


def scan_to_out(s: Scan) -> ScanOut:
    return ScanOut(
        scan_id=s.scan_id,
        target=s.target,
        target_kind=s.target_kind,
        scan_types=s.scan_types or [],
        status=s.status,
        progress=s.progress,
        stage=s.stage,
        start_time=s.start_time,
        end_time=s.end_time,
        scanner_versions=s.scanner_versions or {},
        stats=s.stats or {},
        errors=s.errors or [],
        created_by=s.created_by,
        created_at=s.created_at,
    )


def _quantum_status(a: CryptographicAsset) -> str:
    v = quantum_engine.assess(
        algorithm=a.algorithm, algorithm_family=a.algorithm_family, key_size=a.key_size,
        mode=a.mode, protocol=a.protocol, version=a.version, primitive=a.primitive,
    )
    return v.status


def asset_to_out(a: CryptographicAsset) -> AssetOut:
    return AssetOut(
        asset_id=a.asset_id,
        scan_id=a.scan_id,
        app_id=a.app_id,
        application_name=a.application.name if a.application else None,
        asset_name=a.asset_name,
        algorithm=a.algorithm,
        algorithm_family=a.algorithm_family,
        primitive=a.primitive,
        version=a.version,
        key_size=a.key_size,
        mode=a.mode,
        protocol=a.protocol,
        library_dependency=a.library_dependency,
        usage_location=a.usage_location,
        asset_type=a.asset_type,
        sources=a.sources or [],
        detection_confidence=a.detection_confidence,
        risk_category=a.risk.risk_category if a.risk else None,
        weighted_score=a.risk.weighted_score if a.risk else None,
        quantum_status=_quantum_status(a),
        migration_priority=a.recommendation.migration_priority if a.recommendation else None,
        evidence_count=len(a.evidence),
    )


def evidence_to_out(e) -> EvidenceOut:  # noqa: ANN001
    return EvidenceOut(
        evidence_id=e.evidence_id,
        location_kind=e.location_kind,
        location=e.location,
        line_or_offset=e.line_or_offset,
        function_or_scope=e.function_or_scope,
        matched_indicator=e.matched_indicator,
        surrounding_context=e.surrounding_context,
        confidence=e.confidence,
        detector=e.detector,
        signature_id=e.signature_id,
    )


def _risk_dict(a: CryptographicAsset) -> dict | None:
    if not a.risk:
        return None
    return {
        "risk_category": a.risk.risk_category,
        "weighted_score": a.risk.weighted_score,
        "factors": a.risk.factors,
        "weights": a.risk.weights,
        "explanation": a.risk.explanation,
    }


def _mosca_dict(a: CryptographicAsset) -> dict | None:
    if not a.mosca:
        return None
    m = a.mosca
    return {
        "data_lifetime_years": m.data_lifetime_years,
        "migration_time_years": m.migration_time_years,
        "crqc_horizon_years": m.crqc_horizon_years,
        "sum_xy": m.sum_xy,
        "gap_years": m.gap_years,
        "exposed": m.exposed,
        "priority_result": m.priority_result,
        "assumptions_note": m.assumptions_note,
        "disclaimer": "Estimate, not a prediction. CRQC horizon is a configurable assumption.",
    }


def _rec_dict(a: CryptographicAsset) -> dict | None:
    if not a.recommendation:
        return None
    r = a.recommendation
    return {
        "use_case": r.use_case,
        "current_algorithm": r.current_algorithm,
        "candidate_algorithm": r.candidate_algorithm,
        "recommendation_type": r.recommendation_type,
        "score": r.score,
        "factor_scores": r.factor_scores,
        "rationale": r.rationale,
        "compatibility_notes": r.compatibility_notes,
        "performance_memory_notes": r.performance_memory_notes,
        "migration_priority": r.migration_priority,
        "alternatives": r.alternatives,
    }


def asset_to_detail(a: CryptographicAsset) -> AssetDetailOut:
    base = asset_to_out(a).model_dump()
    v = quantum_engine.assess(
        algorithm=a.algorithm, algorithm_family=a.algorithm_family, key_size=a.key_size,
        mode=a.mode, protocol=a.protocol, version=a.version, primitive=a.primitive,
    )
    return AssetDetailOut(
        **base,
        evidence=[evidence_to_out(e) for e in a.evidence],
        quantum={
            "status": v.status,
            "shor_impact": v.shor_impact,
            "grover_impact": v.grover_impact,
            "posture": v.posture,
            "harvest_now_decrypt_later": v.harvest_now_decrypt_later,
            "explanation": v.explanation,
            "context_notes": v.context_notes,
            "matched_family": v.matched_family,
        },
        risk=_risk_dict(a),
        mosca=_mosca_dict(a),
        recommendation=_rec_dict(a),
    )
