# ECDAT Architecture

```
                         ┌─────────────────────────────┐
                         │   React SPA (Vite + TS)       │
                         │   React Query · Recharts      │
                         └──────────────┬───────────────┘
                                        │ HTTPS / JSON  (OpenAPI 3.1 at /api/v1/openapi.json)
                         ┌──────────────▼───────────────┐
                         │      FastAPI service          │
                         │  auth · scans · assets · cbom │
                         │  risk · mosca · recs · reports│
                         └──────────────┬───────────────┘
        ┌───────────────────────────────┼──────────────────────────────┐
        │                               │                              │
┌───────▼────────┐          ┌───────────▼───────────┐      ┌───────────▼──────────┐
│  Scan runner    │          │   Analysis engines     │      │  Data store           │
│ (BackgroundTask)│◄────────►│ quantum→risk→mosca→rec  │◄────►│ PostgreSQL / SQLite   │
│ source/dep/cfg/ │          │ (pure, deterministic)  │      │ SQLAlchemy 2.0        │
│ binary/container│          └────────────────────────┘      └──────────────────────┘
└───────┬────────┘
        │
┌───────▼──────────────────────────┐
│ detection: rules → (AST-ready) →  │
│ (ML-ready) → normalize → correlate│
└──────────────────────────────────┘
```

## Module boundaries (each swappable behind an interface)

| Concern | Interface | Default impl | Upgrade path |
|---|---|---|---|
| Detection | `app/detection/rules.py::Detector` | `RuleDetector` (regex + comment/string heuristic) | add a tree-sitter AST detector and/or a CodeBERT-style ML classifier to `DETECTORS` |
| Scanners | `app/scanners/base.py::Scanner` | source / dependency / config (full); binary / container (minimal) | richer binary symbol parsing (LIEF), real image-layer unpacking (skopeo) |
| Correlation | `app/cbom/correlate.py::correlate` | deterministic identity+scope keying + post-merge | graph-based cross-repo correlation |
| Quantum engine | `app/analysis/quantum.py::assess` | family baseline + YAML context rules | extend `quantum_kb.yaml` |
| Risk engine | `app/analysis/risk.py::score` | 9 factors, configurable weights | edit weights in Settings or `risk_weights.yaml` |
| Mosca engine | `app/analysis/mosca.py::assess` | X+Y vs Z, configurable Z | edit CRQC horizon in Settings |
| Recommendation | `app/analysis/recommendation.py::recommend` | data-driven mapping + factor scoring | edit `pqc_mapping.yaml` |
| Task execution | FastAPI `BackgroundTasks` + `Scan` row | in-process, cancelable | swap `bg.add_task(run_scan, id)` for `run_scan.delay(id)` (Celery) — `run_scan(scan_id)` is already a self-contained, session-managing function |
| Identity | `app/core/security.py` | local JWT (HS256) + scrypt | OIDC/JWKS — see `auth.md` |

## Why the documented simplifications

* **SQLite default / BackgroundTasks / local JWT / regex detection** — so `docker compose up` and
  `pytest` work on any machine with no C/Rust toolchain, no Redis, no IdP. Every one of these sits
  behind an interface listed above; production swaps are a config or single-function change, not a
  rewrite.
* Determinism is a hard requirement (`docs/acceptance.md` #4–7): the analysis engines take plain
  inputs and contain no randomness, no clock reads, no network calls.

## Observability

Structured logs via `structlog` (JSON when `ECDAT_LOG_JSON=true`). Every request logs
method/path/status/latency and sets `X-Response-Time-ms`. Scan runs emit
`scan.scanner.done` / `scan.completed` events with counts. Prometheus/OTel exporters attach at
the ASGI layer (`opentelemetry-instrumentation-fastapi`) without code changes.
