import { Link, useParams } from "react-router-dom";
import { ArrowLeft } from "lucide-react";
import { useAsset } from "@/api/hooks";
import { PageHeader } from "@/components/layout/PageHeader";
import { Badge, Card, CardHeader, Skeleton } from "@/components/ui/primitives";
import { ConfidenceBadge, QuantumBadge, RecTypeBadge, RiskBadge } from "@/components/badges";
import { FactorRadar } from "@/components/charts";
import { FactorBars } from "@/components/FactorBars";
import { MoscaTimeline } from "@/components/MoscaTimeline";
import { titleCase } from "@/lib/utils";

export default function RiskDetail() {
  const { assetId } = useParams();
  const { data: a, isLoading } = useAsset(assetId);

  return (
    <>
      <PageHeader
        title={a ? `${a.algorithm} — Risk Detail` : "Risk Detail"}
        description={a?.usage_location}
        actions={
          <Link to="/assets" className="flex items-center gap-1 text-xs text-accent hover:underline">
            <ArrowLeft size={13} /> Asset Explorer
          </Link>
        }
      />
      <div className="p-4 sm:p-6 lg:p-8">
        {isLoading || !a ? (
          <div className="grid gap-4 lg:grid-cols-2">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-64" />
            ))}
          </div>
        ) : (
          <div className="grid gap-4 lg:grid-cols-2">
            <Card className="lg:col-span-2">
              <div className="flex flex-wrap items-center gap-2 p-4">
                <span className="text-lg font-semibold">{a.asset_name}</span>
                <QuantumBadge value={a.quantum_status} />
                <RiskBadge value={a.risk_category} />
                <ConfidenceBadge value={a.detection_confidence} />
                {a.sources.map((s) => (
                  <Badge key={s}>{titleCase(s)}</Badge>
                ))}
                <span className="ml-auto text-xs text-muted">
                  {a.evidence_count} evidence occurrence(s)
                </span>
              </div>
            </Card>

            {a.quantum && (
              <Card>
                <CardHeader title="Quantum vulnerability" subtitle={`Matched family: ${a.quantum.matched_family}`} />
                <div className="space-y-2 p-4 text-xs">
                  <p className="leading-relaxed text-muted">{a.quantum.explanation}</p>
                  <div className="flex flex-wrap gap-1.5">
                    <Badge>Shor impact: {a.quantum.shor_impact}</Badge>
                    <Badge>Grover impact: {a.quantum.grover_impact}</Badge>
                    <Badge>Posture: {a.quantum.posture}</Badge>
                    {a.quantum.harvest_now_decrypt_later && (
                      <Badge tone="critical">Harvest-now-decrypt-later</Badge>
                    )}
                  </div>
                  {a.quantum.context_notes.length > 0 && (
                    <ul className="list-inside list-disc text-muted">
                      {a.quantum.context_notes.map((n, i) => (
                        <li key={i}>{n}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </Card>
            )}

            {a.risk && (
              <Card>
                <CardHeader
                  title={`Risk score — ${a.risk.weighted_score} / 5`}
                  subtitle={`Category: ${titleCase(a.risk.risk_category)}`}
                />
                <div className="p-2">
                  <FactorRadar factors={a.risk.factors} />
                </div>
              </Card>
            )}

            {a.risk && (
              <Card className="lg:col-span-2">
                <CardHeader title="Factor contribution" subtitle="value × weight, sorted by contribution" />
                <div className="p-4">
                  <FactorBars factors={a.risk.factors} weights={a.risk.weights} />
                  <p className="mt-3 whitespace-pre-line rounded-md bg-surface-2 p-3 text-xs text-muted">
                    {a.risk.explanation}
                  </p>
                </div>
              </Card>
            )}

            {a.mosca && (
              <Card className="lg:col-span-2">
                <CardHeader title="Mosca prioritisation" subtitle="X (data lifetime) + Y (migration) vs Z (CRQC horizon)" />
                <div className="p-4">
                  <MoscaTimeline mosca={a.mosca} />
                </div>
              </Card>
            )}

            {a.recommendation && (
              <Card className="lg:col-span-2">
                <CardHeader title="PQC recommendation" subtitle={`Use case: ${a.recommendation.use_case}`} />
                <div className="space-y-3 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-md bg-surface-2 px-2 py-1 font-mono text-sm">
                      {a.recommendation.current_algorithm}
                    </span>
                    <span className="text-muted">→</span>
                    <span className="rounded-md bg-accent/15 px-2 py-1 font-mono text-sm font-semibold text-accent">
                      {a.recommendation.candidate_algorithm}
                    </span>
                    <RecTypeBadge value={a.recommendation.recommendation_type} />
                    <Badge tone="neutral">score {a.recommendation.score}/5</Badge>
                    <RiskBadge value={a.recommendation.migration_priority} />
                  </div>
                  <p className="text-xs text-muted">{a.recommendation.rationale}</p>
                  <div className="grid gap-3 md:grid-cols-2">
                    <Info title="Compatibility" body={a.recommendation.compatibility_notes} />
                    <Info title="Performance / memory" body={a.recommendation.performance_memory_notes} />
                  </div>
                  {a.recommendation.alternatives.length > 0 && (
                    <details className="rounded-lg border border-border p-3 text-xs">
                      <summary className="cursor-pointer font-medium">
                        {a.recommendation.alternatives.length} alternative(s)
                      </summary>
                      <div className="mt-2 space-y-2">
                        {a.recommendation.alternatives.map((alt) => (
                          <div key={alt.name} className="rounded-md bg-surface-2 p-2">
                            <div className="flex items-center gap-2">
                              <span className="font-mono font-medium">{alt.name}</span>
                              <RecTypeBadge value={alt.recommendation_type} />
                              <span className="text-muted">score {alt.score}/5</span>
                            </div>
                            <p className="mt-1 text-2xs text-muted">{alt.notes}</p>
                            <p className="text-2xs text-muted">{alt.migration_notes}</p>
                          </div>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              </Card>
            )}
          </div>
        )}
      </div>
    </>
  );
}

function Info({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-md bg-surface-2 p-2.5">
      <div className="text-2xs font-semibold uppercase tracking-wide text-muted">{title}</div>
      <p className="mt-1 text-xs">{body || "—"}</p>
    </div>
  );
}
