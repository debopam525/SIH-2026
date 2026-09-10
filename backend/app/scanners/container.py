"""Container scanner (minimal): parse Dockerfiles + any embedded configs / installed-package
lists found in the tree. A full implementation would pull and unpack image layers (skopeo /
containers-image) and inventory each layer's packages; that plugs in behind this interface.
"""
from __future__ import annotations

import re

from app.detection.rules import RawFinding
from app.scanners.base import ScanContext, ScannerResult, iter_files, read_text, rel
from app.scanners.dependency import CRYPTO_PACKAGES

_APT_INSTALL = re.compile(r"(?:apt-get|apk|yum|dnf)\s+(?:add|install)\s+([^\n&|]+)", re.IGNORECASE)
_PIP_INSTALL = re.compile(r"pip3?\s+install\s+([^\n&|]+)", re.IGNORECASE)
_BASE_IMAGE = re.compile(r"^\s*FROM\s+(\S+)", re.IGNORECASE | re.MULTILINE)

_OS_CRYPTO = {"openssl", "libssl-dev", "libssl", "gnutls", "libgcrypt", "libsodium", "nss"}


class ContainerScanner:
    name = "container"
    scan_type = "container"

    def run(self, ctx: ScanContext) -> ScannerResult:
        res = ScannerResult(scanner=self.name)
        for path in iter_files(ctx.root):
            if not (path.name.lower() == "dockerfile" or path.name.lower().startswith("dockerfile")
                    or path.name.lower() == "containerfile"):
                continue
            relpath = rel(ctx.root, path)
            res.files_scanned += 1
            try:
                text = read_text(path)
            except Exception as exc:  # noqa: BLE001
                res.error(relpath, f"read failed: {exc}")
                continue
            self._scan_dockerfile(text, relpath, res)
        return res

    def _scan_dockerfile(self, text: str, relpath: str, res: ScannerResult) -> None:
        base = _BASE_IMAGE.search(text)
        base_img = base.group(1) if base else "unknown"
        pkgs: set[str] = set()
        for m in _APT_INSTALL.finditer(text):
            pkgs.update(re.split(r"\s+", m.group(1).strip()))
        for m in _PIP_INSTALL.finditer(text):
            pkgs.update(re.split(r"\s+", m.group(1).strip()))
        pkgs = {p for p in pkgs if p and not p.startswith("-")}

        for pkg in sorted(pkgs):
            key = pkg.lower()
            if key in _OS_CRYPTO:
                rf = RawFinding(
                    algorithm="TLS", family="protocol", primitive="protocol",
                    confidence="weak_textual",
                    matched_indicator=f"{pkg} installed in image",
                    signature_id=f"container:os:{key}", detector="container",
                    language="container", library=pkg,
                    location=relpath, location_kind="container",
                    context=f"OS crypto library '{pkg}' installed in container (base image {base_img}).",
                )
                rf.extra.update({"component": base_img, "scanner": self.name, "base_image": base_img})
                res.findings.append(rf)
            entry = CRYPTO_PACKAGES.get(key)
            if entry:
                for algo, fam, prim in entry["caps"]:
                    rf = RawFinding(
                        algorithm=algo, family=fam, primitive=prim,
                        confidence="weak_textual",
                        matched_indicator=f"{pkg} installed in image",
                        signature_id=f"container:pkg:{key}", detector="container",
                        language="container", library=pkg,
                        location=relpath, location_kind="container",
                        context=f"Package '{pkg}' installed in container image (base {base_img}).",
                    )
                    rf.extra.update({"component": base_img, "scanner": self.name,
                                     "base_image": base_img})
                    res.findings.append(rf)
