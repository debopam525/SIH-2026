"""Scan orchestration: resolve target -> run scanners -> correlate -> persist -> analyse.

Runs inside a FastAPI ``BackgroundTasks`` job with its own DB session. Cancellation is
cooperative: the API sets ``Scan.cancel_requested`` and the runner checks it between stages.
One bad file never aborts the scan (errors are collected onto the Scan row).
"""
from __future__ import annotations

import shutil
import subprocess
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from app.analysis.pipeline import run_for_scan
from app.cbom.correlate import correlate
from app.core.config import settings
from app.core.db import session_scope
from app.core.logging import get_logger
from app.models.application import Application, Repository
from app.models.asset import CryptographicAsset
from app.models.evidence import Evidence
from app.models.scan import Scan
from app.scanners.base import SCANNER_VERSION, ScanContext
from app.scanners.binary import BinaryScanner
from app.scanners.config import ConfigScanner
from app.scanners.container import ContainerScanner
from app.scanners.dependency import DependencyScanner
from app.scanners.source import SourceScanner

log = get_logger("scan.runner")

SCANNERS = {
    "source": SourceScanner,
    "dependency": DependencyScanner,
    "config": ConfigScanner,
    "binary": BinaryScanner,
    "container": ContainerScanner,
}


class Cancelled(Exception):
    pass


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _check_cancel(db, scan_id: str) -> None:
    db.expire_all()
    scan = db.get(Scan, scan_id)
    if scan and scan.cancel_requested:
        raise Cancelled()


def _resolve_target(scan: Scan) -> tuple[Path, bool]:
    """Return (root_dir, is_temp). Supports local path, git URL, and uploaded zip path."""
    kind = scan.target_kind
    target = scan.target
    if kind == "path":
        p = Path(target).expanduser().resolve()
        if not p.exists():
            raise FileNotFoundError(f"target path does not exist: {p}")
        return p, False
    if kind == "git":
        dest = settings.scan_workdir / f"{scan.scan_id}_clone"
        if dest.exists():
            shutil.rmtree(dest, ignore_errors=True)
        subprocess.run(
            ["git", "clone", "--depth", "1", target, str(dest)],
            check=True, capture_output=True, text=True, timeout=300,
        )
        return dest, True
    if kind == "upload":
        src = Path(target)
        dest = settings.scan_workdir / f"{scan.scan_id}_unzip"
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(src) as zf:
            zf.extractall(dest)
        return dest, True
    raise ValueError(f"unsupported target_kind: {kind}")


def run_scan(scan_id: str) -> None:
    with session_scope() as db:
        scan = db.get(Scan, scan_id)
        if not scan:
            log.error("scan.missing", scan_id=scan_id)
            return
        scan.status = "running"
        scan.stage = "preparing"
        scan.progress = 0.02
        scan.start_time = _utcnow()
        scan.scanner_versions = dict.fromkeys(scan.scan_types or [], SCANNER_VERSION)
        requested_types = list(scan.scan_types or [])
        db.flush()

    root: Path | None = None
    is_temp = False
    try:
        with session_scope() as db:
            scan = db.get(Scan, scan_id)
            root, is_temp = _resolve_target(scan)
            _ensure_repo_and_app(db, scan, root)

        types = [t for t in requested_types if t in SCANNERS] or ["source"]
        all_findings = []
        errors: list[dict] = []
        files_total = 0
        per_scanner_stats: dict[str, dict] = {}

        for i, stype in enumerate(types):
            with session_scope() as db:
                _check_cancel(db, scan_id)
                s = db.get(Scan, scan_id)
                s.stage = f"scanning:{stype}"
                s.progress = 0.05 + 0.6 * (i / max(1, len(types)))
                db.flush()

            scanner = SCANNERS[stype]()
            ctx = ScanContext(root=root, scan_id=scan_id, scan_types=types)
            t0 = time.perf_counter()
            result = scanner.run(ctx)
            dt = round(time.perf_counter() - t0, 2)
            all_findings.extend(result.findings)
            errors.extend(result.errors)
            files_total += result.files_scanned
            per_scanner_stats[stype] = {
                "files_scanned": result.files_scanned,
                "raw_findings": len(result.findings),
                "errors": len(result.errors),
                "seconds": dt,
            }
            log.info("scan.scanner.done", scan_id=scan_id, scanner=stype, **per_scanner_stats[stype])

        with session_scope() as db:
            _check_cancel(db, scan_id)
            s = db.get(Scan, scan_id)
            s.stage = "correlating"
            s.progress = 0.72
            db.flush()

        assets = correlate(all_findings)

        with session_scope() as db:
            _check_cancel(db, scan_id)
            scan = db.get(Scan, scan_id)
            app_id = _default_app_id(db, scan)
            _persist_assets(db, scan_id, app_id, assets)
            scan.stage = "analysing"
            scan.progress = 0.85
            db.flush()

        with session_scope() as db:
            _check_cancel(db, scan_id)
            analysis = run_for_scan(db, scan_id)
            scan = db.get(Scan, scan_id)
            scan.status = "completed"
            scan.stage = "completed"
            scan.progress = 1.0
            scan.end_time = _utcnow()
            scan.errors = errors[:500]
            scan.stats = {
                "files_scanned": files_total,
                "raw_findings": len(all_findings),
                "assets": len(assets),
                "per_scanner": per_scanner_stats,
                "analysis": analysis,
                "error_count": len(errors),
            }
            db.flush()
        log.info("scan.completed", scan_id=scan_id, assets=len(assets), errors=len(errors))

    except Cancelled:
        with session_scope() as db:
            s = db.get(Scan, scan_id)
            s.status = "cancelled"
            s.stage = "cancelled"
            s.end_time = _utcnow()
            db.flush()
        log.info("scan.cancelled", scan_id=scan_id)
    except Exception as exc:  # noqa: BLE001
        log.exception("scan.failed", scan_id=scan_id)
        with session_scope() as db:
            s = db.get(Scan, scan_id)
            s.status = "failed"
            s.stage = "failed"
            s.end_time = _utcnow()
            s.errors = (s.errors or []) + [{"scanner": "runner", "error": repr(exc)}]
            db.flush()
    finally:
        if is_temp and root and root.exists():
            shutil.rmtree(root, ignore_errors=True)


def _ensure_repo_and_app(db, scan: Scan, root: Path) -> None:
    name = root.name or scan.target
    app = db.query(Application).filter(Application.name == name).one_or_none()
    if not app:
        app = Application(
            name=name, owner="unassigned", business_unit="unassigned",
            description=f"Auto-created from scan {scan.scan_id}",
        )
        db.add(app)
        db.flush()
    if not db.query(Repository).filter(Repository.path == str(root)).one_or_none():
        db.add(Repository(name=name, path=str(root),
                          vcs_url=scan.target if scan.target_kind == "git" else None,
                          app_id=app.app_id))
    db.flush()


def _default_app_id(db, scan: Scan) -> str | None:
    root_name = Path(scan.target).name or scan.target
    app = db.query(Application).filter(Application.name == root_name).one_or_none()
    return app.app_id if app else None


def _persist_assets(db, scan_id: str, app_id: str | None, assets: list) -> None:
    # replace any prior assets for this scan (idempotent re-runs)
    for old in db.query(CryptographicAsset).filter(CryptographicAsset.scan_id == scan_id).all():
        db.delete(old)
    db.flush()
    for ca in assets:
        row = CryptographicAsset(
            scan_id=scan_id,
            app_id=app_id,
            asset_name=ca.asset_name,
            algorithm=ca.algorithm,
            algorithm_family=ca.algorithm_family,
            primitive=ca.primitive,
            version=ca.version,
            key_size=ca.key_size,
            mode=ca.mode,
            protocol=ca.protocol,
            library_dependency=ca.library_dependency,
            usage_location=ca.usage_location,
            asset_type=ca.asset_type,
            source=ca.sources[0] if ca.sources else "unknown",
            sources=ca.sources,
            detection_confidence=ca.detection_confidence,
            dedup_key=ca.dedup_key,
        )
        db.add(row)
        db.flush()
        for e in ca.evidence:
            db.add(Evidence(
                asset_id=row.asset_id,
                location_kind=e.location_kind,
                location=e.location,
                line_or_offset=e.line_or_offset,
                function_or_scope=e.function_or_scope,
                matched_indicator=e.matched_indicator,
                surrounding_context=e.surrounding_context[:4000],
                confidence=e.confidence,
                detector=e.detector,
                signature_id=e.signature_id,
            ))
    db.flush()
