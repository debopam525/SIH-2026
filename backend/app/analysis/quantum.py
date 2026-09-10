"""Quantum vulnerability engine.

Verdict is derived from (family baseline) + (context rules on key_size / mode / protocol
version). It NEVER decides from the algorithm name alone, and always returns an explanation.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.core.kb import quantum_kb

# posture keyword feeds the risk engine's `cryptographic_strength` normaliser
_POSTURE_BY_STATUS = {
    "broken-classical": "broken",
    "quantum-vulnerable": "legacy",
    "quantum-weakened": "acceptable",
    "quantum-safe": "strong",
    "unknown": "unknown",
}


@dataclass
class QuantumVerdict:
    status: str  # quantum-vulnerable | quantum-weakened | quantum-safe | broken-classical | unknown
    shor_impact: str
    grover_impact: str
    posture: str
    harvest_now_decrypt_later: bool
    explanation: str
    context_notes: list[str] = field(default_factory=list)
    matched_family: str = "unknown"


def _to_int(v: str | int | None) -> int | None:
    if v is None:
        return None
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def _family_for(algorithm: str, family_hint: str, kb_families: dict) -> tuple[str, dict]:
    if family_hint in kb_families:
        return family_hint, kb_families[family_hint]
    al = algorithm.lower()
    for fam, spec in kb_families.items():
        if al in [a.lower() for a in spec.get("algorithms", [])]:
            return fam, spec
    return "unknown", {}


def _rule_matches(rule_when: dict, *, algorithm: str, family: str, key_size: int | None,
                  mode: str, protocol_version: str) -> bool:
    if "algorithm" in rule_when and rule_when["algorithm"].lower() != algorithm.lower():
        return False
    if "family" in rule_when and rule_when["family"] != family:
        return False
    if "key_size_min" in rule_when and (key_size is None or key_size < rule_when["key_size_min"]):
        return False
    if "key_size_max" in rule_when and (key_size is None or key_size > rule_when["key_size_max"]):
        return False
    if "mode_in" in rule_when:
        if not mode or mode.upper() not in [m.upper() for m in rule_when["mode_in"]]:
            return False
    if "protocol_version_in" in rule_when:
        pv = (protocol_version or "").upper().replace(" ", "")
        opts = [x.upper().replace(" ", "") for x in rule_when["protocol_version_in"]]
        if pv not in opts:
            return False
    return True


def assess(
    *,
    algorithm: str,
    algorithm_family: str = "unknown",
    key_size: str | int | None = None,
    mode: str | None = None,
    protocol: str | None = None,
    version: str | None = None,
    primitive: str | None = None,
) -> QuantumVerdict:
    kb = quantum_kb()
    families = kb.get("families", {})
    context_rules = kb.get("context_rules", [])
    hndl_families = set(kb.get("harvest_now_decrypt_later_families", []))

    fam, spec = _family_for(algorithm, algorithm_family, families)
    status = spec.get("status", "unknown")
    shor = spec.get("shor_impact", "unknown")
    grover = spec.get("grover_impact", "unknown")
    base_expl = (spec.get("explanation") or
                 "No knowledge-base entry for this algorithm; verdict is 'unknown'. "
                 "Add it to quantum_kb.yaml to get a definitive assessment.").strip()

    ksize = _to_int(key_size)
    pv = version or protocol or ""
    notes: list[str] = []
    for rule in context_rules:
        if _rule_matches(
            rule.get("when", {}),
            algorithm=algorithm, family=fam, key_size=ksize,
            mode=mode or "", protocol_version=pv,
        ):
            new_status = rule.get("set_status")
            if new_status and new_status != status:
                notes.append(
                    f"Context rule adjusted status {status} -> {new_status}: {rule.get('note', '')}"
                )
                status = new_status
            elif rule.get("note"):
                notes.append(rule["note"])

    posture = _POSTURE_BY_STATUS.get(status, "unknown")
    hndl = fam in hndl_families and status in ("quantum-vulnerable", "broken-classical")

    expl = base_expl
    if notes:
        expl = base_expl + " " + " ".join(notes)
    if hndl:
        expl += (
            " Harvest-now-decrypt-later applies: traffic/data captured today can be decrypted "
            "once a CRQC exists, so confidentiality with a long lifetime is already at risk."
        )

    return QuantumVerdict(
        status=status,
        shor_impact=shor,
        grover_impact=grover,
        posture=posture,
        harvest_now_decrypt_later=hndl,
        explanation=expl,
        context_notes=notes,
        matched_family=fam,
    )
