"""Seed the database: users, default settings, and a demo scan of the fixture repo.

    python -m app.seed            # idempotent; skips if already seeded
    python -m app.seed --force    # wipe demo scan + re-run
"""
from __future__ import annotations

import sys

from sqlalchemy import select

from app.core.config import BACKEND_DIR
from app.core.db import create_all, session_scope
from app.core.kb import risk_defaults
from app.core.logging import get_logger
from app.core.security import hash_password
from app.models.application import Application
from app.models.scan import Scan
from app.models.settings import SettingKV
from app.models.user import User

log = get_logger("seed")

FIXTURE_REPO = BACKEND_DIR / "tests" / "fixtures" / "sample_repo"

DEMO_USERS = [
    ("admin@ecdat.local", "Ada Admin", "admin"),
    ("analyst@ecdat.local", "Nils Analyst", "analyst"),
    ("viewer@ecdat.local", "Vera Viewer", "viewer"),
]
DEMO_PASSWORD = "ecdat"


def seed_users(db) -> None:
    for email, name, role in DEMO_USERS:
        if not db.scalar(select(User).where(User.email == email)):
            db.add(User(
                email=email, full_name=name, role=role,
                hashed_password=hash_password(DEMO_PASSWORD), org_id="org_default",
            ))
            log.info("seed.user", email=email, role=role)


def seed_settings(db) -> None:
    if not db.get(SettingKV, "risk_weights"):
        db.add(SettingKV(key="risk_weights", value={"weights": risk_defaults()["weights"]}))
    if not db.get(SettingKV, "mosca_assumption"):
        db.add(SettingKV(key="mosca_assumption", value={
            "crqc_horizon_years": 15,
            "note": ("CRQC horizon is a configurable ASSUMPTION (default 15 years, ~2040). "
                     "Adjust in Settings to match your threat model."),
        }))


def _annotate_apps(db) -> None:
    """Give the demo application realistic metadata so risk/Mosca have signal."""
    app = db.scalar(select(Application).where(Application.name == "sample_repo"))
    if app:
        app.owner = "Payments Platform"
        app.business_unit = "Financial Services"
        app.business_criticality = 5
        app.system_lifetime_years = 12
        app.data_sensitivity = 5
        app.data_lifetime_years = 25  # regulated financial records -> long confidentiality need


def run_demo_scan(db, *, force: bool) -> str | None:
    if not FIXTURE_REPO.exists():
        log.warning("seed.no_fixture", path=str(FIXTURE_REPO))
        return None
    existing = db.scalar(
        select(Scan).where(Scan.target == str(FIXTURE_REPO)).order_by(Scan.created_at.desc())
    )
    if existing and not force:
        log.info("seed.scan.exists", scan_id=existing.scan_id)
        return existing.scan_id

    scan = Scan(
        target=str(FIXTURE_REPO),
        target_kind="path",
        scan_types=["source", "dependency", "config", "container"],
        status="queued",
        stage="queued",
        notes="Seed demo scan",
    )
    db.add(scan)
    db.flush()
    return scan.scan_id


def main(argv: list[str]) -> None:
    force = "--force" in argv
    create_all()
    with session_scope() as db:
        seed_users(db)
        seed_settings(db)
        scan_id = run_demo_scan(db, force=force)

    if scan_id:
        from app.scanners.runner import run_scan  # imported late to avoid cycles

        log.info("seed.scan.run", scan_id=scan_id)
        run_scan(scan_id)  # synchronous for seeding
        with session_scope() as db:
            _annotate_apps(db)
        # re-run analysis so the annotated application metadata is reflected
        from app.analysis.pipeline import run_for_scan

        with session_scope() as db:
            run_for_scan(db, scan_id)
        with session_scope() as db:
            s = db.get(Scan, scan_id)
            log.info("seed.done", scan_id=scan_id, status=s.status, stats=s.stats)
    print("Seed complete. Logins: " + ", ".join(e for e, _, _ in DEMO_USERS) + f"  (password: {DEMO_PASSWORD})")


if __name__ == "__main__":
    main(sys.argv[1:])
