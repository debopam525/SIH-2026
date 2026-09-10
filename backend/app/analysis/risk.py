"""Risk scoring engine.

Nine factors, each normalised to 1-5, combined with configurable weights that sum to 1.0, so
the weighted score stays on a 1-5 scale and maps to a category band. Every factor carries a
``value``, a ``rationale`` string and a ``source`` (``derived`` | ``application`` | ``default``)
so the score is fully explainable and reproducible.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.analysis.quantum import QuantumVerdict
from app.core.kb import risk_defaults

FACTORS = [
    "cryptographic_strength",
    "quantum_vulnerability",
    "data_sensitivity",
    "business_criticality",
    "data_lifetime",
    "system_lifetime",
    "migration_complexity",
    "cost",
    "performance_impact",
]


@dataclass
class AppContext:
    name: str = "unknown"
    business_criticality: int | None = None
    system_lifetime_years: int | None = None
    data_sensitivity: int | None = None
    data_lifetime_years: int | None = None


@dataclass
class RiskResult:
    factors: dict[str, dict] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)
    weighted_score: float = 0.0
    risk_category: str = "low"
    explanation: str = ""


def _years_to_scale(years: int | float | None) -> int | None:
    if years is None:
        return None
    if years < 1:
        return 1
    if years < 3:
        return 2
    if years < 7:
        return 3
    if years < 15:
        return 4
    return 5


_EXPECTED_REPLACEMENT_CLASS = {
    "kem": "ml-kem",
    "key-exchange": "ml-kem",
    "signature": "ml-dsa",
    "cipher": "aes-256",
    "hash": "sha-384",
    "protocol": "hybrid",
    "mac": "none",
    "kdf": "none",
}


def score(
    *,
    primitive: str,
    algorithm_family: str,
    quantum: QuantumVerdict,
    app: AppContext | None,
    weights: dict[str, float] | None = None,
) -> RiskResult:
    defaults = risk_defaults()
    weights = dict(weights or defaults["weights"])
    norm = defaults["normalizers"]
    neutral = int(defaults.get("neutral_default", 3))
    bands = defaults["bands"]
    app = app or AppContext()

    f: dict[str, dict] = {}

    def put(name: str, value: int, rationale: str, source: str) -> None:
        f[name] = {"value": int(max(1, min(5, value))), "rationale": rationale, "source": source}

    # 1. cryptographic strength (intrinsic weakness)
    cs = norm["cryptographic_strength"].get(quantum.posture, neutral)
    put("cryptographic_strength", cs,
        f"Algorithm posture '{quantum.posture}' from the quantum knowledge base.", "derived")

    # 2. quantum vulnerability
    qv = norm["quantum_vulnerability"].get(quantum.status, neutral)
    put("quantum_vulnerability", qv,
        f"Quantum status '{quantum.status}' (Shor: {quantum.shor_impact}, "
        f"Grover: {quantum.grover_impact}).", "derived")

    # 3. data sensitivity
    if app.data_sensitivity:
        put("data_sensitivity", app.data_sensitivity,
            f"From owning application '{app.name}' data classification.", "application")
    else:
        put("data_sensitivity", neutral,
            "No data classification on the owning application; using neutral default.", "default")

    # 4. business criticality
    if app.business_criticality:
        put("business_criticality", app.business_criticality,
            f"From owning application '{app.name}' business criticality.", "application")
    else:
        put("business_criticality", neutral,
            "No business criticality recorded; using neutral default.", "default")

    # 5. data lifetime
    dl = _years_to_scale(app.data_lifetime_years)
    if dl is not None:
        put("data_lifetime", dl,
            f"Data must stay confidential ~{app.data_lifetime_years} years.", "application")
    else:
        put("data_lifetime", neutral,
            "Data lifetime unknown; using neutral default.", "default")

    # 6. system lifetime
    sl = _years_to_scale(app.system_lifetime_years)
    if sl is not None:
        put("system_lifetime", sl,
            f"System expected to run ~{app.system_lifetime_years} more years.", "application")
    else:
        put("system_lifetime", neutral,
            "System lifetime unknown; using neutral default.", "default")

    # 7. migration complexity
    mc = norm["migration_complexity"].get(primitive, neutral)
    put("migration_complexity", mc,
        f"Primitive '{primitive}': rollout coupling / blast radius.", "derived")

    # 8. cost (scales with rollout size and how critical the system is)
    cost = round((mc + f["business_criticality"]["value"]) / 2)
    put("cost", cost,
        "Estimated from migration complexity and business criticality.", "derived")

    # 9. performance impact of the expected PQC replacement class
    repl = _EXPECTED_REPLACEMENT_CLASS.get(primitive, "unknown")
    pi = norm["performance_impact"].get(repl, neutral)
    put("performance_impact", pi,
        f"Expected replacement class '{repl}' runtime cost.", "derived")

    # weighted sum (renormalise weights defensively so the score stays 1-5)
    wsum = sum(weights.get(k, 0.0) for k in FACTORS) or 1.0
    weighted = sum(f[k]["value"] * weights.get(k, 0.0) for k in FACTORS) / wsum
    weighted = round(weighted, 3)

    category = "low"
    for cat in ("critical", "high", "medium", "low"):
        if weighted >= bands[cat]:
            category = cat
            break

    contribs = sorted(
        ((k, f[k]["value"] * weights.get(k, 0.0)) for k in FACTORS),
        key=lambda kv: kv[1], reverse=True,
    )[:3]
    top = ", ".join(f"{k} ({f[k]['value']}/5, w={weights.get(k, 0):.2f})" for k, _ in contribs)
    explanation = (
        f"Weighted score {weighted}/5 -> {category.upper()}. "
        f"Largest contributors: {top}. "
        f"Quantum driver: {quantum.status}. "
        + ("Some factors used neutral defaults because the owning application lacks metadata; "
           "populate it in the Application view for a sharper score."
           if any(v["source"] == "default" for v in f.values()) else
           "All factors derived from asset or application data.")
    )

    return RiskResult(
        factors=f, weights=weights, weighted_score=weighted,
        risk_category=category, explanation=explanation,
    )
