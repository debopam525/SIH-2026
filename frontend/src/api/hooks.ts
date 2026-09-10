import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import type {
  Application,
  Asset,
  AssetDetail,
  DashboardMetrics,
  Facets,
  MigrationBoard,
  Me,
  Paginated,
  Recommendation,
  ReportMeta,
  Scan,
} from "./types";

export const useMe = () => useQuery({ queryKey: ["me"], queryFn: () => api<Me>("/me") });

export const useDashboard = (scanId?: string) =>
  useQuery({
    queryKey: ["dashboard", scanId ?? "latest"],
    queryFn: () => api<DashboardMetrics>("/dashboard/metrics", { query: { scan_id: scanId } }),
    refetchInterval: 15_000,
  });

export const useScans = () =>
  useQuery({
    queryKey: ["scans"],
    queryFn: () => api<{ items: Scan[]; total: number }>("/scans", { query: { limit: 100 } }),
    refetchInterval: (q) =>
      (q.state.data?.items ?? []).some((s) => ["queued", "running"].includes(s.status))
        ? 1500
        : 10_000,
  });

export const useScan = (id: string | undefined) =>
  useQuery({
    queryKey: ["scan", id],
    queryFn: () => api<Scan>(`/scans/${id}`),
    enabled: !!id,
    refetchInterval: (q) =>
      q.state.data && ["queued", "running"].includes(q.state.data.status) ? 1200 : false,
  });

export const useCreateScan = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { target: string; target_kind: string; scan_types: string[] }) =>
      api<Scan>("/scans", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scans"] }),
  });
};

export const useCancelScan = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api<Scan>(`/scans/${id}/cancel`, { method: "POST" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["scans"] }),
  });
};

export const useScanDiff = (id: string | undefined) =>
  useQuery({
    queryKey: ["scan-diff", id],
    queryFn: () => api<Record<string, unknown>>(`/scans/${id}/diff`),
    enabled: !!id,
  });

export interface AssetQuery {
  scan_id?: string;
  q?: string;
  algorithm_family?: string;
  risk_category?: string;
  quantum_status?: string;
  confidence?: string;
  app_id?: string;
  source?: string;
  sort?: string;
  page?: number;
  page_size?: number;
}

export const useAssets = (query: AssetQuery) =>
  useQuery({
    queryKey: ["assets", query],
    queryFn: () => api<Paginated<Asset>>("/assets", { query: query as Record<string, string> }),
  });

export const useAsset = (id: string | undefined) =>
  useQuery({
    queryKey: ["asset", id],
    queryFn: () => api<AssetDetail>(`/assets/${id}`),
    enabled: !!id,
  });

export const useFacets = (scanId?: string) =>
  useQuery({
    queryKey: ["facets", scanId ?? "latest"],
    queryFn: () => api<Facets>("/assets/meta/facets", { query: { scan_id: scanId } }),
  });

export const useApplications = () =>
  useQuery({ queryKey: ["applications"], queryFn: () => api<Application[]>("/applications") });

export const useApplication = (id: string | undefined) =>
  useQuery({
    queryKey: ["application", id],
    queryFn: () => api<{ application: Application; assets: Asset[] }>(`/applications/${id}`),
    enabled: !!id,
  });

export const useUpdateApplication = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<Application> }) =>
      api<Application>(`/applications/${id}`, { method: "PUT", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["assets"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
};

export const useRecommendations = (query: {
  migration_priority?: string;
  recommendation_type?: string;
  scan_id?: string;
}) =>
  useQuery({
    queryKey: ["recommendations", query],
    queryFn: () =>
      api<{ items: Recommendation[]; total: number }>("/recommendations", {
        query: query as Record<string, string>,
      }),
  });

export const useMigrationBoard = (
  query: { owner?: string; business_unit?: string; scan_id?: string } = {},
) =>
  useQuery({
    queryKey: ["migration-board", query],
    queryFn: () =>
      api<MigrationBoard>("/migration/board", { query: query as Record<string, string> }),
  });

export const useUpdateMigration = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ assetId, body }: { assetId: string; body: Record<string, unknown> }) =>
      api(`/migration/${assetId}`, { method: "PUT", body }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["migration-board"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
};

export const useRiskWeights = () =>
  useQuery({ queryKey: ["risk-weights"], queryFn: () => api<{ weights: Record<string, number> }>("/settings/risk-weights") });

export const useUpdateRiskWeights = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (weights: Record<string, number>) =>
      api("/settings/risk-weights", { method: "PUT", body: { weights } }),
    onSuccess: () => qc.invalidateQueries(),
  });
};

export const useMoscaAssumption = () =>
  useQuery({
    queryKey: ["mosca-assumption"],
    queryFn: () => api<{ crqc_horizon_years: number; note: string }>("/settings/mosca-assumption"),
  });

export const useUpdateMoscaAssumption = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { crqc_horizon_years: number; note?: string }) =>
      api("/settings/mosca-assumption", { method: "PUT", body }),
    onSuccess: () => qc.invalidateQueries(),
  });
};

export const useReports = () =>
  useQuery({ queryKey: ["reports"], queryFn: () => api<ReportMeta[]>("/reports") });

export const useGenerateReport = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: { type: string; format: string; scan_id?: string }) =>
      api<ReportMeta>("/reports/generate", { method: "POST", body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["reports"] }),
  });
};

export const useRiskSummary = (scanId?: string) =>
  useQuery({
    queryKey: ["risk-summary", scanId ?? "latest"],
    queryFn: () => api<Record<string, unknown>>("/risk/summary", { query: { scan_id: scanId } }),
  });
