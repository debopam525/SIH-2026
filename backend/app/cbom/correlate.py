"""Correlate + deduplicate raw findings from every scanner into CBOM assets.

Dedup strategy (deterministic, explainable):

1. Normalise each finding to a canonical crypto identity
   (algorithm | key_size | mode | version | protocol | curve).
2. Primary merge key = ``crypto_identity | scope`` where ``scope`` is the library/package for
   dependency & container findings, otherwise the source component (top dir) / config filename.
   All findings with the same key become ONE asset; every finding contributes an Evidence row.
3. Post-merge: within a crypto-identity group, if a code/config asset names a library that also
   appears as a standalone dependency asset, the dependency asset's evidence is folded in and
   the standalone record dropped. This is what stops source + dependency double-counting.

The highest evidence confidence in an asset becomes its ``detection_confidence``.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.detection.normalization import _ALIAS, normalize
from app.detection.rules import RawFinding
from app.models.base import UNKNOWN

_KNOWN_ALGOS = {v[0].lower() for v in _ALIAS.values()}


def _is_noise(algorithm: str, family: str, confidence: str) -> bool:
    """Drop weak generic key/value hits that did not resolve to a real primitive."""
    return (
        confidence == "weak_textual"
        and family == UNKNOWN
        and algorithm.lower() not in _KNOWN_ALGOS
    )

_CONF_RANK = {"weak_textual": 0, "ml_classified": 1, "strong_textual": 2, "confirmed_api": 3}
_CODE_SCANNERS = {"source", "config", "binary"}


@dataclass
class EvidenceItem:
    location_kind: str
    location: str
    line_or_offset: str
    function_or_scope: str
    matched_indicator: str
    surrounding_context: str
    confidence: str
    detector: str
    signature_id: str


@dataclass
class CorrelatedAsset:
    algorithm: str
    algorithm_family: str
    primitive: str
    key_size: str
    mode: str
    version: str
    protocol: str
    curve: str
    library_dependency: str
    asset_type: str
    sources: list[str]
    detection_confidence: str
    dedup_key: str
    scope: str
    usage_location: str
    evidence: list[EvidenceItem] = field(default_factory=list)

    @property
    def asset_name(self) -> str:
        bits = [self.algorithm]
        if self.key_size != UNKNOWN:
            bits.append(self.key_size)
        if self.mode != UNKNOWN:
            bits.append(self.mode)
        if self.version != UNKNOWN and self.protocol != UNKNOWN:
            bits.append(self.version)
        return "-".join(bits) + f" @ {self.scope}"


def _asset_type_for(scanner: str, family: str) -> str:
    if scanner == "dependency":
        return "dependency"
    if scanner == "config":
        return "protocol-config" if family == "protocol" else "config-setting"
    if scanner == "binary":
        return "binary-symbol"
    if scanner == "container":
        return "container-package"
    return "library-call"


def correlate(findings: list[RawFinding]) -> list[CorrelatedAsset]:
    buckets: dict[str, CorrelatedAsset] = {}

    for rf in findings:
        na = normalize(rf)
        if _is_noise(na.algorithm, na.algorithm_family, rf.confidence):
            continue
        scanner = rf.extra.get("scanner", rf.detector)
        if scanner in ("dependency", "container"):
            scope = (rf.library or rf.extra.get("component") or "(dep)")
        else:
            scope = rf.extra.get("component") or "(root)"
        identity = na.crypto_identity()
        key = f"{identity}|{scope}"

        ev = EvidenceItem(
            location_kind=rf.location_kind,
            location=rf.location,
            line_or_offset=str(rf.line) if rf.line else "unknown",
            function_or_scope=rf.function_or_scope,
            matched_indicator=rf.matched_indicator,
            surrounding_context=rf.context,
            confidence=rf.confidence,
            detector=rf.detector,
            signature_id=rf.signature_id,
        )

        if key not in buckets:
            buckets[key] = CorrelatedAsset(
                algorithm=na.algorithm,
                algorithm_family=na.algorithm_family,
                primitive=na.primitive,
                key_size=na.key_size,
                mode=na.mode,
                version=na.version,
                protocol=na.protocol,
                curve=na.curve,
                library_dependency=na.library_dependency,
                asset_type=_asset_type_for(scanner, na.algorithm_family),
                sources=[scanner],
                detection_confidence=rf.confidence,
                dedup_key=key,
                scope=scope,
                usage_location=rf.location,
            )
        asset = buckets[key]
        asset.evidence.append(ev)
        if scanner not in asset.sources:
            asset.sources.append(scanner)
        if _CONF_RANK.get(rf.confidence, 0) > _CONF_RANK.get(asset.detection_confidence, 0):
            asset.detection_confidence = rf.confidence
        # fill in unknowns opportunistically (never overwrite a known value)
        for f in ("key_size", "mode", "version", "curve", "primitive", "library_dependency"):
            if getattr(asset, f) == UNKNOWN:
                v = getattr(na, f, UNKNOWN)
                if v and v != UNKNOWN:
                    setattr(asset, f, v)

    return _post_merge(list(buckets.values()))


def _post_merge(assets: list[CorrelatedAsset]) -> list[CorrelatedAsset]:
    """Fold standalone dependency assets into code assets that name the same library."""
    by_identity: dict[str, list[CorrelatedAsset]] = {}
    for a in assets:
        by_identity.setdefault(_identity(a), []).append(a)

    dropped: set[int] = set()
    for group in by_identity.values():
        code_assets = [a for a in group if any(s in _CODE_SCANNERS for s in a.sources)
                       and a.library_dependency != UNKNOWN]
        dep_assets = [a for a in group if a.sources == ["dependency"]]
        for dep in dep_assets:
            for code in code_assets:
                if code.library_dependency.lower() == dep.scope.lower():
                    code.evidence.extend(dep.evidence)
                    if "dependency" not in code.sources:
                        code.sources.append("dependency")
                    dropped.add(id(dep))
                    break
    return [a for a in assets if id(a) not in dropped]


def _identity(a: CorrelatedAsset) -> str:
    return "|".join([a.algorithm, a.key_size, a.mode, a.version, a.protocol, a.curve])
