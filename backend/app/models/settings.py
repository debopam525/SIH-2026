from __future__ import annotations

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin


class SettingKV(Base, TimestampMixin):
    """Runtime-editable configuration (risk weights, CRQC assumption, ...).

    Falls back to file/env defaults when a key is absent. Admin-only writes.
    """

    __tablename__ = "settings_kv"

    key: Mapped[str] = mapped_column(String(64), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON, default=dict)
