import { Link } from "react-router-dom";
import { useMigrationBoard, useUpdateMigration } from "@/api/hooks";
import { useActiveScan } from "@/store/scan";
import { useAuth } from "@/store/auth";
import { useToast } from "@/components/ui/toast";
import { PageHeader } from "@/components/layout/PageHeader";
import { Card, EmptyState, Progress, Select, Skeleton } from "@/components/ui/primitives";
import { RiskBadge } from "@/components/badges";
import { titleCase } from "@/lib/utils";

const COLS = ["critical", "high", "medium", "low"] as const;
const STATUSES = ["not_started", "in_progress", "blocked", "done"] as const;

export default function Migration() {
  const { scanId } = useActiveScan();
  const { data, isLoading } = useMigrationBoard({ scan_id: scanId });
  const { can } = useAuth();
  const update = useUpdateMigration();
  const toast = useToast();

  const setStatus = (assetId: string, status: string) =>
    update.mutate(
      { assetId, body: { status } },
      { onError: (e) => toast({ kind: "error", title: "Update failed", body: String(e) }) },
    );

  return (
    <>
      <PageHeader
        title="Migration Readiness"
        description="Kanban by priority (derived from risk + Mosca). Owners can advance status."
      />
      <div className="space-y-5 p-4 sm:p-6 lg:p-8">
        {isLoading ? (
          <div className="grid gap-3 lg:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-96" />
            ))}
          </div>
        ) : !data?.scan_id ? (
          <Card>
            <EmptyState title="No scan data" hint="Run a scan to populate the migration board." />
          </Card>
        ) : (
          <>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              {COLS.map((col) => {
                const items = data.columns[col] ?? [];
                return (
                  <div key={col} className="rounded-lg border border-white/10 bg-surface">
                    <div className="flex items-center justify-between border-b border-border px-3 py-2">
                      <span className="flex items-center gap-1.5 text-xs font-semibold">
                        <RiskBadge value={col} /> {items.length}
                      </span>
                    </div>
                    <div className="max-h-[70vh] space-y-2 overflow-y-auto p-2">
                      {items.length === 0 && (
                        <p className="px-2 py-6 text-center text-2xs text-muted">Nothing here</p>
                      )}
                      {items.map((c) => (
                        <div key={c.asset_id} className="rounded-lg border border-border bg-surface-2 p-2.5">
                          <Link
                            to={`/assets/${c.asset_id}`}
                            className="text-xs font-medium hover:text-accent hover:underline"
                          >
                            {c.asset_name}
                          </Link>
                          <div className="mt-0.5 text-2xs text-muted">{c.application ?? "unassigned"}</div>
                          {c.recommended && (
                            <div className="mt-1 text-2xs">
                              <span className="text-muted">→ </span>
                              <span className="font-mono text-accent">{c.recommended}</span>
                            </div>
                          )}
                          <div className="mt-1.5">
                            <Progress value={c.readiness} />
                          </div>
                          <div className="mt-1.5 flex items-center justify-between">
                            <span className="text-2xs text-muted">{c.owner ?? "no owner"}</span>
                            <Select
                              className="h-6 w-28 text-2xs"
                              value={c.status}
                              disabled={!can("report:generate")}
                              onChange={(e) => setStatus(c.asset_id, e.target.value)}
                            >
                              {STATUSES.map((s) => (
                                <option key={s} value={s}>
                                  {titleCase(s)}
                                </option>
                              ))}
                            </Select>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>

            <Card>
              <div className="border-b border-border px-4 py-2 text-sm font-semibold">Progress by application</div>
              <div className="divide-y divide-border">
                {data.by_application.map((r) => (
                  <div key={r.application} className="flex flex-wrap items-center gap-3 px-4 py-3 text-xs sm:flex-nowrap sm:gap-4">
                    <span className="w-full truncate font-medium sm:w-48">{r.application}</span>
                    <div className="flex-1">
                      <Progress value={r.progress_pct} />
                    </div>
                    <span className="w-full text-left text-muted sm:w-32 sm:text-right">
                      {r.done}/{r.total} done · {r.in_progress} in progress
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          </>
        )}
      </div>
    </>
  );
}
