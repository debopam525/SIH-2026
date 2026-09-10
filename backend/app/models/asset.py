from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pk


class CryptographicAsset(Base, TimestampMixin):
    """One deduplicated cryptographic asset in the CBOM.

    Unknown fields are stored literally as the string ``"unknown"`` (never silently inferred).
    ``dedup_key`` is what correlation uses to merge findings from multiple scanners.
    """

    __tablename__ = "crypto_assets"
    __table_args__ = (UniqueConstraint("scan_id", "dedup_key", name="uq_asset_scan_dedup"),)

    asset_id: Mapped[str] = pk("asset")
    scan_id: Mapped[str] = mapped_column(
        ForeignKey("scans.scan_id", ondelete="CASCADE"), index=True
    )
    app_id: Mapped[str | None] = mapped_column(
        ForeignKey("applications.app_id", ondelete="SET NULL"), index=True
    )

    asset_name: Mapped[str] = mapped_column(String(255))
    algorithm: Mapped[str] = mapped_column(String(64), index=True)
    algorithm_family: Mapped[str] = mapped_column(String(64), index=True)
    # kem | key-exchange | signature | cipher | hash | kdf | mac | protocol | unknown
    primitive: Mapped[str] = mapped_column(String(32), default="unknown")
    version: Mapped[str] = mapped_column(String(64), default="unknown")
    key_size: Mapped[str] = mapped_column(String(32), default="unknown")
    mode: Mapped[str] = mapped_column(String(32), default="unknown")
    protocol: Mapped[str] = mapped_column(String(64), default="unknown")
    library_dependency: Mapped[str] = mapped_column(String(255), default="unknown")
    usage_location: Mapped[str] = mapped_column(String(1024), default="unknown")
    asset_type: Mapped[str] = mapped_column(String(32), default="unknown")
    source: Mapped[str] = mapped_column(String(64), default="unknown")  # primary scanner
    sources: Mapped[list] = mapped_column(JSON, default=list)  # all scanners that found it
    detection_confidence: Mapped[str] = mapped_column(
        String(24), default="weak_textual", index=True
    )
    dedup_key: Mapped[str] = mapped_column(String(255), index=True)

    scan: Mapped[Scan] = relationship(back_populates="assets")  # noqa: F821
    application: Mapped[Application | None] = relationship(back_populates="assets")  # noqa: F821
    evidence: Mapped[list[Evidence]] = relationship(  # noqa: F821
        back_populates="asset", cascade="all, delete-orphan"
    )
    risk: Mapped[RiskAssessment | None] = relationship(  # noqa: F821
        back_populates="asset", cascade="all, delete-orphan", uselist=False
    )
    mosca: Mapped[MoscaAssessment | None] = relationship(  # noqa: F821
        back_populates="asset", cascade="all, delete-orphan", uselist=False
    )
    recommendation: Mapped[Recommendation | None] = relationship(  # noqa: F821
        back_populates="asset", cascade="all, delete-orphan", uselist=False
    )
    migration: Mapped[MigrationStatus | None] = relationship(  # noqa: F821
        back_populates="asset", cascade="all, delete-orphan", uselist=False
    )
