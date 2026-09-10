# ECDAT Frontend

React 18 + TypeScript + Vite + Tailwind. Dark-mode-first enterprise dashboard.

```bash
npm install
node node_modules/esbuild/install.js   # only if your npm blocks postinstall scripts
npm run dev        # http://localhost:5173  (proxies /api -> http://localhost:8000)
npm run typecheck
npm run build
```

Point at a non-default API: `ECDAT_API_URL=http://host:8000 npm run dev`.

## Structure

| Path | Purpose |
|---|---|
| `src/api/types.ts` | Hand-authored mirror of `backend/app/schemas.py`. Regenerate from the live spec with `npx openapi-typescript http://localhost:8000/api/v1/openapi.json -o src/api/schema.d.ts`. |
| `src/api/client.ts` | `fetch` wrapper: bearer auth, transparent refresh, error normalisation. |
| `src/api/hooks.ts` | React Query hooks — the only place server state is fetched. |
| `src/store/` | `auth` (JWT + capabilities) and `theme` (light/dark) contexts. |
| `src/components/ui/` | Primitives (Button, Card, Badge, Drawer, Toast, …), themed via CSS variables in `index.css`. |
| `src/components/` | Domain components: badges, charts (Recharts), `AssetDrawer`, `FactorBars`, `MoscaTimeline`. |
| `src/pages/` | One file per route (Section 6 screens). |

## Screens

Dashboard · Scan Management · Asset Explorer (CBOM + drill-down drawer) · Risk Detail
(radar + factor bars + Mosca timeline) · Applications (editable metadata → re-score) ·
Recommendations (current→PQC compare) · Migration Readiness (kanban by priority) · Reports ·
Settings (risk weights + CRQC horizon, admin only) · Login (role-aware).

Every data view has loading skeletons and an empty state. Risk/quantum signalling uses an icon
+ text alongside colour. Charts follow the theme via CSS-variable colours.
