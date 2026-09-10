from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pk


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"

    rec_id: Mapped[str] = pk("rec")
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("crypto_assets.asset_id", ondelete="CASCADE"), unique=True, index=True
    )
    use_case: Mapped[str] = mapped_column(String(32), default="unknown")  # kem|signature|symmetric|hash
    current_algorithm: Mapped[str] = mapped_column(String(96), default="unknown")
    candidate_algorithm: Mapped[str] = mapped_column(String(96), default="unknown")
    recommendation_type: Mapped[str] = mapped_column(String(24), default="no_change")
    score: Mapped[float] = mapped_column(default=0.0)
    factor_scores: Mapped[dict] = mapped_column(JSON, default=dict)
    rationale: Mapped[str] = mapped_column(Text, default="")
    compatibility_notes: Mapped[str] = mapped_column(Text, default="")
    performance_memory_notes: Mapped[str] = mapped_column(Text, default="")
    migration_priority: Mapped[str] = mapped_column(String(12), default="low")
    alternatives: Mapped[list] = mapped_column(JSON, default=list)

    asset: Mapped[CryptographicAsset] = relationship(back_populates="recommendation")  # noqa: F821
