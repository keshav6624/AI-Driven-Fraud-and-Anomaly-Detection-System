"""Member / project schemas — unified 'project' view of each MP allocation."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class MemberBase(BaseModel):
    member_id: int
    sr_no: int
    state: str
    mp_name: str
    mp_name_clean: str
    constituency: str
    constituency_base: str
    constituency_category: str

    model_config = {"from_attributes": True}


class EntitlementOut(BaseModel):
    allocated_amount: Optional[float] = None
    amount_missing: bool
    amount_has_paise: bool
    allocated_amount_raw: Optional[str] = None
    source_file: str
    dataset_version: str

    model_config = {"from_attributes": True}


class FeatureOut(BaseModel):
    benchmark_amount: float
    benchmark_ratio: Optional[float] = None
    deviation_from_benchmark_pct: Optional[float] = None
    state_deviation_pct: Optional[float] = None
    state_percentile: Optional[float] = None
    national_percentile: Optional[float] = None
    paise_component: Optional[float] = None
    excess_over_benchmark_cr: Optional[float] = None
    shortfall_ratio: Optional[float] = None
    benchmark_verdict: str
    peer_state_n: int

    model_config = {"from_attributes": True}


class AnomalyOut(BaseModel):
    score_robust_z: float
    flag_robust_z: bool
    score_isolation_forest: float
    flag_isolation_forest: bool
    score_lof: float
    flag_lof: bool
    anomaly_votes: int
    ensemble_score: float
    is_anomaly: bool
    reasons: list[str] = []
    model_version: str
    detected_at: Optional[datetime] = None

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class RiskOut(BaseModel):
    risk_score: float
    risk_level: str
    financial_risk: float
    data_quality_risk: float
    duplicate_risk: float
    interest_risk: float
    max_duplicate_similarity: Optional[float] = None
    flagged_duplicate_pair: bool
    risk_escalated: bool
    model_version: str
    computed_at: Optional[datetime] = None

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class ExplanationOut(BaseModel):
    risk_factors: list[str] = []
    recommended_actions: list[str] = []
    lofo_attribution: dict = {}
    model_version: str

    model_config = {"from_attributes": True, "protected_namespaces": ()}


class ProjectDetail(BaseModel):
    """Full project (MP allocation) detail including all ML scores."""
    member_id: int
    sr_no: int
    state: str
    mp_name: str
    mp_name_clean: str
    constituency: str
    constituency_base: str
    constituency_category: str
    entitlement: EntitlementOut
    features: FeatureOut
    anomaly: Optional[AnomalyOut] = None
    risk: Optional[RiskOut] = None
    explanation: Optional[ExplanationOut] = None


class ProjectListItem(BaseModel):
    """Summary row for the project list table."""
    member_id: int
    sr_no: int
    state: str
    mp_name: str
    constituency: str
    allocated_amount: Optional[float] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    is_anomaly: Optional[bool] = None
    ensemble_score: Optional[float] = None


class ProjectListResponse(BaseModel):
    items: list[ProjectListItem]
    total: int
    page: int
    page_size: int


class RiskDistribution(BaseModel):
    low: int
    medium: int
    high: int
    critical: int


class MapPoint(BaseModel):
    member_id: int
    mp_name: str
    state: str
    constituency: str
    allocated_amount: Optional[float] = None
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    is_anomaly: Optional[bool] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
