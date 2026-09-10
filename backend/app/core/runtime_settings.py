"""Runtime-editable settings with layered fallback: DB (settings_kv) -> YAML/env default.

Keeps the analysis engines free of I/O concerns — they receive plain dicts/values.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.kb import risk_defaults
from app.models.settings import SettingKV

RISK_WEIGHTS_KEY = "risk_weights"
CRQC_KEY = "mosca_assumption"


def get_risk_weights(db: Session) -> dict[str, float]:
    row = db.get(SettingKV, RISK_WEIGHTS_KEY)
    if row and isinstance(row.value, dict) and row.value.get("weights"):
        return dict(row.value["weights"])
    return dict(risk_defaults()["weights"])


def set_risk_weights(db: Session, weights: dict[str, float]) -> dict[str, float]:
    row = db.get(SettingKV, RISK_WEIGHTS_KEY)
    payload = {"weights": weights}
    if row:
        row.value = payload
    else:
        db.add(SettingKV(key=RISK_WEIGHTS_KEY, value=payload))
    db.flush()
    return weights


def get_crqc_horizon(db: Session) -> float:
    row = db.get(SettingKV, CRQC_KEY)
    if row and isinstance(row.value, dict) and "crqc_horizon_years" in row.value:
        return float(row.value["crqc_horizon_years"])
    return float(settings.crqc_horizon_years)


def get_crqc_note(db: Session) -> str:
    row = db.get(SettingKV, CRQC_KEY)
    if row and isinstance(row.value, dict) and row.value.get("note"):
        return str(row.value["note"])
    return (
        "CRQC horizon is a configurable ASSUMPTION, not a prediction. Default 15 years reflects "
        "the middle of commonly cited industry/government estimates (roughly 2035-2045). Adjust "
        "in Settings to match your organisation's threat model."
    )


def set_crqc(db: Session, years: float, note: str | None = None) -> None:
    row = db.get(SettingKV, CRQC_KEY)
    payload = {"crqc_horizon_years": years}
    if note:
        payload["note"] = note
    elif row and isinstance(row.value, dict) and row.value.get("note"):
        payload["note"] = row.value["note"]
    if row:
        row.value = payload
    else:
        db.add(SettingKV(key=CRQC_KEY, value=payload))
    db.flush()


def all_settings_seeded(db: Session) -> bool:
    keys = set(db.scalars(select(SettingKV.key)).all())
    return {RISK_WEIGHTS_KEY, CRQC_KEY}.issubset(keys)
