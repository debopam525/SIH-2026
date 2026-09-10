from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, pk


class Report(Base, TimestampMixin):
    __tablename__ = "reports"

    report_id: Mapped[str] = pk("rpt")
    type: Mapped[str] = mapped_column(String(32))
    format: Mapped[str] = mapped_column(String(8))
    scan_id: Mapped[str | None] = mapped_column(String(40))
    filename: Mapped[str] = mapped_column(String(255))
    path: Mapped[str] = mapped_column(String(1024))
    size_bytes: Mapped[int] = mapped_column(default=0)
    created_by: Mapped[str | None] = mapped_column(String(40))
