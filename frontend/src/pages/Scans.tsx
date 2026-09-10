import { useState } from "react";
import { Link } from "react-router-dom";
import { Play, Ban, GitCompare, AlertTriangle } from "lucide-react";
import { useCancelScan, useCreateScan, useScanDiff, useScans } from "@/api/hooks";
import { useAuth } from "@/store/auth";
import { useToast } from "@/components/ui/toast";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button, Card, CardHeader, EmptyState, Input, Progress, Skeleton } from "@/components/ui/primitives";
import { StatusChip } from "@/components/badges";
import { relTime, titleCase } from "@/lib/utils";
import type { Scan } from "@/api/types";

const TYPES = ["source", "dependency", "config", "binary", "container"] as const;

export default function Scans() {
  const { can } = useAuth();
  const toast = useToast();
  const scans = useScans();
  const create = useCreateScan();
  const cancel = useCancelScan();

  const [target, setTarget] = useState("");
  const [kind, setKind] = useState<"path" | "git">("path");
  const [selected, setSelected] = useState<string[]>(["source", "dependency", "config"]);
  const [diffFor, setDiffFor] = useState<string | undefined>();

  const start = () => {
    if (!target.trim()) return;
    create.mutate(
      { target: target.trim(), target_kind: kind, scan_types: selected },
      {
        onSuccess: () => {
          toast({ kind: "info", title: "Scan queued", body: "Discovery is running in the background." });
          setTarget("");
        },
        onError: (e) => toast({ kind: "error", title: "Could not start scan", body: String(e) }),
      },
    );
  };

  return (
    <>
      <PageHeader title="Scan Management" description="Start, monitor and compare cryptographic discovery scans" />
      <div className="grid gap-5 p-4 sm:p-6 lg:p-8 xl:grid-cols-[360px_minmax(0,1fr)]">
        <Card className="h-fit">
          <CardHeader title="New scan" subtitle={can("scan:start") ? undefined : "Requires analyst or admin role"} />
          <div className="space-y-3 p-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-muted">Target</label>
              <div className="flex gap-1.5">
                <select
                  value={kind}
                  onChange={(e) => setKind(e.target.value as "path" | "git")}
                  className="h-9 rounded-lg border border-border bg-surface px-2 text-xs"
                >
                  <option value="path">Local path</option>
                  <option value="git">Git URL</option>
                </select>
                <Input
                  placeholder={kind === "git" ? "https://github.com/org/repo.git" : "/srv/app or C:\\code\\app"}
                  value={target}
                  onChange={(e) => setTarget(e.target.value)}
                />
              </div>
            </div>
            <div>
              <label className="mb-1.5 block text-xs font-medium text-muted">Scan types</label>
              <div className="grid grid-cols-2 gap-1.5">
                {TYPES.map((t) => (
                  <label
                    key={t}
                    className="flex cursor-pointer items-center gap-2 rounded-lg border border-border px-2.5 py-1.5 text-xs has-[:checked]:border-accent has-[:checked]:bg-accent/10"
                  >
                    <input
                      type="checkbox"
                      className="accent-accent"
                      checked={selected.includes(t)}
                      onChange={(e) =>
                        setSelected((s) => (e.target.checked ? [...s, t] : s.filter((x) => x !== t)))
                      }
                    />
                    {titleCase(t)}
                  </label>
                ))}
              </div>
            </div>
            <Button
              variant="primary"
              className="w-full"
              onClick={start}
              disabled={!can("scan:start") || !target.trim() || selected.length === 0 || create.isPending}
            >
              <Play size={14} /> {create.isPending ? "Starting…" : "Start scan"}
            </Button>
            <p className="text-2xs text-muted">
              Scans run asynchronously. A completed scan is diffed against the previous one automatically.
            </p>
          </div>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader title="Scan history" subtitle={`${scans.data?.total ?? 0} scans`} />
            {scans.isLoading ? (
              <div className="space-y-2 p-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-14" />
                ))}
              </div>
            ) : !scans.data?.items.length ? (
              <EmptyState title="No scans yet" hint="Start your first scan from the panel on the left." />
            ) : (
              <div className="divide-y divide-border">
                {scans.data.items.map((s) => (
                  <ScanRow
                    key={s.scan_id}
                    scan={s}
                    onCancel={() => cancel.mutate(s.scan_id)}
                    canCancel={can("scan:cancel")}
                    onDiff={() => setDiffFor(s.scan_id)}
                  />
                ))}
              </div>
            )}
          </Card>

          {diffFor && <DiffPanel scanId={diffFor} onClose={() => setDiffFor(undefined)} />}
        </div>
      </div>
    </>
  );
}

function ScanRow({
  scan,
  onCancel,
  canCancel,
  onDiff,
}: {
  scan: Scan;
  onCancel: () => void;
  canCancel: boolean;
  onDiff: () => void;
}) {
  const running = ["queued", "running"].includes(scan.status);
  const stats = scan.stats as { assets?: number; files_scanned?: number };
  return (
    <div className="px-4 py-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="truncate text-sm font-medium">{scan.target.split(/[\\/]/).pop()}</span>
            <StatusChip status={scan.status} />
          </div>
          <div className="mt-0.5 text-2xs text-muted">
            {titleCase(scan.scan_types.join(", "))} · {relTime(scan.created_at)}
            {scan.status === "completed" && stats.assets != null && (
              <> · {stats.assets} assets from {stats.files_scanned} files</>
            )}
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-1.5">
          {scan.status === "completed" && (
            <Button size="sm" variant="ghost" onClick={onDiff}>
              <GitCompare size={13} /> Diff
            </Button>
          )}
          {running && canCancel && (
            <Button size="sm" variant="ghost" onClick={onCancel}>
              <Ban size={13} /> Cancel
            </Button>
          )}
        </div>
      </div>
      {running && (
        <div className="mt-2">
          <Progress value={scan.progress * 100} />
          <div className="mt-1 text-2xs text-muted">{scan.stage}</div>
        </div>
      )}
      {scan.status === "failed" && scan.errors[0] && (
        <div className="mt-2 flex items-start gap-1.5 rounded-md bg-critical/10 px-2 py-1.5 text-2xs text-critical">
          <AlertTriangle size={12} className="mt-0.5" /> {scan.errors[0].error}
        </div>
      )}
      {scan.status === "completed" && scan.errors.length > 0 && (
        <div className="mt-2 text-2xs text-muted">
          {scan.errors.length} non-fatal file warning(s) — scan continued.
        </div>
      )}
      {scan.status === "completed" && (
        <div className="mt-2 flex gap-3 text-2xs">
          <Link to="/assets" className="text-accent hover:underline">
            View CBOM →
          </Link>
        </div>
      )}
    </div>
  );
}

function DiffPanel({ scanId, onClose }: { scanId: string; onClose: () => void }) {
  const diff = useScanDiff(scanId);
  const d = diff.data as
    | {
        summary: Record<string, number>;
        added: { asset_name: string }[];
        removed: { asset_name: string }[];
        changed: { asset_name: string; changes: Record<string, [unknown, unknown]> }[];
      }
    | undefined;
  return (
    <Card>
      <CardHeader
        title="Diff vs previous scan"
        actions={
          <button className="text-xs text-muted hover:text-text" onClick={onClose}>
            close
          </button>
        }
      />
      <div className="p-4 text-xs">
        {!d ? (
          <Skeleton className="h-24" />
        ) : (
          <>
            <div className="mb-3 flex gap-3">
              {Object.entries(d.summary).map(([k, v]) => (
                <span key={k} className="rounded-md bg-surface-2 px-2 py-1">
                  {titleCase(k)}: <b>{v}</b>
                </span>
              ))}
            </div>
            <DiffList label="Added" items={d.added.map((x) => x.asset_name)} tone="text-low" />
            <DiffList label="Removed" items={d.removed.map((x) => x.asset_name)} tone="text-critical" />
            <div className="mt-2">
              <div className="font-medium text-muted">Changed</div>
              {d.changed.length === 0 && <div className="text-muted">none</div>}
              {d.changed.map((c) => (
                <div key={c.asset_name} className="ml-2">
                  {c.asset_name}:{" "}
                  {Object.entries(c.changes).map(([f, [a, b]]) => (
                    <span key={f} className="mr-2">
                      {f} <span className="text-muted">{String(a)}</span>→<b>{String(b)}</b>
                    </span>
                  ))}
                </div>
              ))}
            </div>
          </>
        )}
      </div>
    </Card>
  );
}
function DiffList({ label, items, tone }: { label: string; items: string[]; tone: string }) {
  return (
    <div className="mt-1">
      <div className="font-medium text-muted">
        {label} ({items.length})
      </div>
      {items.slice(0, 20).map((n) => (
        <div key={n} className={`ml-2 ${tone}`}>
          {n}
        </div>
      ))}
    </div>
  );
}
