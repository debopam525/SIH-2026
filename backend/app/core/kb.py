"""Loaders for the YAML knowledge bases under ``app/data``.

Cached in-process; call :func:`reload` in tests or after editing files on disk.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml

from app.core.config import DATA_DIR


def _load(name: str) -> dict[str, Any]:
    path = DATA_DIR / name
    with path.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@lru_cache
def signatures() -> dict[str, Any]:
    return _load("crypto_signatures.yaml")


@lru_cache
def quantum_kb() -> dict[str, Any]:
    return _load("quantum_kb.yaml")


@lru_cache
def risk_defaults() -> dict[str, Any]:
    return _load("risk_weights.yaml")


@lru_cache
def pqc_mapping() -> dict[str, Any]:
    return _load("pqc_mapping.yaml")


def reload() -> None:
    for fn in (signatures, quantum_kb, risk_defaults, pqc_mapping):
        fn.cache_clear()
