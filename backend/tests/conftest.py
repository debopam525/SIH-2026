from __future__ import annotations

import os
import tempfile
from collections.abc import Iterator

import pytest

os.environ.setdefault("ECDAT_ENV", "test")
_tmp_db = os.path.join(tempfile.gettempdir(), "ecdat_test.db")
os.environ["ECDAT_DATABASE_URL"] = f"sqlite+pysqlite:///{_tmp_db}"
os.environ["ECDAT_JWT_SECRET"] = "test-secret-test-secret-test-secret-1234"

from app.core.db import SessionLocal, create_all, engine  # noqa: E402
from app.models.base import Base  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _schema() -> Iterator[None]:
    Base.metadata.drop_all(bind=engine)
    create_all()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db() -> Iterator:
    session = SessionLocal()
    try:
        yield session
        session.rollback()
    finally:
        session.close()


@pytest.fixture(scope="session")
def fixture_repo() -> str:
    from app.core.config import BACKEND_DIR

    return str(BACKEND_DIR / "tests" / "fixtures" / "sample_repo")
