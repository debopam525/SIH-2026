"""Dependency scanner: map declared packages to the crypto they provide.

Correlation with source findings happens in the CBOM correlator; here we just emit one
``RawFinding`` per (package, capability). Direct vs transitive is tracked where the lockfile
exposes it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from app.detection.rules import RawFinding
from app.scanners.base import ScanContext, ScannerResult, iter_files, read_text, rel

# package (lowercased) -> {ecosystem, caps: [(algorithm, family, primitive)], note}
CRYPTO_PACKAGES: dict[str, dict] = {
    # --- PyPI
    "cryptography": {"eco": "pypi", "caps": [("AES", "symmetric", "cipher"), ("RSA", "public-key", "signature"), ("ECDSA", "elliptic-curve", "signature"), ("Ed25519", "elliptic-curve", "signature")], "note": "pyca/cryptography - broad primitive coverage"},
    "pycryptodome": {"eco": "pypi", "caps": [("AES", "symmetric", "cipher"), ("RSA", "public-key", "key-exchange"), ("SHA-256", "hash", "hash")], "note": ""},
    "pycrypto": {"eco": "pypi", "caps": [("AES", "symmetric", "cipher"), ("RSA", "public-key", "key-exchange")], "note": "unmaintained - flag for replacement"},
    "pyopenssl": {"eco": "pypi", "caps": [("TLS", "protocol", "protocol"), ("RSA", "public-key", "signature")], "note": ""},
    "pynacl": {"eco": "pypi", "caps": [("X25519", "elliptic-curve", "key-exchange"), ("Ed25519", "elliptic-curve", "signature")], "note": "libsodium bindings"},
    "rsa": {"eco": "pypi", "caps": [("RSA", "public-key", "signature")], "note": ""},
    "ecdsa": {"eco": "pypi", "caps": [("ECDSA", "elliptic-curve", "signature")], "note": ""},
    "bcrypt": {"eco": "pypi", "caps": [("bcrypt", "kdf", "kdf")], "note": ""},
    "passlib": {"eco": "pypi", "caps": [("PBKDF2", "kdf", "kdf"), ("bcrypt", "kdf", "kdf")], "note": ""},
    "argon2-cffi": {"eco": "pypi", "caps": [("Argon2", "kdf", "kdf")], "note": ""},
    "paramiko": {"eco": "pypi", "caps": [("SSH", "protocol", "protocol")], "note": ""},
    "pyjwt": {"eco": "pypi", "caps": [("HMAC", "mac", "mac"), ("RSA", "public-key", "signature")], "note": "JWT signing"},
    "oqs": {"eco": "pypi", "caps": [("ML-KEM", "pqc-kem", "kem"), ("ML-DSA", "pqc-signature", "signature")], "note": "liboqs - already PQC"},
    "liboqs-python": {"eco": "pypi", "caps": [("ML-KEM", "pqc-kem", "kem")], "note": "already PQC"},
    "pqcrypto": {"eco": "pypi", "caps": [("ML-KEM", "pqc-kem", "kem"), ("ML-DSA", "pqc-signature", "signature")], "note": "already PQC"},
    # --- npm
    "node-forge": {"eco": "npm", "caps": [("RSA", "public-key", "signature"), ("AES", "symmetric", "cipher"), ("SHA-1", "hash", "hash")], "note": ""},
    "crypto-js": {"eco": "npm", "caps": [("AES", "symmetric", "cipher"), ("MD5", "hash", "hash"), ("SHA-1", "hash", "hash")], "note": "ships MD5/SHA-1 helpers"},
    "bcryptjs": {"eco": "npm", "caps": [("bcrypt", "kdf", "kdf")], "note": ""},
    "jsonwebtoken": {"eco": "npm", "caps": [("RSA", "public-key", "signature"), ("HMAC", "mac", "mac")], "note": ""},
    "jose": {"eco": "npm", "caps": [("ECDSA", "elliptic-curve", "signature"), ("RSA", "public-key", "signature")], "note": ""},
    "tweetnacl": {"eco": "npm", "caps": [("X25519", "elliptic-curve", "key-exchange"), ("Ed25519", "elliptic-curve", "signature")], "note": ""},
    "elliptic": {"eco": "npm", "caps": [("ECDSA", "elliptic-curve", "signature")], "note": ""},
    "sjcl": {"eco": "npm", "caps": [("AES", "symmetric", "cipher")], "note": ""},
    "node-rsa": {"eco": "npm", "caps": [("RSA", "public-key", "key-exchange")], "note": ""},
    "libsodium-wrappers": {"eco": "npm", "caps": [("X25519", "elliptic-curve", "key-exchange")], "note": ""},
    "pqc-kyber": {"eco": "npm", "caps": [("ML-KEM", "pqc-kem", "kem")], "note": "already PQC"},
    # --- Maven (matched as substrings of <artifactId>)
    "bcprov": {"eco": "maven", "caps": [("AES", "symmetric", "cipher"), ("RSA", "public-key", "signature"), ("ECDSA", "elliptic-curve", "signature")], "note": "Bouncy Castle provider"},
    "bcpkix": {"eco": "maven", "caps": [("TLS", "protocol", "protocol")], "note": "Bouncy Castle PKIX"},
    "tink": {"eco": "maven", "caps": [("AES", "symmetric", "cipher"), ("ECDSA", "elliptic-curve", "signature")], "note": "Google Tink"},
    "nimbus-jose-jwt": {"eco": "maven", "caps": [("RSA", "public-key", "signature"), ("ECDSA", "elliptic-curve", "signature")], "note": ""},
    # --- Go modules
    "golang.org/x/crypto": {"eco": "go", "caps": [("Ed25519", "elliptic-curve", "signature"), ("ChaCha20", "symmetric", "cipher")], "note": ""},
    "github.com/cloudflare/circl": {"eco": "go", "caps": [("ML-KEM", "pqc-kem", "kem"), ("ML-DSA", "pqc-signature", "signature")], "note": "CIRCL - already PQC"},
    # --- Cargo  (note: `rsa` covered by the PyPI entry above; the crate has identical caps)
    "ring": {"eco": "cargo", "caps": [("AES", "symmetric", "cipher"), ("Ed25519", "elliptic-curve", "signature")], "note": ""},
    "ed25519-dalek": {"eco": "cargo", "caps": [("Ed25519", "elliptic-curve", "signature")], "note": ""},
    "aes-gcm": {"eco": "cargo", "caps": [("AES", "symmetric", "cipher")], "note": ""},
    "ml-kem": {"eco": "cargo", "caps": [("ML-KEM", "pqc-kem", "kem")], "note": "already PQC"},
    "pqcrypto-kyber": {"eco": "cargo", "caps": [("ML-KEM", "pqc-kem", "kem")], "note": "already PQC"},
}

_MANIFESTS = {
    "requirements.txt", "requirements-dev.txt", "pipfile", "pyproject.toml", "setup.py",
    "package.json", "package-lock.json", "pnpm-lock.yaml", "yarn.lock",
    "pom.xml", "build.gradle", "go.mod", "go.sum", "cargo.toml", "cargo.lock",
}


class DependencyScanner:
    name = "dependency"
    scan_type = "dependency"

    def run(self, ctx: ScanContext) -> ScannerResult:
        res = ScannerResult(scanner=self.name)
        for path in iter_files(ctx.root):
            if path.name.lower() not in _MANIFESTS:
                continue
            relpath = rel(ctx.root, path)
            res.files_scanned += 1
            try:
                text = read_text(path)
            except Exception as exc:  # noqa: BLE001
                res.error(relpath, f"read failed: {exc}")
                continue
            try:
                for pkg, version, relation in _parse_manifest(path, text):
                    entry = CRYPTO_PACKAGES.get(pkg.lower())
                    if not entry:
                        continue
                    for algo, family, primitive in entry["caps"]:
                        res.findings.append(_finding(relpath, pkg, version, relation, entry,
                                                     algo, family, primitive))
            except Exception as exc:  # noqa: BLE001
                res.error(relpath, f"parse failed: {exc}")
        return res


def _finding(relpath, pkg, version, relation, entry, algo, family, primitive) -> RawFinding:  # noqa: ANN001
    rf = RawFinding(
        algorithm=algo, family=family, primitive=primitive,
        confidence="confirmed_api",
        matched_indicator=f"{pkg} {version}".strip(),
        signature_id=f"dep:{entry['eco']}:{pkg.lower()}",
        detector="dependency",
        language="dependency",
        library=pkg,
        version=version or "unknown",
        location=relpath,
        location_kind="file",
        context=f"{relation} dependency '{pkg}' ({entry['eco']}) provides {algo}. {entry['note']}".strip(),
    )
    rf.extra.update({"component": pkg, "scanner": "dependency", "relation": relation,
                     "ecosystem": entry["eco"]})
    return rf


def _parse_manifest(path: Path, text: str) -> list[tuple[str, str, str]]:
    name = path.name.lower()
    if name in ("requirements.txt", "requirements-dev.txt"):
        return _parse_requirements(text)
    if name == "package.json":
        return _parse_package_json(text)
    if name == "package-lock.json":
        return _parse_package_lock(text)
    if name == "pom.xml":
        return _parse_pom(text)
    if name in ("go.mod", "go.sum"):
        return _parse_go(text, transitive=(name == "go.sum"))
    if name in ("cargo.toml", "pyproject.toml", "pipfile"):
        return _parse_toml_like(text)
    if name in ("cargo.lock",):
        return _parse_cargo_lock(text)
    return []


def _parse_requirements(text: str) -> list[tuple[str, str, str]]:
    out = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        m = re.match(r"^([A-Za-z0-9_.\-]+)\s*(?:[=<>!~]=?\s*([0-9][\w.\-]*))?", line)
        if m:
            out.append((m.group(1), m.group(2) or "unknown", "direct"))
    return out


def _parse_package_json(text: str) -> list[tuple[str, str, str]]:
    data = json.loads(text)
    out = []
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        for pkg, ver in (data.get(key) or {}).items():
            out.append((pkg, str(ver).lstrip("^~"), "direct"))
    return out


def _parse_package_lock(text: str) -> list[tuple[str, str, str]]:
    data = json.loads(text)
    out = []
    pkgs = data.get("packages")
    if isinstance(pkgs, dict):
        for loc, meta in pkgs.items():
            if not loc:
                continue
            pkg = loc.split("node_modules/")[-1]
            rel_ = "direct" if meta.get("dev") is None and loc.count("node_modules") <= 1 else "transitive"
            out.append((pkg, str(meta.get("version", "unknown")), rel_))
    for pkg, meta in (data.get("dependencies") or {}).items():
        out.append((pkg, str(meta.get("version", "unknown")), "direct"))
    return out


def _parse_pom(text: str) -> list[tuple[str, str, str]]:
    out = []
    for m in re.finditer(r"<artifactId>([^<]+)</artifactId>\s*(?:<version>([^<]+)</version>)?", text):
        out.append((m.group(1).strip(), (m.group(2) or "unknown").strip(), "direct"))
    return out


def _parse_go(text: str, *, transitive: bool) -> list[tuple[str, str, str]]:
    out = []
    for m in re.finditer(r"^\s*([\w./\-]+)\s+v([\w.\-]+)", text, re.MULTILINE):
        mod = m.group(1)
        out.append((mod, "v" + m.group(2), "transitive" if transitive else "direct"))
        # also match known map keys that are prefixes
        for key in CRYPTO_PACKAGES:
            if key.startswith("github.com") or key.startswith("golang.org"):
                if mod == key:
                    out.append((key, "v" + m.group(2), "transitive" if transitive else "direct"))
    return out


def _parse_toml_like(text: str) -> list[tuple[str, str, str]]:
    out = []
    for m in re.finditer(r'^\s*([A-Za-z0-9_.\-]+)\s*=\s*[\{"]?\s*(?:version\s*=\s*)?"?([0-9][\w.\-]*)?',
                         text, re.MULTILINE):
        out.append((m.group(1), m.group(2) or "unknown", "direct"))
    return out


def _parse_cargo_lock(text: str) -> list[tuple[str, str, str]]:
    out = []
    blocks = text.split("[[package]]")
    for b in blocks[1:]:
        nm = re.search(r'name\s*=\s*"([^"]+)"', b)
        vm = re.search(r'version\s*=\s*"([^"]+)"', b)
        if nm:
            out.append((nm.group(1), vm.group(1) if vm else "unknown", "transitive"))
    return out
