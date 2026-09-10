"""CBOM serialization. JSON follows a CycloneDX-1.6-CBOM-style shape (``cryptoProperties``)
so standard tooling can consume it; CSV is a flat inventory for spreadsheets.
"""
from __future__ import annotations

import csv
import io
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.asset import CryptographicAsset
from app.models.scan import Scan

_ASSET_TYPE_MAP = {
    "cipher": "algorithm", "hash": "algorithm", "mac": "algorithm", "kdf": "algorithm",
    "signature": "algorithm", "kem": "algorithm", "key-exchange": "algorithm",
    "protocol": "protocol",
}


def _load(db: Session, scan_id: str) -> tuple[Scan, list[CryptographicAsset]]:
    scan = db.get(Scan, scan_id)
    assets = db.scalars(
        select(CryptographicAsset)
        .where(CryptographicAsset.scan_id == scan_id)
        .options(
            selectinload(CryptographicAsset.evidence),
            selectinload(CryptographicAsset.risk),
            selectinload(CryptographicAsset.mosca),
            selectinload(CryptographicAsset.recommendation),
        )
        .order_by(CryptographicAsset.algorithm_family, CryptographicAsset.algorithm)
    ).all()
    return scan, assets


def to_cyclonedx(db: Session, scan_id: str) -> dict:
    scan, assets = _load(db, scan_id)
    components = []
    for a in assets:
        components.append({
            "type": "cryptographic-asset",
            "bom-ref": a.asset_id,
            "name": a.asset_name,
            "cryptoProperties": {
                "assetType": _ASSET_TYPE_MAP.get(a.primitive, "algorithm"),
                "algorithmProperties": {
                    "algorithm": a.algorithm,
                    "family": a.algorithm_family,
                    "primitive": a.primitive,
                    "parameterSetIdentifier": a.key_size,
                    "mode": a.mode,
                    "curve": None if a.__dict__.get("curve") in (None, "unknown") else a.__dict__.get("curve"),
                },
                "protocolProperties": {"type": a.protocol, "version": a.version}
                if a.algorithm_family == "protocol" else None,
                "oid": None,
            },
            "properties": [
                {"name": "ecdat:usageLocation", "value": a.usage_location},
                {"name": "ecdat:library", "value": a.library_dependency},
                {"name": "ecdat:detectionConfidence", "value": a.detection_confidence},
                {"name": "ecdat:sources", "value": ",".join(a.sources or [])},
                {"name": "ecdat:quantumStatus",
                 "value": (a.recommendation and a.recommendation.use_case) or "n/a"},
                {"name": "ecdat:riskCategory",
                 "value": a.risk.risk_category if a.risk else "n/a"},
                {"name": "ecdat:migrationPriority",
                 "value": a.recommendation.migration_priority if a.recommendation else "n/a"},
            ],
            "evidence": {
                "occurrences": [
                    {
                        "location": e.location,
                        "line": e.line_or_offset,
                        "symbol": e.function_or_scope,
                        "additionalContext": e.matched_indicator,
                        "confidence": e.confidence,
                        "detector": e.detector,
                    }
                    for e in a.evidence
                ]
            },
        })

    return {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "serialNumber": f"urn:uuid:ecdat-{scan_id}",
        "version": 1,
        "metadata": {
            "timestamp": datetime.now(UTC).isoformat(),
            "tools": [{"vendor": "ECDAT", "name": "ecdat", "version": "0.1.0"}],
            "properties": [
                {"name": "ecdat:scanId", "value": scan_id},
                {"name": "ecdat:target", "value": scan.target if scan else "unknown"},
                {"name": "ecdat:scanTypes", "value": ",".join(scan.scan_types or []) if scan else ""},
                {"name": "ecdat:assetCount", "value": str(len(assets))},
            ],
        },
        "components": components,
    }


CSV_COLUMNS = [
    "asset_id", "asset_name", "algorithm", "algorithm_family", "primitive", "key_size", "mode",
    "protocol", "version", "library_dependency", "usage_location", "asset_type", "sources",
    "detection_confidence", "risk_category", "weighted_score", "quantum_use_case",
    "recommended_algorithm", "recommendation_type", "migration_priority", "evidence_count",
]


def to_csv(db: Session, scan_id: str) -> str:
    _scan, assets = _load(db, scan_id)
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_COLUMNS, extrasaction="ignore")
    w.writeheader()
    for a in assets:
        w.writerow({
            "asset_id": a.asset_id,
            "asset_name": a.asset_name,
            "algorithm": a.algorithm,
            "algorithm_family": a.algorithm_family,
            "primitive": a.primitive,
            "key_size": a.key_size,
            "mode": a.mode,
            "protocol": a.protocol,
            "version": a.version,
            "library_dependency": a.library_dependency,
            "usage_location": a.usage_location,
            "asset_type": a.asset_type,
            "sources": ",".join(a.sources or []),
            "detection_confidence": a.detection_confidence,
            "risk_category": a.risk.risk_category if a.risk else "",
            "weighted_score": a.risk.weighted_score if a.risk else "",
            "quantum_use_case": a.recommendation.use_case if a.recommendation else "",
            "recommended_algorithm": a.recommendation.candidate_algorithm if a.recommendation else "",
            "recommendation_type": a.recommendation.recommendation_type if a.recommendation else "",
            "migration_priority": a.recommendation.migration_priority if a.recommendation else "",
            "evidence_count": len(a.evidence),
        })
    return buf.getvalue()
