from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pk


class MigrationStatus(Base, TimestampMixin):
    __tablename__ = "migration_status"

    id: Mapped[str] = pk("mig")
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("crypto_assets.asset_id", ondelete="CASCADE"), unique=True, index=True
    )
    priority: Mapped[str] = mapped_column(String(12), default="low", index=True)
    readiness: Mapped[int] = mapped_column(default=0)  # 0-100 %
    status: Mapped[str] = mapped_column(String(16), default="not_started", index=True)
    owner: Mapped[str | None] = mapped_column(String(255))
    planned_target_date: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    notes: Mapped[str | None] = mapped_column(Text)

    asset: Mapped[CryptographicAsset] = relationship(back_populates="migration")  # noqa: F821
