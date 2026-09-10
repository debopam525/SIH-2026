"""Normalize heterogeneous :class:`RawFinding` objects into a canonical crypto identity.

Canonicalization is deliberately conservative: anything it cannot confidently resolve is left
as the literal string ``"unknown"`` (never guessed).
"""
from __future__ import annotations

import re
from dataclasses import dataclass

from app.core.kb import quantum_kb
from app.detection.rules import RawFinding
from app.models.base import UNKNOWN

# raw token (lower) -> (canonical algorithm, primitive hint)
_ALIAS: dict[str, tuple[str, str]] = {
    "rsa": ("RSA", "unknown"),
    "rsaes": ("RSA", "key-exchange"),
    "rsassa": ("RSA", "signature"),
    "rs256": ("RSA", "signature"), "rs384": ("RSA", "signature"), "rs512": ("RSA", "signature"),
    "ps256": ("RSA", "signature"), "ps384": ("RSA", "signature"),
    "dsa": ("DSA", "signature"),
    "dh": ("DH", "key-exchange"), "diffiehellman": ("DH", "key-exchange"),
    "dhe": ("DH", "key-exchange"),
    "ec": ("ECDSA", "signature"), "ecc": ("ECDSA", "signature"),
    "ecdsa": ("ECDSA", "signature"), "elliptic": ("ECDSA", "signature"),
    "es256": ("ECDSA", "signature"), "es384": ("ECDSA", "signature"), "es512": ("ECDSA", "signature"),
    "ecdh": ("ECDH", "key-exchange"), "ecdhe": ("ECDH", "key-exchange"),
    "ed25519": ("Ed25519", "signature"), "eddsa": ("Ed25519", "signature"),
    "ed448": ("Ed448", "signature"),
    "x25519": ("X25519", "key-exchange"), "x448": ("X448", "key-exchange"),
    "aes": ("AES", "cipher"),
    "aes128": ("AES", "cipher"), "aes192": ("AES", "cipher"), "aes256": ("AES", "cipher"),
    "aesgcm": ("AES", "cipher"), "aesccm": ("AES", "cipher"),
    "des": ("DES", "cipher"), "des3": ("3DES", "cipher"), "3des": ("3DES", "cipher"),
    "tripledes": ("3DES", "cipher"), "desede": ("3DES", "cipher"),
    "rc4": ("RC4", "cipher"), "arc4": ("RC4", "cipher"), "rc2": ("RC2", "cipher"),
    "blowfish": ("Blowfish", "cipher"), "twofish": ("Twofish", "cipher"),
    "camellia": ("Camellia", "cipher"), "chacha20": ("ChaCha20", "cipher"),
    "chacha20poly1305": ("ChaCha20", "cipher"),
    "md5": ("MD5", "hash"), "md4": ("MD4", "hash"), "md2": ("MD2", "hash"),
    "sha1": ("SHA-1", "hash"), "sha-1": ("SHA-1", "hash"),
    "sha224": ("SHA-224", "hash"), "sha-224": ("SHA-224", "hash"),
    "sha256": ("SHA-256", "hash"), "sha-256": ("SHA-256", "hash"),
    "sha384": ("SHA-384", "hash"), "sha-384": ("SHA-384", "hash"),
    "sha512": ("SHA-512", "hash"), "sha-512": ("SHA-512", "hash"),
    "sha3": ("SHA-3", "hash"), "sha3-256": ("SHA-3", "hash"), "sha3_256": ("SHA-3", "hash"),
    "sha3-512": ("SHA-3", "hash"),
    "blake2": ("BLAKE2", "hash"), "blake2b": ("BLAKE2", "hash"), "blake3": ("BLAKE3", "hash"),
    "ripemd160": ("RIPEMD-160", "hash"),
    "hmac": ("HMAC", "mac"),
    "hs256": ("HMAC", "mac"), "hs384": ("HMAC", "mac"), "hs512": ("HMAC", "mac"),
    "poly1305": ("Poly1305", "mac"), "cmac": ("CMAC", "mac"), "gmac": ("GMAC", "mac"),
    "pbkdf2": ("PBKDF2", "kdf"), "pbkdf2hmac": ("PBKDF2", "kdf"),
    "scrypt": ("scrypt", "kdf"), "bcrypt": ("bcrypt", "kdf"),
    "argon2": ("Argon2", "kdf"), "argon2id": ("Argon2", "kdf"), "hkdf": ("HKDF", "kdf"),
    "tls": ("TLS", "protocol"), "ssl": ("TLS", "protocol"), "dtls": ("DTLS", "protocol"),
    "ssh": ("SSH", "protocol"), "ipsec": ("IPsec", "protocol"), "ike": ("IKE", "protocol"),
    "ml-kem": ("ML-KEM", "kem"), "mlkem": ("ML-KEM", "kem"),
    "kyber512": ("ML-KEM", "kem"), "kyber768": ("ML-KEM", "kem"), "kyber1024": ("ML-KEM", "kem"),
    "kyber": ("ML-KEM", "kem"),
    "ml-dsa": ("ML-DSA", "signature"), "mldsa": ("ML-DSA", "signature"),
    "dilithium2": ("ML-DSA", "signature"), "dilithium3": ("ML-DSA", "signature"),
    "dilithium5": ("ML-DSA", "signature"), "dilithium": ("ML-DSA", "signature"),
    "slh-dsa": ("SLH-DSA", "signature"), "sphincs": ("SLH-DSA", "signature"),
    "falcon": ("Falcon", "signature"),
    # Go crypto/* import leaves
    "rc": ("RC4", "cipher"),
}

_FAMILY_BY_ALGO: dict[str, str] = {}
for _fam, _spec in quantum_kb().get("families", {}).items():
    for _a in _spec.get("algorithms", []):
        _FAMILY_BY_ALGO[_a.lower()] = _fam


@dataclass
class NormalizedAsset:
    algorithm: str
    algorithm_family: str
    primitive: str
    key_size: str
    mode: str
    version: str
    protocol: str
    curve: str
    library_dependency: str
    detection_confidence: str

    def crypto_identity(self) -> str:
        return "|".join(
            [self.algorithm, self.key_size, self.mode, self.version, self.protocol, self.curve]
        )


def _canon_algorithm(raw: str) -> tuple[str, str]:
    token = re.sub(r"[^a-z0-9+-]", "", raw.lower())
    if token in _ALIAS:
        return _ALIAS[token]
    # combined forms like aes-256-gcm / aes_256_cbc
    base = re.split(r"[-_]", raw.lower())[0]
    base = re.sub(r"[^a-z0-9]", "", base)
    if base in _ALIAS:
        return _ALIAS[base]
    # already-canonical / unknown
    if raw and raw.upper() == raw and raw not in ("DYNAMIC",):
        return raw, "unknown"
    return raw or UNKNOWN, "unknown"


def _extract_keysize(rf: RawFinding, algorithm: str) -> str:
    if rf.key_size and rf.key_size != UNKNOWN and rf.key_size.isdigit():
        return rf.key_size
    for tok in re.split(r"[-_ ]", rf.algorithm):
        if tok.isdigit() and int(tok) in (56, 64, 112, 128, 192, 256, 384, 512, 1024, 2048, 3072, 4096):
            return tok
    if algorithm in ("SHA-256",):
        return "256"
    if algorithm in ("SHA-384",):
        return "384"
    if algorithm in ("SHA-512", "SHA-1", "MD5"):
        return {"SHA-512": "512", "SHA-1": "160", "MD5": "128"}[algorithm]
    return UNKNOWN


def normalize(rf: RawFinding) -> NormalizedAsset:
    algorithm, prim_hint = _canon_algorithm(rf.algorithm)
    primitive = rf.primitive if rf.primitive not in (UNKNOWN, "") else prim_hint
    if primitive in (UNKNOWN, ""):
        primitive = UNKNOWN

    family = rf.family
    if family in (UNKNOWN, "", "pqc-kem", "pqc-signature") or family.startswith("DYNAMIC"):
        family = _FAMILY_BY_ALGO.get(algorithm.lower(), family if family != "" else UNKNOWN)
    if family in (UNKNOWN, "") :
        family = _FAMILY_BY_ALGO.get(algorithm.lower(), UNKNOWN)

    key_size = _extract_keysize(rf, algorithm)
    mode = rf.mode.upper() if rf.mode not in (UNKNOWN, "") else UNKNOWN
    curve = rf.curve if rf.curve not in (UNKNOWN, "") else UNKNOWN
    protocol = UNKNOWN
    version = rf.version if rf.version not in (UNKNOWN, "") else UNKNOWN
    if family == "protocol":
        protocol = algorithm
        version = rf.version if rf.version not in (UNKNOWN, "") else UNKNOWN

    return NormalizedAsset(
        algorithm=algorithm,
        algorithm_family=family,
        primitive=primitive,
        key_size=key_size,
        mode=mode,
        version=version,
        protocol=protocol,
        curve=curve,
        library_dependency=rf.library or UNKNOWN,
        detection_confidence=rf.confidence,
    )
