"""Binary scanner (minimal): printable-string extraction + signature match, always downgraded.

Real deployments would add symbol-table parsing (pyelftools / LIEF) and an ML classifier for
ambiguous byte patterns behind the same interface. Findings here are never above
``weak_textual`` confidence.
"""
from __future__ import annotations

import re
import string

from app.detection.rules import RuleDetector, downgrade
from app.scanners.base import ScanContext, ScannerResult, iter_files, rel

_BIN_EXTS = {".so", ".dll", ".dylib", ".exe", ".bin", ".a", ".o", ".class", ".wasm", ".node"}
_PRINTABLE = set(string.printable.encode())
_MIN_RUN = 6


class BinaryScanner:
    name = "binary"
    scan_type = "binary"

    def __init__(self) -> None:
        self._rules = RuleDetector()

    def run(self, ctx: ScanContext) -> ScannerResult:
        res = ScannerResult(scanner=self.name)
        for path in iter_files(ctx.root):
            if path.suffix.lower() not in _BIN_EXTS:
                continue
            relpath = rel(ctx.root, path)
            res.files_scanned += 1
            try:
                blob = path.read_bytes()
            except Exception as exc:  # noqa: BLE001
                res.error(relpath, f"read failed: {exc}")
                continue
            strings_text = _extract_strings(blob)
            for rf in self._rules.detect(strings_text, relpath + ".strings", "unknown"):
                rf.confidence = downgrade(rf.confidence, 2)  # never trust binary strings much
                rf.detector = "binary-strings"
                rf.location = relpath
                rf.location_kind = "binary"
                rf.line = 0
                rf.context = f"matched in extracted strings of binary: {rf.matched_indicator}"
                rf.extra.update({"component": relpath.split("/")[-1], "scanner": self.name})
                res.findings.append(rf)
        return res


def _extract_strings(blob: bytes) -> str:
    out, run = [], bytearray()
    for b in blob:
        if b in _PRINTABLE and b not in (0x0a, 0x0d):
            run.append(b)
        else:
            if len(run) >= _MIN_RUN:
                out.append(run.decode("ascii", "replace"))
            run = bytearray()
    if len(run) >= _MIN_RUN:
        out.append(run.decode("ascii", "replace"))
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text)[:2_000_000]
