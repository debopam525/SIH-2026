"""Configuration scanner: TLS/SSH/OpenSSL/webserver configs + generic key/value crypto settings.

Runs the same detection layer as the source scanner but only over config-shaped files, then
enriches findings with parsed protocol versions and cipher-suite hints.
"""
from __future__ import annotations

import re

from app.detection.rules import language_for, run_detectors
from app.scanners.base import ScanContext, ScannerResult, iter_files, read_text, rel

_CONFIG_FILE_HINTS = re.compile(
    r"(sshd?_config|ssl|tls|nginx|apache|httpd|openssl|haproxy|\.pem$|\.crt$|\.cnf$|\.conf$|"
    r"\.cfg$|\.ini$|\.properties$|\.toml$|\.ya?ml$|\.env$)",
    re.IGNORECASE,
)
_TLS_VER = re.compile(r"(TLSv1\.3|TLSv1\.2|TLSv1\.1|TLSv1|SSLv3|SSLv2|DTLSv1\.2)", re.IGNORECASE)
_WEAK_SUITE = re.compile(r"\b(RC4|DES|3DES|MD5|NULL|EXPORT|aNULL|eNULL|CBC)\b")


class ConfigScanner:
    name = "config"
    scan_type = "config"

    def run(self, ctx: ScanContext) -> ScannerResult:
        res = ScannerResult(scanner=self.name)
        for path in iter_files(ctx.root):
            if not _CONFIG_FILE_HINTS.search(path.name) and language_for(str(path)) != "config":
                continue
            relpath = rel(ctx.root, path)
            res.files_scanned += 1
            try:
                text = read_text(path)
            except Exception as exc:  # noqa: BLE001
                res.error(relpath, f"read failed: {exc}")
                continue
            try:
                self._scan_text(text, relpath, res)
            except Exception as exc:  # noqa: BLE001
                res.error(relpath, f"detection failed: {exc}")
        return res

    def _scan_text(self, text: str, relpath: str, res: ScannerResult) -> None:
        lines = text.splitlines()
        for rf in run_detectors(text, relpath if relpath.endswith((".conf", ".cfg", ".cnf", ".ini"))
                                else relpath + ".conf"):
            rf.location = relpath
            rf.location_kind = "config"
            line_txt = lines[rf.line - 1] if 0 < rf.line <= len(lines) else ""
            vm = _TLS_VER.search(line_txt) or _TLS_VER.search(rf.context)
            if vm and rf.version in ("unknown", ""):
                rf.version = vm.group(1)
            weak = sorted({w.upper() for w in _WEAK_SUITE.findall(line_txt)})
            if weak:
                rf.extra["weak_tokens"] = weak
                rf.context = (rf.context + f"  [weak tokens: {', '.join(weak)}]").strip()
            rf.extra["component"] = relpath.split("/")[-1]
            rf.extra["scanner"] = self.name
            res.findings.append(rf)
