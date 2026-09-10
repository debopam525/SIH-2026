import { Layers } from "lucide-react";
import { useScans } from "@/api/hooks";
import { useActiveScan } from "@/store/scan";
import { relTime } from "@/lib/utils";

export function ScanPicker() {
  const { scanId, setScanId } = useActiveScan();
  const { data } = useScans();
  const completed = (data?.items ?? []).filter((scan) => scan.status === "completed");

  const label = (scan: (typeof completed)[number]) => {
    const name = scan.target.split(/[\\/]/).pop() || scan.target;
    const assets = (scan.stats as { assets?: number })?.assets;
    return `${name} · ${assets ?? 0} assets · ${relTime(scan.created_at)}`;
  };

  return (
    <div className="flex min-h-11 items-center gap-2 border-b border-white/10 bg-black px-4 sm:px-6 lg:px-8">
      <Layers size={13} className="shrink-0 text-zinc-600" />
      <span className="hidden shrink-0 text-[10px] font-medium uppercase tracking-[0.14em] text-zinc-600 sm:inline">
        Active scan
      </span>
      <select
        value={scanId ?? ""}
        onChange={(event) => setScanId(event.target.value || undefined)}
        aria-label="Active scan"
        className="h-7 min-w-0 max-w-lg flex-1 truncate rounded-md border-0 bg-transparent px-1 text-xs text-zinc-300 focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-white/40 sm:w-[420px] sm:flex-none"
      >
        <option value="">Latest completed{completed[0] ? ` (${label(completed[0])})` : ""}</option>
        {completed.map((scan) => (
          <option key={scan.scan_id} value={scan.scan_id}>{label(scan)}</option>
        ))}
      </select>
      {completed.length === 0 && (
        <span className="hidden text-2xs text-muted sm:inline">— no completed scans yet; run one from Scans</span>
      )}
    </div>
  );
}
