"""Declarative base + shared column helpers."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:20]}"


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )


def pk(prefix: str) -> Mapped[str]:
    return mapped_column(
        String(40), primary_key=True, default=lambda: new_id(prefix)
    )


# Vocabulary constants (kept as plain strings for SQLite portability; validated in schemas).
SCAN_STATUS = ("queued", "running", "completed", "failed", "cancelled")
SCAN_TYPES = ("source", "dependency", "config", "binary", "container")
ASSET_TYPES = (
    "library-call", "dependency", "config-setting", "certificate", "protocol-config",
    "binary-symbol", "container-package", "unknown",
)
CONFIDENCE = ("confirmed_api", "strong_textual", "weak_textual", "ml_classified")
QUANTUM_STATUS = ("quantum-vulnerable", "quantum-weakened", "quantum-safe", "broken-classical", "unknown")
RISK_CATEGORY = ("critical", "high", "medium", "low")
REC_TYPE = ("pqc", "hybrid", "symmetric_upgrade", "config_change", "no_change")
MIGRATION_STATUS = ("not_started", "in_progress", "blocked", "done")
UNKNOWN = "unknown"
