from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, pk


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    app_id: Mapped[str] = pk("app")
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    owner: Mapped[str | None] = mapped_column(String(255))
    business_unit: Mapped[str | None] = mapped_column(String(255))
    # 1-5; 5 = mission critical. "unknown" -> stored as None, treated as mid (3) with a note.
    business_criticality: Mapped[int | None] = mapped_column()
    system_lifetime_years: Mapped[int | None] = mapped_column()
    data_sensitivity: Mapped[int | None] = mapped_column()  # 1-5
    data_lifetime_years: Mapped[int | None] = mapped_column()
    description: Mapped[str | None] = mapped_column(Text)

    assets: Mapped[list[CryptographicAsset]] = relationship(back_populates="application")  # noqa: F821
    repositories: Mapped[list[Repository]] = relationship(back_populates="application")
    dependencies: Mapped[list[Dependency]] = relationship(back_populates="application")


class Repository(Base, TimestampMixin):
    __tablename__ = "repositories"

    repo_id: Mapped[str] = pk("repo")
    name: Mapped[str] = mapped_column(String(512))
    path: Mapped[str] = mapped_column(String(1024))
    vcs_url: Mapped[str | None] = mapped_column(String(1024))
    app_id: Mapped[str | None] = mapped_column(ForeignKey("applications.app_id", ondelete="SET NULL"))

    application: Mapped[Application | None] = relationship(back_populates="repositories")


class Dependency(Base, TimestampMixin):
    __tablename__ = "dependencies"

    dep_id: Mapped[str] = pk("dep")
    name: Mapped[str] = mapped_column(String(512), index=True)
    ecosystem: Mapped[str] = mapped_column(String(32))  # pypi | npm | maven | go | cargo | ...
    version: Mapped[str] = mapped_column(String(128), default="unknown")
    relation: Mapped[str] = mapped_column(String(16), default="direct")  # direct | transitive
    provides_crypto: Mapped[bool] = mapped_column(default=False)
    app_id: Mapped[str | None] = mapped_column(ForeignKey("applications.app_id", ondelete="SET NULL"))

    application: Mapped[Application | None] = relationship(back_populates="dependencies")
