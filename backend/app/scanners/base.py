from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

from app.detection.rules import RawFinding

SCANNER_VERSION = "0.1.0"

# Directories never worth walking.
SKIP_DIRS = {
    ".git", ".hg", ".svn", "node_modules", ".venv", "venv", "__pycache__", "dist", "build",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox", ".idea", ".vscode", "target",
    "vendor", ".next", ".cache", "site-packages",
}
MAX_FILE_BYTES = 2_000_000


@dataclass
class ScanContext:
    root: Path
    scan_id: str
    scan_types: list[str]


@dataclass
class ScannerResult:
    scanner: str
    findings: list[RawFinding] = field(default_factory=list)
    files_scanned: int = 0
    errors: list[dict] = field(default_factory=list)

    def error(self, path: str, message: str) -> None:
        self.errors.append({"scanner": self.scanner, "path": path, "error": message})


class Scanner(Protocol):
    name: str
    scan_type: str

    def run(self, ctx: ScanContext) -> ScannerResult: ...


def iter_files(root: Path):
    """Yield files under ``root`` skipping noise dirs and oversized files."""
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                continue
        except OSError:
            continue
        yield path


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def rel(root: Path, path: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


def component_of(relpath: str) -> str:
    """First meaningful path segment — used as the dedup 'scope' so call sites in the same
    component merge into one asset but different components stay distinct."""
    parts = [p for p in relpath.split("/") if p not in (".", "")]
    if len(parts) <= 1:
        return "(root)"
    if parts[0] in ("src", "lib", "app", "pkg", "internal", "cmd") and len(parts) > 2:
        return f"{parts[0]}/{parts[1]}"
    return parts[0]
