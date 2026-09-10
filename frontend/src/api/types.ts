// Hand-authored to mirror backend app/schemas.py. To regenerate from the live spec instead:
//   npx openapi-typescript http://localhost:8000/api/v1/openapi.json -o src/api/schema.d.ts

export type Role = "admin" | "analyst" | "viewer";
export type RiskCategory = "critical" | "high" | "medium" | "low";
export type QuantumStatus =
  | "quantum-vulnerable"
  | "quantum-weakened"
  | "quantum-safe"
  | "broken-classical"
  | "unknown";
export type Confidence = "confirmed_api" | "strong_textual" | "weak_textual" | "ml_classified";
export type ScanType = "source" | "dependency" | "config" | "binary" | "container";
export type ScanStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  role: Role;
  email: string;
}

export interface Me {
  user_id: string;
  email: string;
  full_name: string;
  role: Role;
  org_id: string;
  capabilities: string[];
}

export interface Scan {
  scan_id: string;
  target: string;
  target_kind: string;
  scan_types: ScanType[];
  status: ScanStatus;
  progress: number;
  stage: string;
  start_time: string | null;
  end_time: string | null;
  scanner_versions: Record<string, string>;
  stats: Record<string, unknown>;
  errors: { scanner?: string; path?: string; error: string }[];
  created_by: string | null;
  created_at: string;
}

export interface Evidence {
  evidence_id: string;
  location_kind: string;
  location: string;
  line_or_offset: string;
  function_or_scope: string;
  matched_indicator: string;
  surrounding_context: string;
  confidence: Confidence;
  detector: string;
  signature_id: string;
}

export interface Asset {
  asset_id: string;
  scan_id: string;
  app_id: string | null;
  application_name: string | null;
  asset_name: string;
  algorithm: string;
  algorithm_family: string;
  primitive: string;
  version: string;
  key_size: string;
  mode: string;
  protocol: string;
  library_dependency: string;
  usage_location: string;
  asset_type: string;
  sources: string[];
  detection_confidence: Confidence;
  risk_category: RiskCategory | null;
  weighted_score: number | null;
  quantum_status: QuantumStatus | null;
  migration_priority: RiskCategory | null;
  evidence_count: number;
}

export interface RiskFactor {
  value: number;
  rationale: string;
  source: "derived" | "application" | "default";
}

export interface AssetDetail extends Asset {
  evidence: Evidence[];
  quantum: {
    status: QuantumStatus;
    shor_impact: string;
    grover_impact: string;
    posture: string;
    harvest_now_decrypt_later: boolean;
    explanation: string;
    context_notes: string[];
    matched_family: string;
  } | null;
  risk: {
    risk_category: RiskCategory;
    weighted_score: number;
    factors: Record<string, RiskFactor>;
    weights: Record<string, number>;
    explanation: string;
  } | null;
  mosca: {
    data_lifetime_years: number;
    migration_time_years: number;
    crqc_horizon_years: number;
    sum_xy: number;
    gap_years: number;
    exposed: boolean;
    priority_result: string;
    assumptions_note: string;
    disclaimer: string;
  } | null;
  recommendation: Recommendation | null;
}

export interface Recommendation {
  use_case: string;
  current_algorithm: string;
  candidate_algorithm: string;
  recommendation_type: string;
  score: number;
  factor_scores: Record<string, number>;
  rationale: string;
  compatibility_notes: string;
  performance_memory_notes: string;
  migration_priority: RiskCategory;
  alternatives: {
    name: string;
    recommendation_type: string;
    score: number;
    factor_scores: Record<string, number>;
    notes: string;
    migration_notes: string;
  }[];
  asset_id?: string;
  asset_name?: string;
  algorithm_family?: string;
  primitive?: string;
}

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface DashboardMetrics {
  scan_id: string | null;
  generated_at: string;
  totals: Record<string, number>;
  quantum_distribution: Record<string, number>;
  risk_distribution: Record<string, number>;
  algorithm_breakdown: { name: string; count: number }[];
  family_breakdown: { name: string; count: number }[];
  migration_priority: Record<string, number>;
  recent_scans: Scan[];
  top_risky_assets: Asset[];
  confidence_distribution: Record<string, number>;
}

export interface Application {
  app_id: string;
  name: string;
  owner: string | null;
  business_unit: string | null;
  business_criticality: number | null;
  system_lifetime_years: number | null;
  data_sensitivity: number | null;
  data_lifetime_years: number | null;
  description: string | null;
  asset_count: number;
  vulnerable_count: number;
  max_risk_category: RiskCategory | null;
  exposure_score: number;
}

export interface MigrationBoard {
  scan_id: string | null;
  columns: Record<
    string,
    {
      asset_id: string;
      asset_name: string;
      algorithm: string;
      application: string | null;
      priority: RiskCategory;
      status: string;
      readiness: number;
      owner: string | null;
      recommended: string | null;
      recommendation_type: string | null;
      planned_target_date: string | null;
    }[]
  >;
  by_application: {
    application: string;
    total: number;
    done: number;
    in_progress: number;
    progress_pct: number;
  }[];
}

export interface ReportMeta {
  report_id: string;
  type: string;
  format: string;
  scan_id: string | null;
  created_at: string;
  size_bytes: number;
  filename: string;
}

export interface Facets {
  algorithm_family: string[];
  confidence: string[];
  source: string[];
  quantum_status: string[];
  risk_category: string[];
  applications: { app_id: string; name: string }[];
}
