import { useState } from "react";
import { Download, FileText } from "lucide-react";
import { useGenerateReport, useReports } from "@/api/hooks";
import { downloadFile } from "@/api/client";
import { useActiveScan } from "@/store/scan";
import { useAuth } from "@/store/auth";
import { useToast } from "@/components/ui/toast";
import { PageHeader } from "@/components/layout/PageHeader";
import { Button, Card, CardHeader, EmptyState, Select, Skeleton } from "@/components/ui/primitives";
import { fmtBytes, relTime, titleCase } from "@/lib/utils";

const TYPES = [
  ["inventory", "Cryptographic Inventory"],
  ["algorithms", "Algorithm / Version / Protocol"],
  ["vulnerability", "Quantum Vulnerability & Risk"],
  ["exposure", "Sensitive-Data Exposure"],
  ["recommendations", "PQC Recommendations"],
  ["migration_roadmap", "Migration Priority Roadmap"],
  ["executive_summary", "Executive Summary"],
  ["full", "Full Combined Report"],
];

export default function Reports() {
  const reports = useReports();
  const gen = useGenerateReport();
  const { can } = useAuth();
  const { scanId } = useActiveScan();
  const toast = useToast();
  const [type, setType] = useState("executive_summary");
  const [format, setFormat] = useState("pdf");

  const run = () =>
    gen.mutate(
      { type, format, scan_id: scanId },
      {
        onSuccess: (r) =>
          toast({ kind: "success", title: "Report ready", body: `${r.filename} (${fmtBytes(r.size_bytes)})` }),
        onError: (e) => toast({ kind: "error", title: "Generation failed", body: String(e) }),
      },
    );

  return (
    <>
      <PageHeader title="Reports" description="Generate and download inventory, risk, exposure and roadmap reports" />
      <div className="grid gap-5 p-4 sm:p-6 lg:p-8 xl:grid-cols-[360px_minmax(0,1fr)]">
        <Card className="h-fit">
          <CardHeader title="Generate report" subtitle={can("report:generate") ? undefined : "Requires analyst or admin"} />
          <div className="space-y-3 p-4">
            <label className="block text-xs">
              <span className="mb-1 block text-muted">Report type</span>
              <Select value={type} onChange={(e) => setType(e.target.value)}>
                {TYPES.map(([v, l]) => (
                  <option key={v} value={v}>
                    {l}
                  </option>
                ))}
              </Select>
            </label>
            <label className="block text-xs">
              <span className="mb-1 block text-muted">Format</span>
              <Select value={format} onChange={(e) => setFormat(e.target.value)}>
                <option value="pdf">PDF (HTML fallback)</option>
                <option value="json">JSON</option>
                <option value="csv">CSV</option>
              </Select>
            </label>
            <Button variant="primary" className="w-full" onClick={run} disabled={!can("report:generate") || gen.isPending}>
              <FileText size={14} /> {gen.isPending ? "Generating…" : "Generate"}
            </Button>
            <p className="text-2xs text-muted">
              Reports are built from the latest completed scan's CBOM, risk, Mosca and recommendation data.
            </p>
          </div>
        </Card>

        <Card>
          <CardHeader title="Export history" />
          {reports.isLoading ? (
            <div className="space-y-2 p-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-12" />
              ))}
            </div>
          ) : !reports.data?.length ? (
            <EmptyState title="No reports yet" hint="Generate your first report from the panel on the left." />
          ) : (
            <div className="divide-y divide-border">
              {reports.data.map((r) => (
                <div key={r.report_id} className="flex items-center justify-between gap-3 px-4 py-2.5 text-xs">
                  <div className="min-w-0">
                    <div className="truncate font-medium">{titleCase(r.type)}</div>
                    <div className="text-2xs text-muted">
                      {r.format.toUpperCase()} · {fmtBytes(r.size_bytes)} · {relTime(r.created_at)}
                    </div>
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => downloadFile(`/reports/${r.report_id}/download`, r.filename)}
                  >
                    <Download size={13} /> Download
                  </Button>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </>
  );
}
