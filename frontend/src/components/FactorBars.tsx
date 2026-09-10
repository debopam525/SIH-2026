import type { RiskFactor } from "@/api/types";
import { titleCase } from "@/lib/utils";

const SRC_TONE: Record<string, string> = {
  derived: "text-muted",
  application: "text-accent",
  default: "text-medium",
};

export function FactorBars({
  factors,
  weights,
}: {
  factors: Record<string, RiskFactor>;
  weights: Record<string, number>;
}) {
  const rows = Object.entries(factors).sort(
    (a, b) => b[1].value * (weights[b[0]] ?? 0) - a[1].value * (weights[a[0]] ?? 0),
  );
  return (
    <div className="space-y-1.5">
      {rows.map(([name, f]) => {
        const w = weights[name] ?? 0;
        const contrib = (f.value * w).toFixed(2);
        return (
          <div key={name} className="grid grid-cols-[130px_1fr_auto] items-center gap-2 text-2xs">
            <span className="truncate" title={f.rationale}>
              {titleCase(name)}
            </span>
            <div className="h-2 rounded-full bg-surface-2">
              <div
                className="h-full rounded-full bg-accent"
                style={{ width: `${(f.value / 5) * 100}%` }}
                aria-label={`${f.value} of 5`}
              />
            </div>
            <span className="tabular-nums text-muted">
              {f.value}/5 · w{w.toFixed(2)} ={" "}
              <span className="font-medium text-text">{contrib}</span>{" "}
              <span className={SRC_TONE[f.source]}>({f.source})</span>
            </span>
          </div>
        );
      })}
    </div>
  );
}
