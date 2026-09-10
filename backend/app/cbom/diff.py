"""Diff two scans by CBOM dedup key."""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.asset import CryptographicAsset


@dataclass
class ScanDiff:
    base_scan_id: str | None
    target_scan_id: str
    added: list[dict] = field(default_factory=list)
    removed: list[dict] = field(default_factory=list)
    changed: list[dict] = field(default_factory=list)
    unchanged_count: int = 0


def _index(db: Session, scan_id: str) -> dict[str, CryptographicAsset]:
    rows = db.scalars(
        select(CryptographicAsset).where(CryptographicAsset.scan_id == scan_id)
    ).all()
    return {r.dedup_key: r for r in rows}


def _summ(a: CryptographicAsset) -> dict:
    return {
        "asset_id": a.asset_id,
        "asset_name": a.asset_name,
        "algorithm": a.algorithm,
        "algorithm_family": a.algorithm_family,
        "key_size": a.key_size,
        "risk_category": a.risk.risk_category if a.risk else None,
        "quantum_status": None,
        "dedup_key": a.dedup_key,
    }


def diff_scans(db: Session, target_scan_id: str, base_scan_id: str | None) -> ScanDiff:
    target = _index(db, target_scan_id)
    out = ScanDiff(base_scan_id=base_scan_id, target_scan_id=target_scan_id)
    if not base_scan_id:
        out.added = [_summ(a) for a in target.values()]
        return out

    base = _index(db, base_scan_id)
    for key, a in target.items():
        if key not in base:
            out.added.append(_summ(a))
        else:
            b = base[key]
            fields = ("key_size", "mode", "version", "detection_confidence")
            deltas = {
                f: [getattr(b, f), getattr(a, f)]
                for f in fields
                if getattr(b, f) != getattr(a, f)
            }
            b_cat = b.risk.risk_category if b.risk else None
            a_cat = a.risk.risk_category if a.risk else None
            if b_cat != a_cat:
                deltas["risk_category"] = [b_cat, a_cat]
            if deltas:
                out.changed.append({**_summ(a), "changes": deltas})
            else:
                out.unchanged_count += 1
    for key, b in base.items():
        if key not in target:
            out.removed.append(_summ(b))
    return out
