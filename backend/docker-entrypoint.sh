#!/usr/bin/env bash
set -euo pipefail

echo "[entrypoint] waiting for database…"
python - <<'PY'
import time, sys
from sqlalchemy import create_engine, text
from app.core.config import settings
for i in range(30):
    try:
        create_engine(settings.database_url).connect().execute(text("SELECT 1"))
        print("[entrypoint] database reachable"); sys.exit(0)
    except Exception as e:  # noqa
        print(f"[entrypoint] db not ready ({i}): {e}"); time.sleep(2)
sys.exit("database never became ready")
PY

echo "[entrypoint] running migrations…"
alembic upgrade head

if [ "${ECDAT_SEED_ON_BOOT:-true}" = "true" ]; then
  echo "[entrypoint] seeding demo data (idempotent)…"
  python -m app.seed || echo "[entrypoint] seed skipped/failed (continuing)"
fi

echo "[entrypoint] starting: $*"
exec "$@"
