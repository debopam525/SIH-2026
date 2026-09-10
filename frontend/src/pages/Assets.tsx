import { useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { Download, Search, ArrowUpRight } from "lucide-react";
import { useAssets, useFacets } from "@/api/hooks";
import { useActiveScan } from "@/store/scan";
import { downloadFile } from "@/api/client";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button, Card, EmptyState, Input, Select, Skeleton } from "@/components/ui/primitives";
import { ConfidenceBadge, QuantumBadge, RiskBadge } from "@/components/badges";
import { titleCase } from "@/lib/utils";
import { AssetDrawer } from "@/components/AssetDrawer";
import type { Asset } from "@/api/types";

export default function Assets() {
  const nav = useNavigate();
  const [sp, setSp] = useSearchParams();
  const { scanId } = useActiveScan();
  const facets = useFacets(scanId);

  const [q, setQ] = useState("");
  const [family, setFamily] = useState("");
  const [risk, setRisk] = useState("");
  const [quantum, setQuantum] = useState("");
  const [confidence, setConfidence] = useState("");
  const [source, setSource] = useState("");
  const [sort, setSort] = useState("risk");
  const [page, setPage] = useState(1);

  const drawerId = sp.get("asset") ?? undefined;

  const query = useMemo(
    () => ({
      scan_id: scanId,
      q: q || undefined,
      algorithm_family: family || undefined,
      risk_category: risk || undefined,
      quantum_status: quantum || undefined,
      confidence: confidence || undefined,
      source: source || undefined,
      sort,
      page,
      page_size: 40,
    }),
    [scanId, q, family, risk, quantum, confidence, source, sort, page],
  );
  const { data, isLoading, isFetching } = useAssets(query);
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1;

  return (
    <>
      <PageHeader
        title="Asset Explorer"
        description="Browse the Cryptographic Bill of Materials — filter, sort, drill into evidence"
        actions={
          <>
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                downloadFile(
                  `/cbom/export?format=json${scanId ? `&scan_id=${scanId}` : ""}`,
                  "cbom.json",
                )
              }
            >
              <Download size={13} /> CBOM JSON
            </Button>
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                downloadFile(
                  `/cbom/export?format=csv${scanId ? `&scan_id=${scanId}` : ""}`,
                  "cbom.csv",
                )
              }
            >
              <Download size={13} /> CSV
            </Button>
          </>
        }
      />
      <div className="space-y-4 p-4 sm:p-6 lg:p-8">
        <Card className="p-3">
          <div className="grid gap-2 md:grid-cols-2 lg:grid-cols-4 xl:grid-cols-7">
            <div className="relative xl:col-span-2">
              <Search size={14} className="absolute left-2.5 top-2.5 text-muted" />
              <Input
                className="pl-8"
                placeholder="algorithm, path, library…"
                value={q}
                onChange={(e) => {
                  setQ(e.target.value);
                  setPage(1);
                }}
              />
            </div>
            <FilterSelect label="Family" value={family} set={setFamily} opts={facets.data?.algorithm_family} />
            <FilterSelect label="Risk" value={risk} set={setRisk} opts={facets.data?.risk_category} />
            <FilterSelect label="Quantum" value={quantum} set={setQuantum} opts={facets.data?.quantum_status} />
            <FilterSelect label="Confidence" value={confidence} set={setConfidence} opts={facets.data?.confidence} />
            <FilterSelect label="Source" value={source} set={setSource} opts={facets.data?.source} />
          </div>
        </Card>

        <Card>
          <div className="flex items-center justify-between border-b border-border px-4 py-2 text-xs text-muted">
            <span>
              {data ? `${data.total} assets` : "…"}
              {isFetching && <span className="ml-2 animate-pulse">updating…</span>}
            </span>
            <label className="flex items-center gap-1.5">
              Sort
              <Select value={sort} onChange={(e) => setSort(e.target.value)} className="h-7 w-32 text-xs">
                <option value="risk">Risk (high→low)</option>
                <option value="algorithm">Algorithm</option>
                <option value="family">Family</option>
                <option value="confidence">Confidence</option>
                <option value="name">Name</option>
              </Select>
            </label>
          </div>

          {isLoading ? (
            <div className="space-y-1 p-3">
              {Array.from({ length: 10 }).map((_, i) => (
                <Skeleton key={i} className="h-10" />
              ))}
            </div>
          ) : !data?.items.length ? (
            <EmptyState
              title={data && data.total === 0 ? "No cryptographic assets in this scan" : "No matching assets"}
              hint={
                data && data.total === 0
                  ? "The selected scan's target has no detectable crypto. Pick another scan in the Active scan selector above, or run a new scan."
                  : "Adjust the filters above."
              }
            />
          ) : (
            <div className="overflow-x-auto [scrollbar-gutter:stable]">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-border text-left text-2xs uppercase tracking-wide text-muted">
                    <th className="px-4 py-2 font-medium">Algorithm</th>
                    <th className="px-2 py-2 font-medium">Family</th>
                    <th className="px-2 py-2 font-medium">Key / Mode</th>
                    <th className="px-2 py-2 font-medium">Quantum</th>
                    <th className="px-2 py-2 font-medium">Risk</th>
                    <th className="px-2 py-2 font-medium">Confidence</th>
                    <th className="px-2 py-2 font-medium">Location</th>
                    <th className="px-2 py-2" />
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((a) => (
                    <Row key={a.asset_id} a={a} onOpen={() => setSp({ asset: a.asset_id })} />
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {pages > 1 && (
            <div className="flex items-center justify-between border-t border-border px-4 py-2 text-xs">
              <span className="text-muted">
                Page {page} / {pages}
              </span>
              <div className="flex gap-1.5">
                <Button size="sm" variant="ghost" disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
                  Prev
                </Button>
                <Button size="sm" variant="ghost" disabled={page >= pages} onClick={() => setPage((p) => p + 1)}>
                  Next
                </Button>
              </div>
            </div>
          )}
        </Card>
      </div>

      <AssetDrawer
        assetId={drawerId}
        onClose={() => setSp({})}
        onFullPage={(id) => nav(`/assets/${id}`)}
      />
    </>
  );
}

function Row({ a, onOpen }: { a: Asset; onOpen: () => void }) {
  return (
    <tr className="cursor-pointer border-b border-border/60 last:border-0 hover:bg-surface-2" onClick={onOpen}>
      <td className="px-4 py-2">
        <div className="font-medium">{a.algorithm}</div>
        <div className="text-2xs text-muted">{a.library_dependency !== "unknown" ? a.library_dependency : a.primitive}</div>
      </td>
      <td className="px-2 py-2 text-xs text-muted">{titleCase(a.algorithm_family)}</td>
      <td className="px-2 py-2 text-xs">
        {a.key_size !== "unknown" ? a.key_size : "—"}
        {a.mode !== "unknown" ? ` / ${a.mode}` : ""}
      </td>
      <td className="px-2 py-2">
        <QuantumBadge value={a.quantum_status} />
      </td>
      <td className="px-2 py-2">
        <RiskBadge value={a.risk_category} />
      </td>
      <td className="px-2 py-2">
        <ConfidenceBadge value={a.detection_confidence} />
      </td>
      <td className="max-w-[240px] px-2 py-2">
        <div className="truncate text-2xs text-muted" title={a.usage_location}>
          {a.usage_location}
        </div>
      </td>
      <td className="px-2 py-2 text-muted">
        <ArrowUpRight size={14} />
      </td>
    </tr>
  );
}

function FilterSelect({
  label,
  value,
  set,
  opts,
}: {
  label: string;
  value: string;
  set: (v: string) => void;
  opts?: string[];
}) {
  return (
    <Select value={value} onChange={(e) => set(e.target.value)} aria-label={label}>
      <option value="">{label}: all</option>
      {(opts ?? []).map((o) => (
        <option key={o} value={o}>
          {titleCase(o)}
        </option>
      ))}
    </Select>
  );
}
