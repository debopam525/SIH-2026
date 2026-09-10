import {
  ShieldAlert,
  ShieldX,
  ShieldCheck,
  ShieldQuestion,
  Shield,
  CircleDot,
  Loader2,
  CheckCircle2,
  XCircle,
  Ban,
} from "lucide-react";
import { Badge } from "@/components/ui/primitives";
import { QUANTUM_LABEL, titleCase } from "@/lib/utils";
import type { Confidence, QuantumStatus, RiskCategory, ScanStatus } from "@/api/types";

const RISK_TONE: Record<string, "critical" | "high" | "medium" | "low" | "neutral"> = {
  critical: "critical",
  high: "high",
  medium: "medium",
  low: "low",
};

export function RiskBadge({ value }: { value: RiskCategory | null | undefined }) {
  if (!value) return <Badge tone="neutral">n/a</Badge>;
  const Icon = value === "critical" || value === "high" ? ShieldAlert : Shield;
  return (
    <Badge tone={RISK_TONE[value]}>
      <Icon size={11} aria-hidden />
      {titleCase(value)}
    </Badge>
  );
}

const Q_TONE: Record<QuantumStatus, "critical" | "high" | "medium" | "low" | "neutral"> = {
  "quantum-vulnerable": "critical",
  "broken-classical": "critical",
  "quantum-weakened": "medium",
  "quantum-safe": "low",
  unknown: "neutral",
};
const Q_ICON: Record<QuantumStatus, typeof Shield> = {
  "quantum-vulnerable": ShieldAlert,
  "broken-classical": ShieldX,
  "quantum-weakened": ShieldQuestion,
  "quantum-safe": ShieldCheck,
  unknown: ShieldQuestion,
};

export function QuantumBadge({ value }: { value: QuantumStatus | null | undefined }) {
  if (!value) return <Badge tone="neutral">n/a</Badge>;
  const Icon = Q_ICON[value];
  return (
    <Badge tone={Q_TONE[value]}>
      <Icon size={11} aria-hidden />
      {QUANTUM_LABEL[value] ?? value}
    </Badge>
  );
}

const CONF_TONE: Record<Confidence, "low" | "medium" | "high" | "neutral"> = {
  confirmed_api: "low",
  strong_textual: "medium",
  weak_textual: "high",
  ml_classified: "neutral",
};
export function ConfidenceBadge({ value }: { value: Confidence }) {
  return <Badge tone={CONF_TONE[value]}>{titleCase(value)}</Badge>;
}

export function StatusChip({ status }: { status: ScanStatus | string }) {
  const map: Record<string, { tone: "low" | "accent" | "critical" | "neutral"; icon: typeof CircleDot }> =
    {
      completed: { tone: "low", icon: CheckCircle2 },
      running: { tone: "accent", icon: Loader2 },
      queued: { tone: "neutral", icon: CircleDot },
      failed: { tone: "critical", icon: XCircle },
      cancelled: { tone: "neutral", icon: Ban },
    };
  const m = map[status] ?? { tone: "neutral" as const, icon: CircleDot };
  const Icon = m.icon;
  return (
    <Badge tone={m.tone}>
      <Icon size={11} className={status === "running" ? "animate-spin" : ""} aria-hidden />
      {titleCase(status)}
    </Badge>
  );
}

export function RecTypeBadge({ value }: { value: string }) {
  const tone =
    value === "no_change" ? "low" : value === "hybrid" ? "accent" : value === "pqc" ? "accent" : "medium";
  return <Badge tone={tone as "low" | "accent" | "medium"}>{titleCase(value)}</Badge>;
}
