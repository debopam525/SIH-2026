# Acceptance criteria (spec Section 10) — status & how to verify

Run `python -m app.seed` then `python -m app.acceptance` for the automated subset, and
`pytest` for the full suite.

| # | Criterion | Status | Where / how to verify |
|---|---|---|---|
| 1 | Fixture repo → expected assets detected with evidence | ✅ | `tests/integration/test_scan_pipeline.py::test_scan_completes_and_finds_expected_algorithms`; acceptance #1. Fixture: `backend/tests/fixtures/sample_repo` (RSA, AES, MD5, SHA-1, ECDSA, TLS, SSH, ML-KEM + negative cases). |
| 2 | Every asset has all applicable CBOM fields; unavailable = explicit `unknown` | ✅ | `test_every_asset_has_cbom_fields_and_evidence`; acceptance #2. Model defaults are the literal string `"unknown"`. |
| 3 | Same underlying asset never double-counted across scanners | ✅ | `test_no_asset_double_counted` + `tests/unit/test_correlate.py`; acceptance #3. `dedup_key` unique per scan; post-merge folds source+dependency. |
| 4 | Every quantum verdict includes an explanation | ✅ | `tests/unit/test_quantum.py`; acceptance #4. `QuantumVerdict.explanation` always populated, incl. `unknown`. |
| 5 | Risk score/category reproducible from stored factors + weights | ✅ | `tests/unit/test_risk.py::test_score_is_reproducible`; acceptance #5 (re-runs `analyze_asset`, asserts identical). No randomness / clock / IO in engines. |
| 6 | Every Mosca result exposes its X / Y / Z assumptions | ✅ | `tests/unit/test_mosca.py`; acceptance #6. `assumptions_note` always contains X, Y, Z and "not a prediction". |
| 7 | Every recommendation shows the alternative(s) + factors considered | ✅ | `tests/unit/test_recommendation.py`; acceptance #7. `rationale` lists weighted factors; `alternatives[]` populated unless `no_change`. |
| 8 | Every dashboard number derived live from the same CBOM/risk data | ✅ | `app/api/v1/dashboard.py` computes from `CryptographicAsset` + `RiskAssessment` rows on each request; no stored aggregates. `test_api_happy_path_scan_to_report`. |
| 9 | Reports contain inventory, algorithm details, vulnerability/risk, exposure, recommendations, migration priorities | ✅ | `app/reports/generator.py` (`inventory`, `algorithms`, `vulnerability`, `exposure`, `recommendations`, `migration_roadmap`, `executive_summary`, `full`); acceptance #9; `test_api_happy_path_scan_to_report`. |
| 10 | GUI: start scan → CBOM → risk → recommendation → export report without leaving the app | ✅ | Routes: `/scans` → `/assets` (drawer) → `/assets/:id` (RiskDetail) → `/recommendations` → `/reports`. API path covered by `test_api_happy_path_scan_to_report`. |
| 11 | CI passes (lint, types, tests, build) on a clean checkout | ✅ | `.github/workflows/ci.yml` runs ruff + pytest + acceptance (backend) and tsc + eslint + vite build (frontend). |
| 12 | `docker compose up` brings up DB + API + workers + frontend with one command | ✅ | `infra/docker-compose.yml` (postgres + api + web). "Workers" run in-process via `BackgroundTasks` (documented simplification, `docs/architecture.md`). |

## Known limitations (intentional, documented)

* Binary & container scanners are minimal (`strings` + Dockerfile parsing), always low-confidence.
* No ML classifier model ships — the `Detector` interface and `ml_classified` confidence tier exist for it.
* Task queue is `BackgroundTasks`, not Celery/Redis — `run_scan(scan_id)` is written to drop into a Celery task unchanged.
* PDF export requires the optional `weasyprint` extra; otherwise a standalone styled HTML file is produced.
