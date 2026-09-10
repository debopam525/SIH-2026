import { ExternalLink, FileCode2 } from "lucide-react";
import { useAsset } from "@/api/hooks";
import { Drawer } from "@/components/ui/Drawer";
import { Badge, Button, Skeleton } from "@/components/ui/primitives";
import { ConfidenceBadge, QuantumBadge, RecTypeBadge, RiskBadge } from "@/components/badges";
import { FactorBars } from "@/components/FactorBars";
import { MoscaTimeline } from "@/components/MoscaTimeline";
import { titleCase } from "@/lib/utils";

export function AssetDrawer({
  assetId,
  onClose,
  onFullPage,
}: {
  assetId?: string;
  onClose: () => void;
  onFullPage: (id: string) => void;
}) {
  const { data: a, isLoading } = useAsset(assetId);

  return (
    <Drawer
      open={!!assetId}
      onClose={onClose}
      title={a ? a.algorithm : "Asset"}
      subtitle={a?.usage_location}
    >
      {isLoading || !a ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-20" />
          ))}
        </div>
      ) : (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center gap-1.5">
            <QuantumBadge value={a.quantum_status} />
            <RiskBadge value={a.risk_category} />
            <ConfidenceBadge value={a.detection_confidence} />
            {a.sources.map((s) => (
              <Badge key={s}>{titleCase(s)}</Badge>
            ))}
            <Button size="sm" variant="ghost" className="ml-auto" onClick={() => onFullPage(a.asset_id)}>
              <ExternalLink size={13} /> Full risk view
            </Button>
          </div>

          <Section title="Identity">
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-xs">
              {[
                ["Algorithm", a.algorithm],
                ["Family", titleCase(a.algorithm_family)],
                ["Primitive", a.primitive],
                ["Key size", a.key_size],
                ["Mode", a.mode],
                ["Protocol / version", `${a.protocol} ${a.version}`.trim()],
                ["Library", a.library_dependency],
                ["Asset type", a.asset_type],
              ].map(([k, v]) => (
                <div key={k}>
                  <dt className="text-muted">{k}</dt>
                  <dd className="font-medium">{v || "unknown"}</dd>
                </div>
              ))}
            </dl>
          </Section>

          {a.quantum && (
            <Section title="Quantum verdict">
              <p className="text-xs leading-relaxed text-muted">{a.quantum.explanation}</p>
              <div className="mt-2 flex flex-wrap gap-1.5 text-2xs">
                <Badge>Shor: {a.quantum.shor_impact}</Badge>
                <Badge>Grover: {a.quantum.grover_impact}</Badge>
                {a.quantum.harvest_now_decrypt_later && (
                  <Badge tone="critical">Harvest-now-decrypt-later</Badge>
                )}
              </div>
            </Section>
          )}

          {a.risk && (
            <Section title={`Risk — ${titleCase(a.risk.risk_category)} (${a.risk.weighted_score}/5)`}>
              <FactorBars factors={a.risk.factors} weights={a.risk.weights} />
              <p className="mt-2 whitespace-pre-line text-2xs text-muted">{a.risk.explanation}</p>
            </Section>
          )}

          {a.mosca && (
            <Section title="Mosca (X + Y > Z)">
              <MoscaTimeline mosca={a.mosca} />
            </Section>
          )}

          {a.recommendation && (
            <Section title="Recommendation">
              <div className="flex items-center gap-2 text-sm">
                <span className="font-mono text-muted">{a.recommendation.current_algorithm}</span>
                <span>→</span>
                <span className="font-mono font-semibold text-accent">
                  {a.recommendation.candidate_algorithm}
                </span>
                <RecTypeBadge value={a.recommendation.recommendation_type} />
              </div>
              <p className="mt-1.5 text-2xs text-muted">{a.recommendation.rationale}</p>
            </Section>
          )}

          <Section title={`Evidence (${a.evidence.length})`}>
            <div className="space-y-2">
              {a.evidence.map((e) => (
                <div key={e.evidence_id} className="rounded-lg border border-border bg-surface-2 p-2.5">
                  <div className="flex items-center justify-between gap-2 text-2xs">
                    <span className="flex items-center gap-1 font-mono text-muted">
                      <FileCode2 size={11} /> {e.location}
                      {e.line_or_offset !== "unknown" && `:${e.line_or_offset}`}
                    </span>
                    <ConfidenceBadge value={e.confidence} />
                  </div>
                  <div className="mt-1 text-2xs">
                    <span className="text-muted">matched</span>{" "}
                    <code className="rounded bg-surface px-1">{e.matched_indicator}</code>
                    {e.function_or_scope !== "unknown" && (
                      <span className="text-muted"> in {e.function_or_scope}()</span>
                    )}
                  </div>
                  {e.surrounding_context && (
                    <pre className="mt-1.5 max-h-24 overflow-auto rounded bg-surface p-1.5 text-2xs text-muted">
                      {e.surrounding_context}
                    </pre>
                  )}
                  <div className="mt-1 text-2xs text-muted">
                    detector: {e.detector} · signature: {e.signature_id}
                  </div>
                </div>
              ))}
            </div>
          </Section>
        </div>
      )}
    </Drawer>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section>
      <h4 className="mb-2 text-2xs font-semibold uppercase tracking-wide text-muted">{title}</h4>
      {children}
    </section>
  );
}
