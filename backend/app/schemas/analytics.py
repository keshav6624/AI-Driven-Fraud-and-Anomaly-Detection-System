"""Analytics aggregation schemas."""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class StateAggregation(BaseModel):
    state: str
    total_members: int
    total_allocated: float
    mean_allocated: float
    median_allocated: float
    anomaly_count: int
    mean_risk_score: Optional[float] = None
    risk_distribution: dict = {}


class AnalyticsOverview(BaseModel):
    total_members: int
    total_allocated: float
    mean_allocated: float
    median_allocated: float
    benchmark_amount: float
    anomaly_count: int
    anomaly_rate: float
    risk_distribution: dict
    top_risk_states: list[StateAggregation]
    state_summary: list[StateAggregation]


class RiskTrend(BaseModel):
    risk_level: str
    count: int
    percentage: float


class AnomalyScatter(BaseModel):
    member_id: int
    mp_name: str
    state: str
    ensemble_score: float
    allocated_amount: Optional[float] = None
    risk_score: Optional[float] = None
    is_anomaly: bool
    risk_level: Optional[str] = None


class AnomalyDistribution(BaseModel):
    bins: list[float]
    counts: list[int]


class DuplicateSummary(BaseModel):
    total_pairs: int
    flagged_pairs: int
    flagged_rate: float
    max_similarity: float
    mean_similarity: float


class DuplicatePairOut(BaseModel):
    pair_id: int
    member_id_a: int
    member_id_b: int
    mp_name_a: str
    mp_name_b: str
    state_a: str
    state_b: str
    constituency_a: str
    constituency_b: str
    name_similarity: float
    constituency_similarity: float
    same_state: bool
    overall_similarity: float
    potential_duplicate: bool
    reason: str


class DuplicatePairsResponse(BaseModel):
    items: list[DuplicatePairOut]
    total: int
