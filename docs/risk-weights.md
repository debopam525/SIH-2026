# Risk scoring — default weights & assumptions

The risk engine (`app/analysis/risk.py`) scores every asset on **nine factors**, each
normalised to **1–5**, then computes `weighted_score = Σ(value × weight) / Σ(weight)` so the
score stays on a 1–5 scale. Weights live in `app/data/risk_weights.yaml` and are **editable at
runtime** in Settings (admin only) — the DB value overrides the file.

## Default weights

| Factor | Weight | How the 1–5 value is derived | Source tag |
|---|---:|---|---|
| `quantum_vulnerability` | **0.20** | quantum status → 5 (vulnerable/broken), 3 (weakened), 1 (safe) | derived |
| `cryptographic_strength` | 0.14 | algorithm posture → broken 5 / legacy 4 / acceptable 2 / strong 1 | derived |
| `data_sensitivity` | 0.14 | owning Application's data classification (1–5) | application / default 3 |
| `business_criticality` | 0.13 | owning Application's criticality (1–5) | application / default 3 |
| `data_lifetime` | 0.12 | years the data must stay secret → banded 1–5 | application / default 3 |
| `system_lifetime` | 0.08 | remaining service life in years → banded 1–5 | application / default 3 |
| `migration_complexity` | 0.08 | primitive → protocol/signature/KEM harder (4–5), hash/MAC easier (2) | derived |
| `performance_impact` | 0.06 | expected PQC replacement class runtime cost | derived |
| `cost` | 0.05 | mean(migration_complexity, business_criticality) | derived |

Weights sum to 1.00; if edited weights don't, the engine renormalises defensively so the score
band still means the same thing.

## Category bands (applied to the final weighted score)

| Band | Score ≥ | Meaning |
|---|---:|---|
| **Critical** | 4.0 | immediate migration planning required |
| **High** | 3.2 | vulnerable crypto protecting sensitive / long-lived data |
| **Medium** | 2.3 | plan the migration |
| **Low** | 0.0 | currently acceptable — monitor |

## Explainability & reproducibility

Each factor stores `{value, rationale, source}`. `source=default` means the owning Application
had no value and the neutral default (3) was used — the UI flags this and the explanation says
so. Given the same stored factor values + weights the score is **exactly reproducible**
(`python -m app.acceptance`, check #5).

## Grover ≠ critical

Symmetric/hash assets are scored as *weakened*, not *broken*: AES-256 / SHA-384+ come out
`low`/`medium` unless the owning application's sensitivity and lifetime push them up. AES-128
and sub-256-bit digests are nudged toward `medium` with a "move to 256-bit" note.
