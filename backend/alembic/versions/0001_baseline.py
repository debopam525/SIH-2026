"""Baseline schema.

Creates the full ECDAT schema from the SQLAlchemy models. Young project -> a single baseline
revision. Subsequent changes use ``alembic revision --autogenerate``.

Revision ID: 0001_baseline
Revises:
Create Date: 2026-01-01
"""
from __future__ import annotations

from alembic import op
from app import models  # noqa: F401
from app.models.base import Base

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
