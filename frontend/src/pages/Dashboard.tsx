import { Link, useNavigate } from "react-router-dom";
import { Activity, AppWindow, ArrowUpRight, Atom, Boxes, Plus, ShieldAlert, Siren } from "lucide-react";
import { useDashboard } from "@/api/hooks";
import { useActiveScan } from "@/store/scan";
import { PageHeader } from "@/components/layout/PageHeader";
import { KpiCard } from "@/components/KpiCard";
import { BarBreakdown, DonutChart } from "@/components/charts";
import { QuantumBadge, RiskBadge, StatusChip } from "@/components/badges";
import { Button, Card, CardHeader, EmptyState, Skeleton } from "@/components/ui/primitives";
import { relTime, titleCase } from "@/lib/utils";

const DOTS: Record<string, string> = {
  critical: "bg-critical", high: "bg-high", medium: "bg-medium", low: "bg-low",
  "quantum-vulnerable": "bg-critical", "broken-classical": "bg-critical",
  "quantum-weakened": "bg-medium", "quantum-safe": "bg-low", unknown: "bg-zinc-600",
};

export default function Dashboard() {
  const { scanId } = useActiveScan();
  const { data, isLoading } = useDashboard(scanId);
  const navigate = useNavigate();

  if (isLoading) return <LoadingState />;
  if (!data?.scan_id) return <EmptyDashboard />;

  const totals = data.totals;
  const quantum = Object.entries(data.quantum_distribution).map(([name, count]) => ({ name, count }));
  const risk = ["critical", "high", "medium", "low"]
    .map((name) => ({ name, count: data.risk_distribution[name] ?? 0 }))
    .filter((item) => item.count > 0);
  const migration = ["critical", "high", "medium", "low"]
    .map((name) => ({ name, count: data.migration_priority[name] ?? 0 }))
    .filter((item) => item.count > 0);
  const exposedPct = totals.assets ? Math.round((totals.vulnerable / totals.assets) * 100) : 0;

  return (
    <>
      <PageHeader
        title="Security overview"
        description={`Estate posture from scan ${data.scan_id.slice(0, 12)} · refreshed ${relTime(data.generated_at)}`}
        actions={<Link to="/scans"><Button size="sm" variant="primary"><Plus size={14} /> New scan</Button></Link>}
      />

      <div className="dashboard-grid space-y-5 p-4 sm:p-6 lg:p-8">
        {totals.assets === 0 && (
          <div className="flex items-start gap-3 rounded-lg border border-medium/25 bg-medium/[0.055] px-4 py-3 text-xs leading-5 text-medium">
            <Activity size={15} className="mt-0.5 shrink-0" />
            <span>No cryptographic assets were detected in this scan. Select another scan or run a broader discovery pass.</span>
          </div>
        )}

        <section aria-label="Key metrics" className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <KpiCard index={0} label="Total assets" value={totals.assets} icon={<Boxes size={16} />} hint="Across this scan" />
          <KpiCard index={1} label="Quantum exposed" value={totals.vulnerable} tone="critical" icon={<ShieldAlert size={16} />} hint={`${exposedPct}% of inventory`} />
          <KpiCard index={2} label="Critical risk" value={totals.critical} tone="critical" icon={<Siren size={16} />} hint="Immediate review" />
          <KpiCard index={3} label="Apps at risk" value={totals.apps_at_risk} tone="high" icon={<AppWindow size={16} />} hint="Business systems" />
          <KpiCard index={4} label="PQC ready" value={totals.already_pqc} tone="low" icon={<Atom size={16} />} hint="Protected assets" />
        </section>

        <section className="grid gap-5 xl:grid-cols-12">
          <Card className="overflow-hidden xl:col-span-5">
            <CardHeader title="Quantum exposure" subtitle="Inventory grouped by cryptographic resilience" actions={<span className="text-[10px] text-zinc-600">{totals.assets} TOTAL</span>} />
            <div className="grid items-center px-5 pb-5 sm:grid-cols-[minmax(0,1fr)_180px] xl:grid-cols-1 2xl:grid-cols-[minmax(0,1fr)_170px]">
              <DonutChart data={quantum} colorBy="severity" />
              <DistributionList data={quantum} total={totals.assets} />
            </div>
          </Card>

          <div className="grid gap-5 xl:col-span-7">
            <Card className="overflow-hidden">
              <CardHeader title="Risk concentration" subtitle="Weighted score distribution across the estate" />
              <div className="px-5 py-4">{risk.length ? <BarBreakdown data={risk} horizontal height={150} /> : <MiniEmpty />}</div>
            </Card>
            <Card className="overflow-hidden">
              <CardHeader title="Migration urgency" subtitle="Priorities derived from risk and Mosca exposure" />
              <div className="px-5 py-4">{migration.length ? <BarBreakdown data={migration} horizontal height={150} /> : <MiniEmpty />}</div>
            </Card>
          </div>
        </section>

        <section className="grid gap-5 xl:grid-cols-12">
          <Card className="overflow-hidden xl:col-span-8">
            <CardHeader
              title="Algorithm footprint"
              subtitle="Most prevalent algorithms in the active CBOM"
              actions={<TextLink to="/assets">Explore inventory</TextLink>}
            />
            <div className="px-5 py-4">
              <BarBreakdown data={data.algorithm_breakdown.slice(0, 10)} horizontal height={Math.max(220, data.algorithm_breakdown.slice(0, 10).length * 29)} />
            </div>
          </Card>
          <Card className="overflow-hidden xl:col-span-4">
            <CardHeader title="Detection confidence" subtitle="Evidence quality across discoveries" />
            <div className="px-5 py-4">
              <BarBreakdown data={Object.entries(data.confidence_distribution).map(([name, count]) => ({ name, count }))} horizontal height={260} />
            </div>
          </Card>
        </section>

        <section className="grid gap-5 lg:grid-cols-2">
          <Card className="overflow-hidden">
            <CardHeader title="Highest-risk assets" subtitle="Items requiring the earliest intervention" actions={<TextLink to="/assets">View all</TextLink>} />
            <div className="divide-y divide-white/[0.07]">
              {data.top_risky_assets.slice(0, 7).map((asset, index) => (
                <button
                  key={asset.asset_id}
                  onClick={() => navigate(`/assets/${asset.asset_id}`)}
                  className="group flex w-full items-center gap-3 px-5 py-3 text-left transition-colors hover:bg-white/[0.025]"
                >
                  <span className="w-5 shrink-0 font-mono text-[10px] text-zinc-700">{String(index + 1).padStart(2, "0")}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-xs font-medium text-zinc-200 group-hover:text-white">{asset.algorithm}</span>
                    <span className="mt-1 block truncate text-[10px] text-zinc-600">{asset.usage_location}</span>
                  </span>
                  <span className="hidden shrink-0 items-center gap-1.5 sm:flex"><QuantumBadge value={asset.quantum_status} /><RiskBadge value={asset.risk_category} /></span>
                  <ArrowUpRight size={13} className="shrink-0 text-zinc-700 transition-transform group-hover:-translate-y-0.5 group-hover:translate-x-0.5 group-hover:text-white" />
                </button>
              ))}
            </div>
          </Card>

          <Card className="overflow-hidden">
            <CardHeader title="Recent activity" subtitle="Latest discovery runs and their state" actions={<TextLink to="/scans">Scan history</TextLink>} />
            <div className="divide-y divide-white/[0.07]">
              {data.recent_scans.map((scan) => (
                <div key={scan.scan_id} className="flex items-center gap-3 px-5 py-3">
                  <span className="grid h-8 w-8 shrink-0 place-items-center rounded-md border border-white/[0.08] bg-white/[0.025] text-zinc-600"><Activity size={14} /></span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-xs font-medium text-zinc-300">{scan.target.split(/[\\/]/).pop()}</span>
                    <span className="mt-1 block text-[10px] text-zinc-600">{titleCase(scan.scan_types.join(", "))} · {relTime(scan.created_at)}</span>
                  </span>
                  <StatusChip status={scan.status} />
                </div>
              ))}
            </div>
          </Card>
        </section>
      </div>
    </>
  );
}

function DistributionList({ data, total }: { data: { name: string; count: number }[]; total: number }) {
  return (
    <div className="space-y-3 border-t border-white/[0.07] pt-4 sm:border-l sm:border-t-0 sm:pl-5 sm:pt-0 xl:border-l-0 xl:border-t xl:pl-0 xl:pt-4 2xl:border-l 2xl:border-t-0 2xl:pl-5 2xl:pt-0">
      {data.map((item) => (
        <div key={item.name} className="flex items-center gap-2.5">
          <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${DOTS[item.name] ?? "bg-zinc-600"}`} />
          <span className="min-w-0 flex-1 truncate text-[10px] text-zinc-500">{titleCase(item.name)}</span>
          <span className="font-mono text-[10px] text-zinc-300">{item.count}</span>
          <span className="w-7 text-right font-mono text-[9px] text-zinc-700">{total ? Math.round((item.count / total) * 100) : 0}%</span>
        </div>
      ))}
    </div>
  );
}

function TextLink({ to, children }: { to: string; children: string }) {
  return <Link to={to} className="group flex items-center gap-1 text-[10px] font-medium text-zinc-500 transition-colors hover:text-white">{children}<ArrowUpRight size={11} className="transition-transform group-hover:-translate-y-px group-hover:translate-x-px" /></Link>;
}

function EmptyDashboard() {
  return <><PageHeader title="Security overview" description="Estate-wide cryptographic risk and migration posture" /><div className="p-4 sm:p-6 lg:p-8"><Card><EmptyState icon={<Boxes size={28} />} title="No completed scans" hint="Run a discovery scan to build the CBOM and calculate your cryptographic risk posture." action={<Link to="/scans"><Button className="mt-3" variant="primary" size="sm"><Plus size={14} /> Start a scan</Button></Link>} /></Card></div></>;
}

function MiniEmpty() { return <div className="grid h-[150px] place-items-center text-[11px] text-zinc-600">No data available</div>; }

function LoadingState() {
  return <><PageHeader title="Security overview" /><div className="space-y-5 p-4 sm:p-6 lg:p-8"><div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">{Array.from({ length: 5 }).map((_, index) => <Skeleton key={index} className="h-[142px]" />)}</div><div className="grid gap-5 xl:grid-cols-12"><Skeleton className="h-[420px] xl:col-span-5" /><Skeleton className="h-[420px] xl:col-span-7" /></div></div></>;
}
