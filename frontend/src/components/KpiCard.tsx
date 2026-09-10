import type { ReactNode } from "react";
import { Card } from "@/components/ui/primitives";
import { cn } from "@/lib/utils";

export function KpiCard({
  label,
  value,
  icon,
  tone = "neutral",
  hint,
  index = 0,
}: {
  label: string;
  value: ReactNode;
  icon?: ReactNode;
  tone?: "neutral" | "critical" | "high" | "accent" | "low";
  hint?: ReactNode;
  index?: number;
}) {
  return (
    <Card
      className="group relative min-h-[142px] overflow-hidden p-5 transition-all duration-300 hover:-translate-y-0.5 hover:border-white/[0.18] hover:bg-[#0c0c0c]"
      style={{ animationDelay: `${index * 45}ms` }}
    >
      <div className="flex items-start justify-between gap-4">
        <span className="text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-500">{label}</span>
        {icon && (
          <span className={cn(
            "grid h-8 w-8 place-items-center rounded-md border transition-colors duration-300",
            tone === "neutral" || tone === "accent"
              ? "border-white/10 bg-white/[0.035] text-zinc-500 group-hover:text-white"
              : tone === "critical" ? "border-critical/20 bg-critical/[0.07] text-critical"
              : tone === "high" ? "border-high/20 bg-high/[0.07] text-high"
              : "border-low/20 bg-low/[0.07] text-low",
          )}>{icon}</span>
        )}
      </div>
      <div className={cn(
        "mt-5 text-[34px] font-semibold leading-none tracking-[-0.055em] tabular-nums",
        tone === "critical" && "text-critical",
        tone === "high" && "text-high",
        tone === "low" && "text-low",
      )}>{value}</div>
      <div className="mt-2 min-h-4 text-[11px] text-zinc-600">{hint ?? "Current scan"}</div>
      <span className={cn(
        "absolute inset-x-0 bottom-0 h-px origin-left scale-x-0 transition-transform duration-500 group-hover:scale-x-100",
        tone === "critical" ? "bg-critical/60" : tone === "high" ? "bg-high/60" : tone === "low" ? "bg-low/60" : "bg-white/50",
      )} />
    </Card>
  );
}
