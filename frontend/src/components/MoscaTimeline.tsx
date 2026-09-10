import { Info } from "lucide-react";
import type { AssetDetail } from "@/api/types";

type Mosca = NonNullable<AssetDetail["mosca"]>;

export function MoscaTimeline({ mosca }: { mosca: Mosca }) {
  const { data_lifetime_years: x, migration_time_years: y, crqc_horizon_years: z } = mosca;
  const scale = Math.max(x + y, z) * 1.1 || 1;
  const pct = (v: number) => `${(v / scale) * 100}%`;

  return (
    <div>
      <div className="relative h-14">
        {/* X + Y bar */}
        <div className="absolute top-1 h-4 rounded bg-accent/70" style={{ width: pct(x) }} title={`X data lifetime ${x}y`} />
        <div
          className="absolute top-1 h-4 rounded bg-high/70"
          style={{ left: pct(x), width: pct(y) }}
          title={`Y migration time ${y}y`}
        />
        {/* Z marker */}
        <div className="absolute top-0 h-6 w-0.5 bg-critical" style={{ left: pct(z) }} />
        <div className="absolute top-6 -translate-x-1/2 text-2xs text-critical" style={{ left: pct(z) }}>
          CRQC Z={z}y
        </div>
        <div className="absolute top-6 text-2xs text-muted">0</div>
      </div>
      <div className="mt-1 flex flex-wrap gap-3 text-2xs">
        <Legend color="bg-accent/70" label={`X data lifetime ${x}y`} />
        <Legend color="bg-high/70" label={`Y migration ${y}y`} />
        <span className="text-muted">
          X + Y = <b className="text-text">{mosca.sum_xy}y</b> · gap{" "}
          <b className={mosca.exposed ? "text-critical" : "text-low"}>
            {mosca.gap_years > 0 ? "+" : ""}
            {mosca.gap_years}y
          </b>{" "}
          · {mosca.exposed ? "EXPOSED" : "not exposed"} · priority {mosca.priority_result}
        </span>
      </div>
      <p className="mt-2 flex items-start gap-1.5 rounded-md bg-surface-2 p-2 text-2xs text-muted">
        <Info size={12} className="mt-0.5 shrink-0" />
        {mosca.assumptions_note}
      </p>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="flex items-center gap-1 text-muted">
      <span className={`inline-block h-2 w-2 rounded-sm ${color}`} /> {label}
    </span>
  );
}
