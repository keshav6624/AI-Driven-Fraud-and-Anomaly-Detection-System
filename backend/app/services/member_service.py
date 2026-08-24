"""Member / Project service — queries for the unified project view."""
from __future__ import annotations

from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.app.models.orm import (
    Member,
    Entitlement,
    MpFeature,
    MemberAnomaly,
    RiskScore,
    MemberExplanation,
    State,
    Constituency,
)
from backend.app.schemas.member import (
    ProjectDetail,
    ProjectListItem,
    ProjectListResponse,
    EntitlementOut,
    FeatureOut,
    AnomalyOut,
    RiskOut,
    ExplanationOut,
    MapPoint,
)


def _build_project_detail(member: Member) -> ProjectDetail:
    ent = member.entitlement
    feat = member.features
    anom = member.anomaly
    risk = member.risk
    expl = member.explanation
    return ProjectDetail(
        member_id=member.member_id,
        sr_no=member.sr_no,
        state=member.state_rel.name,
        mp_name=member.mp_name,
        mp_name_clean=member.mp_name_clean,
        constituency=member.constituency_rel.name,
        constituency_base=member.constituency_rel.base_name,
        constituency_category=member.constituency_rel.category,
        entitlement=EntitlementOut(
            allocated_amount=ent.allocated_amount if ent else None,
            amount_missing=ent.amount_missing if ent else True,
            amount_has_paise=ent.amount_has_paise if ent else False,
            allocated_amount_raw=ent.allocated_amount_raw if ent else None,
            source_file=ent.source_file if ent else "",
            dataset_version=ent.dataset_version if ent else "",
        ) if ent else EntitlementOut(
            allocated_amount=None, amount_missing=True, amount_has_paise=False,
            allocated_amount_raw=None, source_file="", dataset_version="",
        ),
        features=FeatureOut(
            benchmark_amount=feat.benchmark_amount,
            benchmark_ratio=feat.benchmark_ratio,
            deviation_from_benchmark_pct=feat.deviation_from_benchmark_pct,
            state_deviation_pct=feat.state_deviation_pct,
            state_percentile=feat.state_percentile,
            national_percentile=feat.national_percentile,
            paise_component=feat.paise_component,
            excess_over_benchmark_cr=feat.excess_over_benchmark_cr,
            shortfall_ratio=feat.shortfall_ratio,
            benchmark_verdict=feat.benchmark_verdict,
            peer_state_n=feat.peer_state_n,
        ) if feat else None,
        anomaly=AnomalyOut(
            score_robust_z=anom.score_robust_z,
            flag_robust_z=anom.flag_robust_z,
            score_isolation_forest=anom.score_isolation_forest,
            flag_isolation_forest=anom.flag_isolation_forest,
            score_lof=anom.score_lof,
            flag_lof=anom.flag_lof,
            anomaly_votes=anom.anomaly_votes,
            ensemble_score=anom.ensemble_score,
            is_anomaly=anom.is_anomaly,
            reasons=anom.reasons if isinstance(anom.reasons, list) else [],
            model_version=anom.model_version,
            detected_at=anom.detected_at,
        ) if anom else None,
        risk=RiskOut(
            risk_score=risk.risk_score,
            risk_level=risk.risk_level,
            financial_risk=risk.financial_risk,
            data_quality_risk=risk.data_quality_risk,
            duplicate_risk=risk.duplicate_risk,
            interest_risk=risk.interest_risk,
            max_duplicate_similarity=risk.max_duplicate_similarity,
            flagged_duplicate_pair=risk.flagged_duplicate_pair,
            risk_escalated=risk.risk_escalated,
            model_version=risk.model_version,
            computed_at=risk.computed_at,
        ) if risk else None,
        explanation=ExplanationOut(
            risk_factors=expl.risk_factors if isinstance(expl.risk_factors, list) else [],
            recommended_actions=expl.recommended_actions if isinstance(expl.recommended_actions, list) else [],
            lofo_attribution=expl.lofo_attribution if isinstance(expl.lofo_attribution, dict) else {},
            model_version=expl.model_version,
        ) if expl else None,
    )


def get_project(db: Session, member_id: int) -> ProjectDetail | None:
    member = (
        db.query(Member)
        .options(
            joinedload(Member.state_rel),
            joinedload(Member.constituency_rel),
            joinedload(Member.entitlement),
            joinedload(Member.features),
            joinedload(Member.anomaly),
            joinedload(Member.risk),
            joinedload(Member.explanation),
        )
        .filter(Member.member_id == member_id)
        .first()
    )
    if not member:
        return None
    return _build_project_detail(member)


def list_projects(
    db: Session,
    page: int = 1,
    page_size: int = 20,
    state: Optional[str] = None,
    risk_level: Optional[str] = None,
    is_anomaly: Optional[bool] = None,
    search: Optional[str] = None,
    sort_by: str = "member_id",
    sort_order: str = "asc",
) -> ProjectListResponse:
    q = (
        db.query(Member)
        .join(State, Member.state_id == State.state_id)
        .join(Constituency, Member.constituency_id == Constituency.constituency_id)
        .outerjoin(Entitlement, Member.member_id == Entitlement.member_id)
        .outerjoin(MemberAnomaly, Member.member_id == MemberAnomaly.member_id)
        .outerjoin(RiskScore, Member.member_id == RiskScore.member_id)
    )
    if state:
        q = q.filter(State.name == state)
    if risk_level:
        q = q.filter(RiskScore.risk_level == risk_level)
    if is_anomaly is not None:
        q = q.filter(MemberAnomaly.is_anomaly == is_anomaly)
    if search:
        like = f"%{search}%"
        q = q.filter(
            (Member.mp_name.ilike(like))
            | (Member.mp_name_clean.ilike(like))
            | (Constituency.name.ilike(like))
        )
    total = q.count()
    sort_col = {
        "member_id": Member.member_id,
        "mp_name": Member.mp_name,
        "state": State.name,
        "allocated_amount": Entitlement.allocated_amount,
        "risk_score": RiskScore.risk_score,
        "risk_level": RiskScore.risk_level,
    }.get(sort_by, Member.member_id)
    if sort_order == "desc":
        q = q.order_by(sort_col.desc().nullslast())
    else:
        q = q.order_by(sort_col.asc().nullsfirst())
    members = q.offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for m in members:
        ent = m.entitlement
        anom = m.anomaly
        risk = m.risk
        items.append(ProjectListItem(
            member_id=m.member_id,
            sr_no=m.sr_no,
            state=m.state_rel.name,
            mp_name=m.mp_name,
            constituency=m.constituency_rel.name,
            allocated_amount=ent.allocated_amount if ent else None,
            risk_score=risk.risk_score if risk else None,
            risk_level=risk.risk_level if risk else None,
            is_anomaly=anom.is_anomaly if anom else None,
            ensemble_score=anom.ensemble_score if anom else None,
        ))
    return ProjectListResponse(items=items, total=total, page=page, page_size=page_size)


def get_map_points(db: Session, state: Optional[str] = None) -> list[MapPoint]:
    q = (
        db.query(Member)
        .join(State, Member.state_id == State.state_id)
        .join(Constituency, Member.constituency_id == Constituency.constituency_id)
        .outerjoin(Entitlement, Member.member_id == Entitlement.member_id)
        .outerjoin(MemberAnomaly, Member.member_id == MemberAnomaly.member_id)
        .outerjoin(RiskScore, Member.member_id == RiskScore.member_id)
    )
    if state:
        q = q.filter(State.name == state)
    members = q.all()
    points = []
    for m in members:
        ent = m.entitlement
        anom = m.anomaly
        risk = m.risk
        points.append(MapPoint(
            member_id=m.member_id,
            mp_name=m.mp_name,
            state=m.state_rel.name,
            constituency=m.constituency_rel.name,
            allocated_amount=ent.allocated_amount if ent else None,
            risk_score=risk.risk_score if risk else None,
            risk_level=risk.risk_level if risk else None,
            is_anomaly=anom.is_anomaly if anom else None,
        ))
    return points


def get_states(db: Session) -> list[str]:
    rows = db.query(State.name).order_by(State.name).all()
    return [r[0] for r in rows]


def get_risk_distribution(db: Session) -> dict:
    rows = (
        db.query(RiskScore.risk_level, func.count(RiskScore.member_id))
        .group_by(RiskScore.risk_level)
        .all()
    )
    dist = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for level, cnt in rows:
        dist[level] = cnt
    return dist
