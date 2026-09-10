"""PQC recommendation engine.

Policy lives in ``pqc_mapping.yaml``; this module only classifies the asset into a use case,
context-adjusts the selection weights, scores every candidate over the eight factors, and
returns the top pick plus ranked alternatives with rationale.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.analysis.quantum import QuantumVerdict
from app.core.kb import pqc_mapping

_FACTORS = [
    "security_level", "application_fit", "latency", "compute_performance",
    "memory_usage", "migration_cost", "compatibility",
]

_ALREADY_PQC_FAMILIES = {"pqc-kem", "pqc-signature"}


@dataclass
class Candidate:
    name: str
    recommendation_type: str
    score: float
    factor_scores: dict[str, int]
    notes: str
    migration_notes: str


@dataclass
class RecommendationResult:
    use_case: str
    current_algorithm: str
    top: Candidate
    alternatives: list[Candidate] = field(default_factory=list)
    recommendation_type: str = "no_change"
    rationale: str = ""
    compatibility_notes: str = ""
    performance_memory_notes: str = ""
    migration_priority: str = "low"
    selection_weights: dict[str, float] = field(default_factory=dict)


def _classify(primitive: str, family: str) -> str:
    mp = pqc_mapping()["classify"]
    if primitive in mp["by_primitive"]:
        return mp["by_primitive"][primitive]
    return mp["by_family"].get(family, "none")


def _adjust_weights(base: dict[str, float], *, business_criticality: int | None,
                    primitive: str, latency_sensitive: bool) -> dict[str, float]:
    w = dict(base)
    if business_criticality and business_criticality >= 4:
        w["security_level"] = w.get("security_level", 0.28) + 0.06
        w["migration_cost"] = max(0.02, w.get("migration_cost", 0.12) - 0.03)
    if latency_sensitive or primitive in ("cipher", "hash"):
        w["latency"] = w.get("latency", 0.12) + 0.04
        w["compute_performance"] = w.get("compute_performance", 0.12) + 0.03
        w["memory_usage"] = w.get("memory_usage", 0.10) + 0.02
    total = sum(w.values()) or 1.0
    return {k: round(v / total, 4) for k, v in w.items()}


def _score_candidate(spec: dict, weights: dict[str, float]) -> Candidate:
    fs = {k: int(spec.get(k, 3)) for k in _FACTORS}
    wsum = sum(weights.get(k, 0.0) for k in _FACTORS) or 1.0
    raw = sum(fs[k] * weights.get(k, 0.0) for k in _FACTORS) / wsum
    return Candidate(
        name=spec["name"],
        recommendation_type=spec.get("recommendation_type", "pqc"),
        score=round(raw, 3),
        factor_scores=fs,
        notes=spec.get("notes", ""),
        migration_notes=spec.get("migration_notes", ""),
    )


def _priority(risk_category: str, mosca_priority: str, quantum_status: str) -> str:
    if quantum_status == "quantum-safe":
        return "low"
    order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
    r = order.get(risk_category, 1)
    if mosca_priority == "act_now":
        r = max(r, 3)
    if mosca_priority == "act_now" and risk_category in ("critical", "high"):
        return "critical"
    return {4: "critical", 3: "high", 2: "medium", 1: "low"}[r]


def recommend(
    *,
    algorithm: str,
    algorithm_family: str,
    primitive: str,
    quantum: QuantumVerdict,
    risk_category: str = "medium",
    mosca_priority: str = "plan",
    business_criticality: int | None = None,
    latency_sensitive: bool = False,
) -> RecommendationResult:
    mapping = pqc_mapping()
    use_case = _classify(primitive, algorithm_family)

    # Already post-quantum, or a primitive that needs no crypto change and is not broken.
    if algorithm_family in _ALREADY_PQC_FAMILIES or (
        use_case == "none" and quantum.status in ("quantum-safe",)
    ):
        spec = mapping["candidates"]["none"][0]
        top = _score_candidate(spec, mapping["selection_weights"])
        return RecommendationResult(
            use_case="none",
            current_algorithm=algorithm,
            top=top,
            recommendation_type="no_change",
            rationale=(
                f"{algorithm} retains an adequate post-quantum margin "
                f"(status: {quantum.status}). No cryptographic change required; monitor for "
                f"guidance updates and keep key sizes >= 256-bit."
            ),
            compatibility_notes=top.notes,
            performance_memory_notes=top.migration_notes,
            migration_priority="low",
            selection_weights=mapping["selection_weights"],
        )

    weights = _adjust_weights(
        mapping["selection_weights"],
        business_criticality=business_criticality,
        primitive=primitive,
        latency_sensitive=latency_sensitive,
    )
    specs = mapping["candidates"].get(use_case) or mapping["candidates"]["none"]
    ranked = sorted((_score_candidate(s, weights) for s in specs), key=lambda c: c.score, reverse=True)
    top, alts = ranked[0], ranked[1:]

    priority = _priority(risk_category, mosca_priority, quantum.status)
    urgency = ""
    if quantum.status == "broken-classical":
        urgency = "This primitive is already broken by classical cryptanalysis — replace now, independent of the quantum timeline. "
    elif quantum.harvest_now_decrypt_later:
        urgency = "Harvest-now-decrypt-later exposure: recorded data is at risk retroactively. "

    factors_considered = ", ".join(f"{k} (w={weights.get(k, 0):.2f})" for k in _FACTORS)
    rationale = (
        f"{urgency}Use case classified as '{use_case}' from primitive '{primitive}'/family "
        f"'{algorithm_family}'. Ranked {len(ranked)} candidates over: {factors_considered}. "
        f"Top pick '{top.name}' scored {top.score}/5 "
        f"(security {top.factor_scores['security_level']}/5, "
        f"compat {top.factor_scores['compatibility']}/5, "
        f"migration cost {top.factor_scores['migration_cost']}/5). "
        + (f"Runner-up: '{alts[0].name}' ({alts[0].score}/5)." if alts else "")
    )

    return RecommendationResult(
        use_case=use_case,
        current_algorithm=algorithm,
        top=top,
        alternatives=alts,
        recommendation_type=top.recommendation_type,
        rationale=rationale,
        compatibility_notes=top.notes,
        performance_memory_notes=top.migration_notes,
        migration_priority=priority,
        selection_weights=weights,
    )
