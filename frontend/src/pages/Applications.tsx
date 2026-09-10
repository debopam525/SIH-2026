import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { ChevronRight, Save } from "lucide-react";
import { useApplication, useApplications, useUpdateApplication } from "@/api/hooks";
import { useAuth } from "@/store/auth";
import { useToast } from "@/components/ui/toast";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button, Card, EmptyState, Input, Skeleton } from "@/components/ui/primitives";
import { QuantumBadge, RiskBadge } from "@/components/badges";
import { Drawer } from "@/components/ui/Drawer";
import type { Application } from "@/api/types";

export default function Applications() {
  const apps = useApplications();
  const [openId, setOpenId] = useState<string>();

  return (
    <>
      <PageHeader
        title="Applications"
        description="Systems ranked by cryptographic exposure. Add metadata to sharpen risk & Mosca scoring."
      />
      <div className="p-4 sm:p-6 lg:p-8">
        {apps.isLoading ? (
          <div className="space-y-2">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16" />
            ))}
          </div>
        ) : !apps.data?.length ? (
          <Card>
            <EmptyState title="No applications" hint="Applications are created automatically when you run a scan." />
          </Card>
        ) : (
          <Card>
            <div className="divide-y divide-border">
              {apps.data.map((app) => (
                <button
                  key={app.app_id}
                  onClick={() => setOpenId(app.app_id)}
                  className="flex w-full items-center gap-4 px-4 py-3 text-left hover:bg-surface-2"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate font-medium">{app.name}</span>
                      <RiskBadge value={app.max_risk_category} />
                    </div>
                    <div className="mt-0.5 text-2xs text-muted">
                      {app.owner ?? "no owner"} · {app.business_unit ?? "no BU"} ·{" "}
                      {app.business_criticality ? `criticality ${app.business_criticality}/5` : "criticality unset"}
                    </div>
                  </div>
                  <div className="hidden gap-6 text-right text-xs sm:flex">
                    <Metric label="Assets" value={app.asset_count} />
                    <Metric label="Crit/High" value={app.vulnerable_count} tone="text-critical" />
                    <Metric label="Exposure" value={app.exposure_score.toFixed(1)} />
                  </div>
                  <ChevronRight size={16} className="text-muted" />
                </button>
              ))}
            </div>
          </Card>
        )}
      </div>
      <AppDrawer appId={openId} onClose={() => setOpenId(undefined)} />
    </>
  );
}

function Metric({ label, value, tone }: { label: string; value: React.ReactNode; tone?: string }) {
  return (
    <div>
      <div className="text-2xs uppercase text-muted">{label}</div>
      <div className={`font-semibold tabular-nums ${tone ?? ""}`}>{value}</div>
    </div>
  );
}

function AppDrawer({ appId, onClose }: { appId?: string; onClose: () => void }) {
  const { data, isLoading } = useApplication(appId);
  const { can } = useAuth();
  const toast = useToast();
  const update = useUpdateApplication();
  const nav = useNavigate();
  const [form, setForm] = useState<Partial<Application>>({});

  const app = data?.application;
  const merged = { ...app, ...form } as Application;

  const save = () => {
    if (!appId) return;
    update.mutate(
      { id: appId, body: form },
      {
        onSuccess: () => {
          toast({ kind: "success", title: "Application updated", body: "Risk & Mosca re-scored." });
          setForm({});
        },
        onError: (e) => toast({ kind: "error", title: "Update failed", body: String(e) }),
      },
    );
  };

  return (
    <Drawer open={!!appId} onClose={onClose} title={app?.name ?? "Application"} subtitle={app?.description ?? undefined}>
      {isLoading || !data ? (
        <div className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-16" />
          ))}
        </div>
      ) : (
        <div className="space-y-5">
          <section>
            <h4 className="mb-2 text-2xs font-semibold uppercase tracking-wide text-muted">
              Metadata (feeds risk + Mosca)
            </h4>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <Field label="Owner">
                <Input
                  defaultValue={app?.owner ?? ""}
                  disabled={!can("settings:write")}
                  onChange={(e) => setForm((f) => ({ ...f, owner: e.target.value }))}
                />
              </Field>
              <Field label="Business unit">
                <Input
                  defaultValue={app?.business_unit ?? ""}
                  disabled={!can("settings:write")}
                  onChange={(e) => setForm((f) => ({ ...f, business_unit: e.target.value }))}
                />
              </Field>
              <NumField label="Business criticality (1-5)" value={merged.business_criticality} min={1} max={5}
                disabled={!can("settings:write")}
                onChange={(v) => setForm((f) => ({ ...f, business_criticality: v }))} />
              <NumField label="Data sensitivity (1-5)" value={merged.data_sensitivity} min={1} max={5}
                disabled={!can("settings:write")}
                onChange={(v) => setForm((f) => ({ ...f, data_sensitivity: v }))} />
              <NumField label="Data lifetime (years)" value={merged.data_lifetime_years} min={0} max={60}
                disabled={!can("settings:write")}
                onChange={(v) => setForm((f) => ({ ...f, data_lifetime_years: v }))} />
              <NumField label="System lifetime (years)" value={merged.system_lifetime_years} min={0} max={60}
                disabled={!can("settings:write")}
                onChange={(v) => setForm((f) => ({ ...f, system_lifetime_years: v }))} />
            </div>
            {can("settings:write") && (
              <Button
                variant="primary"
                size="sm"
                className="mt-3"
                onClick={save}
                disabled={Object.keys(form).length === 0 || update.isPending}
              >
                <Save size={13} /> {update.isPending ? "Saving…" : "Save & re-score"}
              </Button>
            )}
          </section>

          <section>
            <h4 className="mb-2 text-2xs font-semibold uppercase tracking-wide text-muted">
              Associated assets ({data.assets.length})
            </h4>
            <div className="divide-y divide-border rounded-lg border border-border">
              {data.assets.map((a) => (
                <button
                  key={a.asset_id}
                  onClick={() => nav(`/assets/${a.asset_id}`)}
                  className="flex w-full items-center justify-between gap-2 px-3 py-2 text-left text-xs hover:bg-surface-2"
                >
                  <span className="min-w-0">
                    <span className="font-medium">{a.algorithm}</span>{" "}
                    <span className="text-muted">{a.usage_location}</span>
                  </span>
                  <span className="flex shrink-0 gap-1.5">
                    <QuantumBadge value={a.quantum_status} />
                    <RiskBadge value={a.risk_category} />
                  </span>
                </button>
              ))}
            </div>
          </section>
        </div>
      )}
    </Drawer>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <span className="mb-1 block text-muted">{label}</span>
      {children}
    </label>
  );
}
function NumField({
  label,
  value,
  min,
  max,
  disabled,
  onChange,
}: {
  label: string;
  value: number | null | undefined;
  min: number;
  max: number;
  disabled?: boolean;
  onChange: (v: number) => void;
}) {
  return (
    <Field label={label}>
      <Input
        type="number"
        min={min}
        max={max}
        defaultValue={value ?? ""}
        disabled={disabled}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </Field>
  );
}
