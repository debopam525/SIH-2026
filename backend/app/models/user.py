from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, pk


class User(Base, TimestampMixin):
    __tablename__ = "users"

    user_id: Mapped[str] = pk("usr")
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(16), default="viewer")  # admin|analyst|viewer
    org_id: Mapped[str] = mapped_column(String(40), default="org_default")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
