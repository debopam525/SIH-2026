"""Source-code scanner: walk the tree, run the detection layer on each code/text file."""
from __future__ import annotations

from app.detection.rules import language_for, run_detectors
from app.scanners.base import (
    ScanContext,
    ScannerResult,
    component_of,
    iter_files,
    read_text,
    rel,
)

_CODE_LANGS = {
    "python", "javascript", "typescript", "java", "go", "c", "cpp", "rust", "ruby", "php",
    "csharp",
}


class SourceScanner:
    name = "source"
    scan_type = "source"

    def run(self, ctx: ScanContext) -> ScannerResult:
        res = ScannerResult(scanner=self.name)
        for path in iter_files(ctx.root):
            lang = language_for(str(path))
            if lang not in _CODE_LANGS:
                continue
            relpath = rel(ctx.root, path)
            res.files_scanned += 1
            try:
                text = read_text(path)
            except Exception as exc:  # noqa: BLE001
                res.error(relpath, f"read failed: {exc}")
                continue
            try:
                for rf in run_detectors(text, relpath):
                    rf.location = relpath
                    rf.location_kind = "file"
                    rf.function_or_scope = _enclosing_scope(text, rf.line)
                    rf.extra["component"] = component_of(relpath)
                    rf.extra["scanner"] = self.name
                    res.findings.append(rf)
            except Exception as exc:  # noqa: BLE001
                res.error(relpath, f"detection failed: {exc}")
        return res


def _enclosing_scope(text: str, line: int) -> str:
    """Best-effort nearest def/func/class above the match (no AST dependency)."""
    lines = text.splitlines()
    import re

    pat = re.compile(r"^\s*(?:def |class |func |function |public |private |static ).*?([A-Za-z_]\w*)\s*[\(:]")
    for i in range(min(line, len(lines)) - 1, -1, -1):
        m = pat.match(lines[i])
        if m:
            return m.group(1)
    return "unknown"
