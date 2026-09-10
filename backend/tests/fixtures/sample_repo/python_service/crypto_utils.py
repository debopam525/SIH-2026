"""Sample crypto usage for ECDAT detection tests (POSITIVE cases)."""
import hashlib
import hmac

from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


def generate_signing_key():
    # RSA-2048 for signing — quantum-vulnerable (Shor)
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


def encrypt_legacy(key: bytes, iv: bytes, data: bytes) -> bytes:
    # AES-128-CBC — weak key length under Grover, no AEAD
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    enc = cipher.encryptor()
    return enc.update(data) + enc.finalize()


def checksum_md5(data: bytes) -> str:
    # MD5 — already broken classically
    return hashlib.md5(data).hexdigest()


def checksum_sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def mac(key: bytes, msg: bytes) -> bytes:
    return hmac.new(key, msg, hashlib.sha256).digest()


def derive_key(password: bytes, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(algorithm=hashlib.sha256, length=32, salt=salt, iterations=200_000)
    return kdf.derive(password)
