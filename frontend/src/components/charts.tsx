import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  PolarAngleAxis,
  PolarGrid,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { titleCase } from "@/lib/utils";

// CSS-var driven so charts follow the theme.
const cssvar = (name: string) => `rgb(var(${name}))`;
export const SEVERITY_COLOR: Record<string, string> = {
  critical: cssvar("--critical"),
  high: cssvar("--high"),
  medium: cssvar("--medium"),
  low: cssvar("--low"),
  "quantum-vulnerable": cssvar("--critical"),
  "broken-classical": cssvar("--critical"),
  "quantum-weakened": cssvar("--medium"),
  "quantum-safe": cssvar("--low"),
  unknown: cssvar("--muted"),
};
const PALETTE = [
  "#ffffff", "#d4d4d8", "#a1a1aa", "#71717a",
  "#52525b", "#3f3f46", "#27272a", "#18181b",
];

const tooltipStyle = {
  background: "#111111",
  border: "1px solid rgba(255,255,255,0.14)",
  borderRadius: 8,
  fontSize: 11,
  color: cssvar("--text"),
  boxShadow: "0 18px 48px rgba(0,0,0,0.55)",
};

export function DonutChart({
  data,
  colorBy = "severity",
}: {
  data: { name: string; count: number }[];
  colorBy?: "severity" | "palette";
}) {
  const total = data.reduce((s, d) => s + d.count, 0);
  return (
    <div className="relative h-60">
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="count"
            nameKey="name"
            innerRadius={67}
            outerRadius={94}
            paddingAngle={3}
            cornerRadius={3}
            stroke="#090909"
            strokeWidth={3}
            animationDuration={900}
            animationEasing="ease-out"
          >
            {data.map((d, i) => (
              <Cell
                key={d.name}
                fill={
                  colorBy === "severity"
                    ? SEVERITY_COLOR[d.name] ?? PALETTE[i % PALETTE.length]
                    : PALETTE[i % PALETTE.length]
                }
              />
            ))}
          </Pie>
          <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: "#fff" }} formatter={(v: number, n: string) => [v, titleCase(n)]} />
        </PieChart>
      </ResponsiveContainer>
      <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
        <span className="text-3xl font-semibold tracking-[-0.05em] tabular-nums">{total}</span>
        <span className="mt-1 text-[9px] font-medium uppercase tracking-[0.15em] text-zinc-600">assets</span>
      </div>
    </div>
  );
}

export function BarBreakdown({
  data,
  color,
  horizontal = true,
  height = 220,
}: {
  data: { name: string; count: number }[];
  color?: string;
  horizontal?: boolean;
  height?: number;
}) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={data} layout={horizontal ? "vertical" : "horizontal"} margin={{ left: 4, right: 16, top: 4, bottom: 4 }}>
          <CartesianGrid horizontal={!horizontal} vertical={horizontal} stroke="rgba(255,255,255,0.045)" strokeDasharray="2 6" />
          {horizontal ? (
            <>
              <XAxis type="number" hide />
              <YAxis
                type="category"
                dataKey="name"
                width={110}
                tick={{ fontSize: 10, fill: "#71717a" }}
                axisLine={false}
                tickLine={false}
                tickFormatter={titleCase}
              />
            </>
          ) : (
            <>
              <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: "#71717a" }} tickFormatter={titleCase} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 10, fill: "#71717a" }} allowDecimals={false} />
            </>
          )}
          <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: "#fff" }} cursor={{ fill: "rgba(255,255,255,0.025)" }} />
          <Bar dataKey="count" radius={[3, 3, 3, 3]} barSize={10} fill={color ?? cssvar("--accent")} background={{ fill: "rgba(255,255,255,0.035)", radius: 3 }} animationDuration={800}>
            {data.map((d, i) => (
              <Cell key={i} fill={SEVERITY_COLOR[d.name] ?? color ?? cssvar("--accent")} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}

export function FactorRadar({ factors }: { factors: Record<string, { value: number }> }) {
  const data = Object.entries(factors).map(([k, v]) => ({ factor: titleCase(k), value: v.value }));
  return (
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} outerRadius="72%">
          <PolarGrid stroke="rgba(255,255,255,0.1)" />
          <PolarAngleAxis dataKey="factor" tick={{ fontSize: 9, fill: cssvar("--muted") }} />
          <Radar dataKey="value" stroke="#fff" fill="#fff" fillOpacity={0.12} animationDuration={900} />
          <Tooltip contentStyle={tooltipStyle} itemStyle={{ color: "#fff" }} />
        </RadarChart>
      </ResponsiveContainer>
    </div>
  );
}
