"""Pydantic v2 request/response models. Kept in one module for a compact contract; the
generated OpenAPI schema is the source of truth for the frontend client.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- auth
class LoginRequest(BaseModel):
    # Plain str (not EmailStr): this is only a lookup key, and strict RFC/special-use
    # validation (e.g. rejecting ``.local``) is the IdP's job, not the login form's.
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    email: str


class RefreshRequest(BaseModel):
    refresh_token: str


class MeResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    role: str
    org_id: str
    capabilities: list[str]


# --------------------------------------------------------------------------- scans
class ScanCreate(BaseModel):
    target: str = Field(..., description="Local path, git URL, or uploaded-zip token")
    target_kind: Literal["path", "git", "upload"] = "path"
    scan_types: list[Literal["source", "dependency", "config", "binary", "container"]] = Field(
        default_factory=lambda: ["source", "dependency", "config"]
    )
    notes: str | None = None


class ScanOut(BaseModel):
    scan_id: str
    target: str
    target_kind: str
    scan_types: list[str]
    status: str
    progress: float
    stage: str
    start_time: datetime | None
    end_time: datetime | None
    scanner_versions: dict[str, Any]
    stats: dict[str, Any]
    errors: list[dict[str, Any]]
    created_by: str | None
    created_at: datetime


class ScanListOut(BaseModel):
    items: list[ScanOut]
    total: int


# --------------------------------------------------------------------------- assets / CBOM
class EvidenceOut(BaseModel):
    evidence_id: str
    location_kind: str
    location: str
    line_or_offset: str
    function_or_scope: str
    matched_indicator: str
    surrounding_context: str
    confidence: str
    detector: str
    signature_id: str


class AssetOut(BaseModel):
    asset_id: str
    scan_id: str
    app_id: str | None
    application_name: str | None
    asset_name: str
    algorithm: str
    algorithm_family: str
    primitive: str
    version: str
    key_size: str
    mode: str
    protocol: str
    library_dependency: str
    usage_location: str
    asset_type: str
    sources: list[str]
    detection_confidence: str
    risk_category: str | None
    weighted_score: float | None
    quantum_status: str | None
    migration_priority: str | None
    evidence_count: int


class AssetDetailOut(AssetOut):
    evidence: list[EvidenceOut]
    quantum: dict[str, Any] | None
    risk: dict[str, Any] | None
    mosca: dict[str, Any] | None
    recommendation: dict[str, Any] | None


class AssetListOut(BaseModel):
    items: list[AssetOut]
    total: int
    page: int
    page_size: int


# --------------------------------------------------------------------------- applications
class ApplicationOut(BaseModel):
    app_id: str
    name: str
    owner: str | None
    business_unit: str | None
    business_criticality: int | None
    system_lifetime_years: int | None
    data_sensitivity: int | None
    data_lifetime_years: int | None
    description: str | None
    asset_count: int
    vulnerable_count: int
    max_risk_category: str | None
    exposure_score: float


class ApplicationUpdate(BaseModel):
    owner: str | None = None
    business_unit: str | None = None
    business_criticality: int | None = Field(None, ge=1, le=5)
    system_lifetime_years: int | None = Field(None, ge=0, le=60)
    data_sensitivity: int | None = Field(None, ge=1, le=5)
    data_lifetime_years: int | None = Field(None, ge=0, le=60)
    description: str | None = None


# --------------------------------------------------------------------------- dashboard
class DashboardMetrics(BaseModel):
    scan_id: str | None
    generated_at: datetime
    totals: dict[str, int]
    quantum_distribution: dict[str, int]
    risk_distribution: dict[str, int]
    algorithm_breakdown: list[dict[str, Any]]
    family_breakdown: list[dict[str, Any]]
    migration_priority: dict[str, int]
    recent_scans: list[ScanOut]
    top_risky_assets: list[AssetOut]
    confidence_distribution: dict[str, int]


# --------------------------------------------------------------------------- settings
class RiskWeights(BaseModel):
    weights: dict[str, float]


class MoscaAssumption(BaseModel):
    crqc_horizon_years: float = Field(..., ge=1, le=60)
    note: str | None = None


# --------------------------------------------------------------------------- migration
class MigrationUpdate(BaseModel):
    status: Literal["not_started", "in_progress", "blocked", "done"] | None = None
    readiness: int | None = Field(None, ge=0, le=100)
    owner: str | None = None
    planned_target_date: datetime | None = None
    notes: str | None = None


# --------------------------------------------------------------------------- reports
class ReportRequest(BaseModel):
    type: Literal[
        "inventory", "algorithms", "vulnerability", "exposure", "recommendations",
        "migration_roadmap", "executive_summary", "full",
    ]
    format: Literal["json", "csv", "pdf"] = "json"
    scan_id: str | None = None


class ReportOut(BaseModel):
    report_id: str
    type: str
    format: str
    scan_id: str | None
    created_at: datetime
    size_bytes: int
    filename: str
