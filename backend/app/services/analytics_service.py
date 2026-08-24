"""Analytics service — dashboard and aggregation queries.

Uses Python-side median/mode computation for SQLite compatibility.
"""
from __future__ import annotations

import statistics
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from backend.app.models.orm import (
    Member,
    Entitlement,
    MpFeature,
    MemberAnomaly,
    RiskScore,
    State,
    Constituency,
)
from backend.app.schemas.analytics import (
    AnalyticsOverview,
    StateAggregation,
    AnomalyScatter,
    AnomalyDistribution,
    DuplicateSummary,
)


def _risk_dist(db: Session) -> dict:
    rows = (
        db.query(RiskScore.risk_level, func.count(RiskScore.member_id))
        .group_by(RiskScore.risk_level)
        .all()
    )
    d = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
    for level, cnt in rows:
        d[level] = cnt
    return d


def _safe_median(values: list) -> float:
    clean = [v for v in values if v is not None]
    if not clean:
        return 0.0
    return float(statistics.median(clean))


def _safe_mode(values: list) -> float:
    clean = [v for v in values if v is not None]
    if not clean:
        return 0.0
    return float(statistics.mode(clean))


def get_overview(db: Session) -> AnalyticsOverview:
    total = db.query(func.count(Member.member_id)).scalar() or 0
    total_alloc = db.query(func.coalesce(func.sum(Entitlement.allocated_amount), 0.0)).scalar()
    mean_alloc = db.query(func.coalesce(func.avg(Entitlement.allocated_amount), 0.0)).scalar()

    all_amounts = [r[0] for r in db.query(Entitlement.allocated_amount).all()]
    median_alloc = _safe_median(all_amounts)
    benchmark = _safe_mode(all_amounts)

    anomaly_count = (
        db.query(func.count(MemberAnomaly.member_id))
        .filter(MemberAnomaly.is_anomaly.is_(True))
        .scalar() or 0
    )
    risk_dist = _risk_dist(db)

    # Per-state aggregation
    state_members = (
        db.query(State.name, Member.member_id)
        .join(Member, State.state_id == Member.state_id)
        .all()
    )
    state_member_map: dict[str, list[int]] = {}
    for sname, mid in state_members:
        state_member_map.setdefault(sname, []).append(mid)

    state_summary = []
    for sname, mids in sorted(state_member_map.items()):
        cnt = len(mids)
        amounts = []
        anomaly_cnt = 0
        risk_scores_list = []
        for mid in mids:
            amt = (
                db.query(Entitlement.allocated_amount)
                .filter(Entitlement.member_id == mid)
                .scalar()
            )
            if amt is not None:
                amounts.append(float(amt))
            is_anom = (
                db.query(MemberAnomaly.is_anomaly)
                .filter(MemberAnomaly.member_id == mid)
                .scalar()
            )
            if is_anom:
                anomaly_cnt += 1
            rs = (
                db.query(RiskScore.risk_score)
                .filter(RiskScore.member_id == mid)
                .scalar()
            )
            if rs is not None:
                risk_scores_list.append(float(rs))

        state_risk = (
            db.query(RiskScore.risk_level, func.count(RiskScore.member_id))
            .join(Member, RiskScore.member_id == Member.member_id)
            .join(State, Member.state_id == State.state_id)
            .filter(State.name == sname)
            .group_by(RiskScore.risk_level)
            .all()
        )
        rd = {"LOW": 0, "MEDIUM": 0, "HIGH": 0, "CRITICAL": 0}
        for lvl, c in state_risk:
            rd[lvl] = c

        state_summary.append(StateAggregation(
            state=sname,
            total_members=cnt,
            total_allocated=sum(amounts),
            mean_allocated=round(sum(amounts) / cnt, 2) if cnt else 0.0,
            median_allocated=round(_safe_median(amounts), 2),
            anomaly_count=anomaly_cnt,
            mean_risk_score=round(statistics.mean(risk_scores_list), 1) if risk_scores_list else 0.0,
            risk_distribution=rd,
        ))

    top_risk = sorted(state_summary, key=lambda s: s.anomaly_count, reverse=True)[:10]
    return AnalyticsOverview(
        total_members=total,
        total_allocated=float(total_alloc),
        mean_allocated=round(float(mean_alloc), 2),
        median_allocated=round(median_alloc, 2),
        benchmark_amount=benchmark,
        anomaly_count=anomaly_count,
        anomaly_rate=round(anomaly_count / total * 100, 2) if total else 0.0,
        risk_distribution=risk_dist,
        top_risk_states=top_risk,
        state_summary=state_summary,
    )


def get_anomaly_scatter(db: Session) -> list[AnomalyScatter]:
    rows = (
        db.query(
            Member.member_id, Member.mp_name, State.name,
            MemberAnomaly.ensemble_score, Entitlement.allocated_amount,
            RiskScore.risk_score, MemberAnomaly.is_anomaly, RiskScore.risk_level,
        )
        .join(State, Member.state_id == State.state_id)
        .outerjoin(MemberAnomaly, Member.member_id == MemberAnomaly.member_id)
        .outerjoin(Entitlement, Member.member_id == Entitlement.member_id)
        .outerjoin(RiskScore, Member.member_id == RiskScore.member_id)
        .all()
    )
    return [
        AnomalyScatter(
            member_id=r[0], mp_name=r[1], state=r[2],
            ensemble_score=r[3], allocated_amount=r[4],
            risk_score=r[5], is_anomaly=r[6], risk_level=r[7],
        )
        for r in rows
    ]


def get_anomaly_distribution(db: Session) -> AnomalyDistribution:
    scores = db.query(MemberAnomaly.ensemble_score).all()
    vals = sorted([float(s[0]) for s in scores if s[0] is not None])
    if not vals:
        return AnomalyDistribution(bins=[], counts=[])
    step = 0.1
    bins = [round(i * step, 2) for i in range(0, int(1.0 / step) + 1)]
    counts = [0] * len(bins)
    for v in vals:
        idx = min(int(v / step), len(bins) - 1)
        counts[idx] += 1
    return AnomalyDistribution(bins=bins, counts=counts)


def get_duplicate_summary(db: Session) -> DuplicateSummary:
    from backend.app.models.orm import DuplicatePair
    total = db.query(func.count(DuplicatePair.pair_id)).scalar() or 0
    flagged = (
        db.query(func.count(DuplicatePair.pair_id))
        .filter(DuplicatePair.potential_duplicate.is_(True))
        .scalar() or 0
    )
    max_sim = db.query(func.coalesce(func.max(DuplicatePair.overall_similarity), 0.0)).scalar()
    mean_sim = db.query(func.coalesce(func.avg(DuplicatePair.overall_similarity), 0.0)).scalar()
    return DuplicateSummary(
        total_pairs=total,
        flagged_pairs=flagged,
        flagged_rate=round(flagged / total * 100, 2) if total else 0.0,
        max_similarity=round(float(max_sim), 4),
        mean_similarity=round(float(mean_sim), 4),
    )
