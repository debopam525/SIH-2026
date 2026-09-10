import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight } from "lucide-react";
import { useRecommendations } from "@/api/hooks";
import { useActiveScan } from "@/store/scan";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, EmptyState, Select, Skeleton } from "@/components/ui/primitives";
import { RecTypeBadge, RiskBadge } from "@/components/badges";
import { titleCase } from "@/lib/utils";

export default function Recommendations() {
  const { scanId } = useActiveScan();
  const [priority, setPriority] = useState("");
  const [type, setType] = useState("");
  const { data, isLoading } = useRecommendations({
    migration_priority: priority || undefined,
    recommendation_type: type || undefined,
    scan_id: scanId,
  });

  return (
    <>
      <PageHeader
        title="PQC Recommendations"
        description="Current algorithm → recommended post-quantum / hybrid replacement, with rationale"
        actions={
          <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
            <Select value={priority} onChange={(e) => setPriority(e.target.value)} className="w-full sm:w-40">
              <option value="">All priorities</option>
              {["critical", "high", "medium", "low"].map((p) => (
                <option key={p}>{p}</option>
              ))}
            </Select>
            <Select value={type} onChange={(e) => setType(e.target.value)} className="w-full sm:w-44">
              <option value="">All types</option>
              {["pqc", "hybrid", "symmetric_upgrade", "config_change", "no_change"].map((p) => (
                <option key={p} value={p}>
                  {titleCase(p)}
                </option>
              ))}
            </Select>
          </div>
        }
      />
      <div className="p-4 sm:p-6 lg:p-8">
        {isLoading ? (
          <div className="grid gap-3 lg:grid-cols-2">
            {Array.from({ length: 6 }).map((_, i) => (
              <Skeleton key={i} className="h-44" />
            ))}
          </div>
        ) : !data?.items.length ? (
          <Card>
            <EmptyState title="No recommendations" hint="Run a scan to generate PQC recommendations." />
          </Card>
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            {data.items.map((r) => (
              <Card key={r.asset_id} className="p-4">
                <div className="flex items-start justify-between gap-2">
                  <div className="min-w-0">
                    <Link
                      to={`/assets/${r.asset_id}`}
                      className="text-sm font-medium hover:text-accent hover:underline"
                    >
                      {r.asset_name}
                    </Link>
                    <div className="mt-0.5 text-2xs text-muted">
                      {titleCase(r.algorithm_family ?? "")} · use case: {r.use_case}
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-1.5">
                    <RecTypeBadge value={r.recommendation_type} />
                    <RiskBadge value={r.migration_priority} />
                  </div>
                </div>

                <div className="my-4 flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
                  <div className="flex-1 rounded-lg border border-border bg-surface-2 p-2 text-center">
                    <div className="text-2xs uppercase text-muted">Current</div>
                    <div className="font-mono text-sm">{r.current_algorithm}</div>
                  </div>
                  <ArrowRight size={16} className="shrink-0 text-muted" />
                  <div className="flex-1 rounded-lg border border-accent/40 bg-accent/10 p-2 text-center">
                    <div className="text-2xs uppercase text-accent">Recommended</div>
                    <div className="font-mono text-sm font-semibold text-accent">{r.candidate_algorithm}</div>
                    <div className="text-2xs text-muted">score {r.score}/5</div>
                  </div>
                </div>

                <p className="text-2xs text-muted">{r.rationale}</p>

                {r.alternatives.length > 0 && (
                  <details className="mt-2 text-2xs">
                    <summary className="cursor-pointer text-accent">
                      {r.alternatives.length} alternative(s) & factors considered
                    </summary>
                    <div className="mt-1.5 space-y-1.5">
                      {r.alternatives.map((a) => (
                        <div key={a.name} className="rounded bg-surface-2 p-1.5">
                          <span className="font-mono font-medium">{a.name}</span>{" "}
                          <span className="text-muted">
                            · {titleCase(a.recommendation_type)} · score {a.score}/5
                          </span>
                          <div className="text-muted">{a.notes}</div>
                        </div>
                      ))}
                      <div className="rounded bg-surface-2 p-1.5 text-muted">
                        Factors:{" "}
                        {Object.entries(r.factor_scores)
                          .map(([k, v]) => `${titleCase(k)} ${v}/5`)
                          .join(" · ")}
                      </div>
                    </div>
                  </details>
                )}
              </Card>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
