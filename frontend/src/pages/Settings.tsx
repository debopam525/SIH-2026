import { useEffect, useState } from "react";
import { RotateCcw, Save } from "lucide-react";
import {
  useMoscaAssumption,
  useRiskWeights,
  useUpdateMoscaAssumption,
  useUpdateRiskWeights,
} from "@/api/hooks";
import { useAuth } from "@/store/auth";
import { useToast } from "@/components/ui/toast";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button, Card, CardHeader, EmptyState, Input, Skeleton } from "@/components/ui/primitives";
import { titleCase } from "@/lib/utils";

export default function Settings() {
  const { can } = useAuth();
  if (!can("settings:write"))
    return (
      <>
        <PageHeader title="Settings" />
        <div className="p-4 sm:p-6 lg:p-8">
          <Card>
            <EmptyState title="Admins only" hint="Your role does not have settings:write." />
          </Card>
        </div>
      </>
    );
  return (
    <>
      <PageHeader title="Settings" description="Risk-scoring weights and the CRQC horizon assumption. Changes re-score all scans." />
      <div className="grid gap-5 p-4 sm:p-6 lg:grid-cols-2 lg:p-8">
        <RiskWeightsCard />
        <CrqcCard />
      </div>
    </>
  );
}

function RiskWeightsCard() {
  const q = useRiskWeights();
  const update = useUpdateRiskWeights();
  const toast = useToast();
  const [w, setW] = useState<Record<string, number>>({});

  useEffect(() => {
    if (q.data) setW(q.data.weights);
  }, [q.data]);

  const total = Object.values(w).reduce((s, v) => s + Number(v || 0), 0);
  const save = () =>
    update.mutate(w, {
      onSuccess: () => toast({ kind: "success", title: "Weights saved", body: "All scans re-scored." }),
      onError: (e) => toast({ kind: "error", title: "Save failed", body: String(e) }),
    });

  return (
    <Card>
      <CardHeader
        title="Risk-factor weights"
        subtitle="Normalised at scoring time; the weighted score stays on a 1-5 scale."
        actions={
          <Button size="sm" variant="ghost" onClick={() => q.data && setW(q.data.weights)}>
            <RotateCcw size={13} /> Reset
          </Button>
        }
      />
      <div className="p-4">
        {q.isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 9 }).map((_, i) => (
              <Skeleton key={i} className="h-8" />
            ))}
          </div>
        ) : (
          <>
            <div className="space-y-2">
              {Object.entries(w).map(([k, v]) => (
                <div key={k} className="grid grid-cols-[1fr_56px] items-center gap-2 text-xs sm:grid-cols-[180px_1fr_64px] sm:gap-3">
                  <label htmlFor={k}>{titleCase(k)}</label>
                  <input
                    id={k}
                    type="range"
                    min={0}
                    max={0.4}
                    step={0.01}
                    value={v}
                    onChange={(e) => setW((x) => ({ ...x, [k]: Number(e.target.value) }))}
                    className="col-span-2 accent-accent sm:col-span-1"
                  />
                  <span className="text-right tabular-nums text-muted">{Number(v).toFixed(2)}</span>
                </div>
              ))}
            </div>
            <div className="mt-4 flex flex-col items-start gap-3 text-xs sm:flex-row sm:items-center sm:justify-between">
              <span className={total > 1.001 || total < 0.999 ? "text-medium" : "text-low"}>
                Sum: {total.toFixed(2)} {Math.abs(total - 1) > 0.001 && "(auto-normalised on save)"}
              </span>
              <Button variant="primary" size="sm" onClick={save} disabled={update.isPending}>
                <Save size={13} /> {update.isPending ? "Saving…" : "Save & re-score"}
              </Button>
            </div>
          </>
        )}
      </div>
    </Card>
  );
}

function CrqcCard() {
  const q = useMoscaAssumption();
  const update = useUpdateMoscaAssumption();
  const toast = useToast();
  const [years, setYears] = useState(15);
  const [note, setNote] = useState("");

  useEffect(() => {
    if (q.data) {
      setYears(q.data.crqc_horizon_years);
      setNote(q.data.note);
    }
  }, [q.data]);

  const save = () =>
    update.mutate(
      { crqc_horizon_years: years, note },
      {
        onSuccess: () => toast({ kind: "success", title: "Assumption updated", body: "Mosca re-evaluated for all scans." }),
        onError: (e) => toast({ kind: "error", title: "Save failed", body: String(e) }),
      },
    );

  return (
    <Card>
      <CardHeader title="CRQC horizon (Mosca Z)" subtitle="A clearly-labelled assumption, not a prediction." />
      <div className="space-y-3 p-4 text-xs">
        {q.isLoading ? (
          <Skeleton className="h-40" />
        ) : (
          <>
            <label className="block">
              <span className="mb-1 block text-muted">Years until a cryptographically-relevant quantum computer</span>
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={1}
                  max={40}
                  value={years}
                  onChange={(e) => setYears(Number(e.target.value))}
                  className="flex-1 accent-accent"
                />
                <Input
                  type="number"
                  min={1}
                  max={60}
                  value={years}
                  onChange={(e) => setYears(Number(e.target.value))}
                  className="w-20"
                />
              </div>
            </label>
            <label className="block">
              <span className="mb-1 block text-muted">Assumption note (shown on every Mosca result)</span>
              <textarea
                value={note}
                onChange={(e) => setNote(e.target.value)}
                rows={4}
                className="w-full rounded-lg border border-border bg-surface p-2 text-xs"
              />
            </label>
            <Button variant="primary" size="sm" onClick={save} disabled={update.isPending}>
              <Save size={13} /> {update.isPending ? "Saving…" : "Save & re-evaluate"}
            </Button>
          </>
        )}
      </div>
    </Card>
  );
}
