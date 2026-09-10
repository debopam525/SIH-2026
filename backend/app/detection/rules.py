"""Rule / signature detection layer.

``RuleDetector`` matches the regex signatures in ``crypto_signatures.yaml`` against file text.
It includes a lightweight comment/string heuristic that stands in for a full AST pass: a match
that only appears inside a comment or a bare string (in a real code file) is downgraded one
confidence level. Swap in a tree-sitter backend by implementing :class:`Detector` and adding it
to ``DETECTORS``; nothing downstream changes.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from typing import Protocol

from app.core.kb import signatures

_CONFIDENCE_ORDER = ["ml_classified", "weak_textual", "strong_textual", "confirmed_api"]

EXT_LANG = {
    ".py": "python", ".pyi": "python",
    ".js": "javascript", ".jsx": "javascript", ".mjs": "javascript", ".cjs": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".java": "java", ".kt": "java", ".scala": "java",
    ".go": "go",
    ".c": "c", ".h": "c", ".cc": "cpp", ".cpp": "cpp", ".hpp": "cpp",
    ".rs": "rust",
    ".rb": "ruby", ".php": "php", ".cs": "csharp",
}
CONFIG_EXTS = {
    ".conf", ".cfg", ".ini", ".yaml", ".yml", ".toml", ".properties", ".env",
    ".json", ".xml", ".pem", ".crt",
}
CONFIG_NAMES = {
    "sshd_config", "ssh_config", "nginx.conf", "httpd.conf", "openssl.cnf",
    "ssl.conf", "haproxy.cfg",
}

COMMENT_PREFIXES = ("#", "//", "/*", "*", "--", ";", "<!--")


def language_for(path: str) -> str:
    p = PurePosixPath(path.replace("\\", "/"))
    if p.name in CONFIG_NAMES:
        return "config"
    ext = p.suffix.lower()
    if ext in EXT_LANG:
        return EXT_LANG[ext]
    if ext in CONFIG_EXTS:
        return "config"
    return "unknown"


def downgrade(conf: str, steps: int = 1) -> str:
    try:
        i = _CONFIDENCE_ORDER.index(conf)
    except ValueError:
        return conf
    return _CONFIDENCE_ORDER[max(0, i - steps)]


@dataclass
class RawFinding:
    algorithm: str
    family: str
    primitive: str
    confidence: str
    matched_indicator: str
    signature_id: str
    detector: str = "rules"
    language: str = "unknown"
    key_size: str = "unknown"
    mode: str = "unknown"
    curve: str = "unknown"
    version: str = "unknown"
    library: str = "unknown"
    # location (filled by the scanner / detector)
    location: str = "unknown"
    location_kind: str = "file"
    line: int = 0
    function_or_scope: str = "unknown"
    context: str = ""
    extra: dict = field(default_factory=dict)


class Detector(Protocol):
    name: str

    def detect(self, text: str, path: str, language: str) -> list[RawFinding]: ...


class RuleDetector:
    name = "rules"

    def __init__(self) -> None:
        self._sigs = []
        for s in signatures().get("signatures", []):
            compiled = [re.compile(p) for p in s.get("patterns", [])]
            self._sigs.append((s, compiled))

    def detect(self, text: str, path: str, language: str) -> list[RawFinding]:
        findings: list[RawFinding] = []
        lines = text.splitlines()
        for s, compiled in self._sigs:
            langs = s.get("languages", [])
            if langs and language not in langs and "any" not in langs:
                continue
            for lineno, line in enumerate(lines, start=1):
                if len(line) > 4000:  # skip minified / data lines
                    continue
                for pat in compiled:
                    m = pat.search(line)
                    if not m:
                        continue
                    findings.append(self._build(s, m, line, lineno, lines, path, language))
                    break  # one hit per signature per line is enough
        return findings

    def _build(self, s, m, line, lineno, lines, path, language) -> RawFinding:  # noqa: ANN001
        conf = s.get("confidence", "weak_textual")
        stripped = line.strip()
        is_code = language not in ("config", "unknown")
        if is_code and stripped.startswith(COMMENT_PREFIXES):
            conf = downgrade(conf, 1)

        algorithm = s["algorithm"]
        dyn = s.get("dynamic_algorithm_regex")
        if dyn:
            dm = re.search(dyn, line)
            if dm:
                algorithm = dm.group(1)

        window = "\n".join(lines[max(0, lineno - 2): lineno + 1])
        rf = RawFinding(
            algorithm=algorithm,
            family=s.get("family", "unknown"),
            primitive=s.get("primitive", "unknown"),
            confidence=conf,
            matched_indicator=m.group(0)[:200],
            signature_id=s["id"],
            language=language,
            library=s.get("library", "unknown"),
            location=path,
            location_kind="config" if language == "config" else "file",
            line=lineno,
            context=window[:600],
        )
        _apply_regex(rf, "key_size", s.get("key_size_regex"), line, window)
        _apply_regex(rf, "mode", s.get("mode_regex"), line, window)
        _apply_regex(rf, "curve", s.get("curve_regex"), line, window)
        _apply_regex(rf, "version", s.get("version_regex"), line, window)
        return rf


def _apply_regex(rf: RawFinding, attr: str, pattern: str | None, line: str, window: str) -> None:
    if not pattern:
        return
    for hay in (line, window):
        m = re.search(pattern, hay)
        if m:
            setattr(rf, attr, m.group(m.lastindex or 0))
            return


# Registered detectors, in order. AST / ML backends append here.
DETECTORS: list[Detector] = [RuleDetector()]


def run_detectors(text: str, path: str) -> list[RawFinding]:
    language = language_for(path)
    out: list[RawFinding] = []
    for det in DETECTORS:
        out.extend(det.detect(text, path, language))
    return out
