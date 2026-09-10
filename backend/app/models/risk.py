from __future__ import annotations

from sqlalchemy import JSON, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pk


class RiskAssessment(Base, TimestampMixin):
    __tablename__ = "risk_assessments"

    assessment_id: Mapped[str] = pk("risk")
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("crypto_assets.asset_id", ondelete="CASCADE"), unique=True, index=True
    )
    # {factor_name: {value: 1-5, rationale: str, source: "derived"|"application"|"default"}}
    factors: Mapped[dict] = mapped_column(JSON, default=dict)
    weights: Mapped[dict] = mapped_column(JSON, default=dict)
    weighted_score: Mapped[float] = mapped_column(default=0.0)  # 1.0 - 5.0
    risk_category: Mapped[str] = mapped_column(String(12), default="low", index=True)
    explanation: Mapped[str] = mapped_column(Text, default="")

    asset: Mapped[CryptographicAsset] = relationship(back_populates="risk")  # noqa: F821
