from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pk


class Scan(Base, TimestampMixin):
    __tablename__ = "scans"

    scan_id: Mapped[str] = pk("scan")
    target: Mapped[str] = mapped_column(String(1024))
    target_kind: Mapped[str] = mapped_column(String(32), default="path")  # path | git | upload | image
    scan_types: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(16), default="queued", index=True)
    progress: Mapped[float] = mapped_column(default=0.0)
    stage: Mapped[str] = mapped_column(String(64), default="queued")
    start_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    scanner_versions: Mapped[dict] = mapped_column(JSON, default=dict)
    stats: Mapped[dict] = mapped_column(JSON, default=dict)
    errors: Mapped[list] = mapped_column(JSON, default=list)
    cancel_requested: Mapped[bool] = mapped_column(default=False)
    created_by: Mapped[str | None] = mapped_column(String(40))
    notes: Mapped[str | None] = mapped_column(Text)

    assets: Mapped[list[CryptographicAsset]] = relationship(  # noqa: F821
        back_populates="scan", cascade="all, delete-orphan"
    )
