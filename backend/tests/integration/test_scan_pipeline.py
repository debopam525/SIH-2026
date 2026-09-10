"""Full scan -> correlate -> analyse pipeline against the fixture repo, plus API happy path."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.core.db import session_scope
from app.core.security import hash_password
from app.main import app
from app.models.scan import Scan
from app.models.user import User
from app.scanners.runner import run_scan


@pytest.fixture(scope="module")
def seeded_scan(fixture_repo) -> str:
    with session_scope() as db:
        if not db.scalar(select(User).where(User.email == "admin@ecdat.local")):
            db.add(User(email="admin@ecdat.local", full_name="A", role="admin",
                        hashed_password=hash_password("ecdat")))
        scan = Scan(target=fixture_repo, target_kind="path",
                    scan_types=["source", "dependency", "config"], status="queued", stage="queued")
        db.add(scan)
        db.flush()
        sid = scan.scan_id
    run_scan(sid)
    return sid


def test_scan_completes_and_finds_expected_algorithms(seeded_scan):
    with session_scope() as db:
        scan = db.get(Scan, seeded_scan)
        assert scan.status == "completed"
        algos = {a.algorithm for a in scan.assets}
    for expected in {"RSA", "AES", "MD5", "ECDSA", "SHA-1"}:
        assert expected in algos, f"missing {expected} in {sorted(algos)}"
    assert "ML-KEM" in algos  # already-PQC component picked up


def test_every_asset_has_cbom_fields_and_evidence(seeded_scan):
    with session_scope() as db:
        for a in db.get(Scan, seeded_scan).assets:
            for field in ("algorithm", "algorithm_family", "key_size", "mode", "protocol",
                          "version", "library_dependency", "usage_location", "asset_type"):
                assert getattr(a, field), f"{a.asset_name}.{field} empty"
            assert len(a.evidence) >= 1


def test_no_asset_double_counted(seeded_scan):
    with session_scope() as db:
        keys = [a.dedup_key for a in db.get(Scan, seeded_scan).assets]
    assert len(keys) == len(set(keys))


def test_every_vulnerable_asset_has_explained_verdict_risk_mosca_rec(seeded_scan):
    with session_scope() as db:
        for a in db.get(Scan, seeded_scan).assets:
            assert a.risk is not None and a.risk.explanation
            assert a.risk.factors and len(a.risk.factors) == 9
            assert a.mosca is not None and "ESTIMATE" in a.mosca.assumptions_note
            assert a.recommendation is not None
            assert a.recommendation.rationale
            if a.recommendation.recommendation_type != "no_change":
                assert a.recommendation.alternatives is not None


def test_api_happy_path_scan_to_report(seeded_scan):
    c = TestClient(app)
    tok = c.post("/api/v1/auth/login",
                 json={"email": "admin@ecdat.local", "password": "ecdat"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}

    metrics = c.get("/api/v1/dashboard/metrics", headers=h).json()
    assert metrics["totals"]["assets"] > 0

    assets = c.get("/api/v1/assets", headers=h, params={"scan_id": seeded_scan}).json()
    assert assets["total"] > 0
    aid = assets["items"][0]["asset_id"]

    detail = c.get(f"/api/v1/assets/{aid}", headers=h).json()
    assert detail["quantum"]["explanation"]
    assert detail["risk"]["factors"]
    assert detail["mosca"]["assumptions_note"]

    risk = c.get(f"/api/v1/risk/{aid}", headers=h)
    assert risk.status_code == 200

    rec = c.get(f"/api/v1/recommendations/{aid}", headers=h)
    assert rec.status_code == 200

    rpt = c.post("/api/v1/reports/generate", headers=h,
                 json={"type": "executive_summary", "format": "json", "scan_id": seeded_scan})
    assert rpt.status_code == 201
    rid = rpt.json()["report_id"]
    dl = c.get(f"/api/v1/reports/{rid}/download", headers=h)
    assert dl.status_code == 200


def test_rbac_viewer_cannot_start_scan():
    with session_scope() as db:
        if not db.scalar(select(User).where(User.email == "viewer@ecdat.local")):
            db.add(User(email="viewer@ecdat.local", full_name="V", role="viewer",
                        hashed_password=hash_password("ecdat")))
    c = TestClient(app)
    tok = c.post("/api/v1/auth/login",
                 json={"email": "viewer@ecdat.local", "password": "ecdat"}).json()["access_token"]
    r = c.post("/api/v1/scans", headers={"Authorization": f"Bearer {tok}"},
               json={"target": "x", "target_kind": "path", "scan_types": ["source"]})
    assert r.status_code == 403


def test_cbom_diff_reports_added_on_first_scan(seeded_scan):
    c = TestClient(app)
    tok = c.post("/api/v1/auth/login",
                 json={"email": "admin@ecdat.local", "password": "ecdat"}).json()["access_token"]
    h = {"Authorization": f"Bearer {tok}"}
    d = c.get(f"/api/v1/scans/{seeded_scan}/diff", headers=h).json()
    assert d["summary"]["added"] >= 1
