"""Analytics routes — dashboard aggregations."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.analytics import (
    AnalyticsOverview,
    AnomalyScatter,
    AnomalyDistribution,
    DuplicateSummary,
    DuplicatePairOut,
    DuplicatePairsResponse,
)
from backend.app.services import analytics_service
from backend.app.services.member_service import get_risk_distribution
from backend.app.api.deps import CurrentUser
from backend.app.ml.loader import ml_loader

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview", response_model=AnalyticsOverview)
def overview(db: Annotated[Session, Depends(get_db)], _user: CurrentUser):
    return analytics_service.get_overview(db)


@router.get("/risk-distribution")
def risk_distribution(db: Annotated[Session, Depends(get_db)], _user: CurrentUser):
    return get_risk_distribution(db)


@router.get("/anomaly/scatter", response_model=list[AnomalyScatter])
def anomaly_scatter(db: Annotated[Session, Depends(get_db)], _user: CurrentUser):
    return analytics_service.get_anomaly_scatter(db)


@router.get("/anomaly/distribution", response_model=AnomalyDistribution)
def anomaly_distribution(db: Annotated[Session, Depends(get_db)], _user: CurrentUser):
    return analytics_service.get_anomaly_distribution(db)


@router.get("/duplicates/summary", response_model=DuplicateSummary)
def duplicate_summary(db: Annotated[Session, Depends(get_db)], _user: CurrentUser):
    return analytics_service.get_duplicate_summary(db)


@router.get("/duplicates", response_model=DuplicatePairsResponse)
def list_duplicates(
    _user: CurrentUser,
    page: int = 1,
    page_size: int = 50,
    flagged_only: bool = False,
):
    df = ml_loader.duplicates
    if df.empty:
        return DuplicatePairsResponse(items=[], total=0)
    if flagged_only:
        df = df[df["potential_duplicate"] == True]
    total = len(df)
    start = (page - 1) * page_size
    rows = df.iloc[start:start + page_size]
    items = []
    for _, r in rows.iterrows():
        items.append(DuplicatePairOut(
            pair_id=0,
            member_id_a=int(r["member_id_a"]),
            member_id_b=int(r["member_id_b"]),
            mp_name_a=str(r.get("mp_name_a", "")),
            mp_name_b=str(r.get("mp_name_b", "")),
            state_a=str(r.get("state_a", "")),
            state_b=str(r.get("state_b", "")),
            constituency_a=str(r.get("constituency_a", "")),
            constituency_b=str(r.get("constituency_b", "")),
            name_similarity=float(r["name_similarity"]),
            constituency_similarity=float(r["constituency_similarity"]),
            same_state=bool(r["same_state"]),
            overall_similarity=float(r["overall_similarity"]),
            potential_duplicate=bool(r["potential_duplicate"]),
            reason=str(r.get("duplicate_reason", "")),
        ))
    return DuplicatePairsResponse(items=items, total=total)
