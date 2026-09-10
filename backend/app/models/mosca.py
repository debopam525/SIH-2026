from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pk


class MoscaAssessment(Base, TimestampMixin):
    """Mosca 'X + Y > Z' theorem. All values are ESTIMATES, surfaced with a disclaimer."""

    __tablename__ = "mosca_assessments"

    mosca_id: Mapped[str] = pk("mosca")
    asset_id: Mapped[str] = mapped_column(
        ForeignKey("crypto_assets.asset_id", ondelete="CASCADE"), unique=True, index=True
    )
    data_lifetime_years: Mapped[float] = mapped_column(default=0.0)          # X
    migration_time_years: Mapped[float] = mapped_column(default=0.0)          # Y
    crqc_horizon_years: Mapped[float] = mapped_column(default=15.0)           # Z (assumption)
    sum_xy: Mapped[float] = mapped_column(default=0.0)
    gap_years: Mapped[float] = mapped_column(default=0.0)                     # (X + Y) - Z
    exposed: Mapped[bool] = mapped_column(default=False)                      # X + Y > Z
    priority_result: Mapped[str] = mapped_column(String(16), default="low")  # act_now|plan|monitor
    assumptions_note: Mapped[str] = mapped_column(Text, default="")

    asset: Mapped[CryptographicAsset] = relationship(back_populates="mosca")  # noqa: F821
