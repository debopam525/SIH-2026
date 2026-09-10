from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pk


class Evidence(Base, TimestampMixin):
    __tablename__ = "evidence"

    evidence_id: Mapped[str] = pk("ev")
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("crypto_assets.asset_id", ondelete="CASCADE"), index=True
    )
    location_kind: Mapped[str] = mapped_column(String(24), default="file")  # file|binary|container|config
    location: Mapped[str] = mapped_column(String(1024))
    line_or_offset: Mapped[str] = mapped_column(String(32), default="unknown")
    function_or_scope: Mapped[str] = mapped_column(String(255), default="unknown")
    matched_indicator: Mapped[str] = mapped_column(String(255))
    surrounding_context: Mapped[str] = mapped_column(Text, default="")
    confidence: Mapped[str] = mapped_column(String(24), default="weak_textual")
    detector: Mapped[str] = mapped_column(String(64), default="rules")
    signature_id: Mapped[str] = mapped_column(String(96), default="unknown")

    asset: Mapped[CryptographicAsset] = relationship(back_populates="evidence")  # noqa: F821
