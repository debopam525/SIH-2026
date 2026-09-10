# Data flow: one scan, end to end

```
POST /api/v1/scans                     Scan row: status=queued
   │
   ▼  (BackgroundTasks -> app/scanners/runner.py::run_scan)
resolve target (path | git clone | unzip)        status=running, stage=preparing
   │
   ▼  ensure Application + Repository rows exist
for each requested scan_type:                     stage=scanning:<type>
   SourceScanner / DependencyScanner / ConfigScanner / BinaryScanner / ContainerScanner
   → each file → app/detection/rules.py::run_detectors → [RawFinding...]
        RawFinding = {algorithm, family, primitive, key_size, mode, version,
                      confidence, matched_indicator, signature_id, location, line, context}
   │
   ▼  app/cbom/correlate.py::correlate                stage=correlating
   normalize each finding (canonical names/families)  → NormalizedAsset
   bucket by  (crypto_identity | scope)               → merge evidence, keep max confidence
   post-merge: fold standalone dependency assets into code assets naming the same library
   drop weak generic-KV noise
   │
   ▼  persist                                          CryptographicAsset + Evidence rows
   │
   ▼  app/analysis/pipeline.py::run_for_scan           stage=analysing
   for each asset:
       quantum.assess()      → {status, shor, grover, posture, explanation, hndl}
       risk.score()          → 9 factors ×1-5 × weights → weighted_score → category + explanation
       mosca.assess()        → X + Y vs Z → exposed?, gap, priority, assumptions_note
       recommendation.recommend()
                             → use_case → ranked candidates → top + alternatives + rationale
       upsert RiskAssessment / MoscaAssessment / Recommendation / MigrationStatus
   │
   ▼                                                   status=completed, stats populated
GET /api/v1/dashboard/metrics   ─┐
GET /api/v1/assets              ─┤ all derive live from the same CryptographicAsset +
GET /api/v1/risk/{id}           ─┤ RiskAssessment / MoscaAssessment / Recommendation rows
GET /api/v1/recommendations     ─┤ (no cached or hard-coded numbers)
GET /api/v1/cbom/export         ─┘
GET /api/v1/scans/{id}/diff      → compares this scan's dedup_keys against the previous scan's
POST /api/v1/reports/generate    → app/reports/generator.py builds a report dict from the same data
```

## Re-scoring triggers

Changing application metadata (`PUT /applications/{id}`), risk weights
(`PUT /settings/risk-weights`) or the CRQC horizon (`PUT /settings/mosca-assumption`) re-runs
`analyze_asset` / `run_for_scan` so every downstream number stays consistent.
