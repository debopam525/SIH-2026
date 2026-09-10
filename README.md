# ECDAT — Enterprise Cryptographic Discovery & Analysis Tool

ECDAT scans codebases, dependencies and configuration for cryptographic assets, builds a
**Cryptographic Bill of Materials (CBOM)**, assesses quantum vulnerability, scores risk,
runs a Mosca (`X + Y > Z`) prioritization, and recommends post-quantum (PQC) replacements —
all surfaced through an interactive dashboard.

```
scan → extract → detect (rules + AST-ready + ML-ready) → normalize → correlate/dedupe →
CBOM → quantum engine → risk engine → Mosca engine → recommendation engine →
dashboard → report export → rescan → diff
```

## Quick start (Docker)

```bash
cd infra
docker compose up --build
```

- Frontend: http://localhost:5173
- API + docs: http://localhost:8000/docs
- Default logins (seeded): `admin@ecdat.local` / `analyst@ecdat.local` / `viewer@ecdat.local`, password `ecdat` for all.

## Quick start (local, no Docker)

### Backend
```bash
cd backend
python -m venv .venv && . .venv/Scripts/activate   # Windows: .venv\Scripts\Activate.ps1
pip install -e ".[dev]"
python -m app.seed            # creates ecdat.db, seeds users + a demo scan of tests/fixtures/sample_repo
uvicorn app.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Tests
```bash
cd backend
pytest -q
```

## What is real vs. simplified

| Area | Status |
|---|---|
| Data model (Section 4) | Implemented in full (SQLAlchemy 2.0 + Alembic) |
| Quantum / Risk / Mosca / PQC engines | Implemented for real, data-driven, deterministic, unit-tested |
| Source scanner (rules + evidence + confidence) | Implemented (regex + language heuristics; AST/ML behind the same `Detector` interface) |
| Dependency scanner | Implemented for `requirements.txt`, `package.json`/`package-lock.json`, `pom.xml`, `go.mod`/`go.sum`, `Cargo.toml` |
| Config scanner | Implemented for TLS/SSH/OpenSSL/nginx/apache-style configs + generic key/value |
| Binary / container scanner | Minimal: `strings`-style extraction + Dockerfile parsing, always low-confidence |
| CBOM correlate / dedupe / diff / export | Implemented (JSON + CSV, CycloneDX-style structure) |
| Auth | Local JWT + RBAC (admin/analyst/viewer); OIDC swap documented in `docs/auth.md` |
| Task queue | FastAPI `BackgroundTasks` + a `Scan` status row (cancelable); Celery upgrade path in `docs/architecture.md` |
| Reports | JSON + CSV always; PDF if `weasyprint` is installed |
| DB | SQLite by default; set `ECDAT_DATABASE_URL=postgresql+psycopg://…` for Postgres |

See [`docs/`](docs/) for architecture, data-flow, detection-confidence explainer, and the default
risk weights / CRQC assumption.

## Acceptance criteria

`docs/acceptance.md` maps every item in Section 10 of the spec to where it is implemented and how to verify it.
`python -m app.acceptance` runs an automated check of the machine-verifiable ones.
