"""Seed the database from processed CSVs and create the admin user.

Usage:
    cd project_root
    python -m backend.scripts.seed_data
"""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import pandas as pd
from sqlalchemy.orm import Session

from backend.app.database.session import engine, SessionLocal
from backend.app.models.orm import (
    Base, State, Constituency, Member, Entitlement, MpFeature,
    MemberAnomaly, RiskScore, MemberExplanation, DuplicatePair, User,
)
from backend.app.utils.security import hash_password
from backend.app.config import get_settings

DATA_DIR = PROJECT_ROOT / "data" / "processed"


def _load(name: str) -> pd.DataFrame:
    p = DATA_DIR / name
    if not p.exists():
        print(f"  [SKIP] {p} not found")
        return pd.DataFrame()
    return pd.read_csv(p)


def seed(db: Session):
    Base.metadata.create_all(bind=engine)

    # --- States ---
    clean = _load("mp_allocations_clean.csv")
    if clean.empty:
        print("No clean data found. Run the ETL pipeline first.")
        return
    state_names = sorted(clean["state"].dropna().unique())
    state_map: dict[str, int] = {}
    for name in state_names:
        existing = db.query(State).filter(State.name == name).first()
        if existing:
            state_map[name] = existing.state_id
        else:
            s = State(name=name)
            db.add(s)
            db.flush()
            state_map[name] = s.state_id
    print(f"  States: {len(state_map)}")

    # --- Constituencies ---
    const_map: dict[str, int] = {}
    for _, row in clean.drop_duplicates(["constituency", "state"]).iterrows():
        cname = row["constituency"]
        sname = row["state"]
        sid = state_map.get(sname)
        if not sid:
            continue
        key = f"{cname}||{sid}"
        if key in const_map:
            continue
        existing = db.query(Constituency).filter(
            Constituency.name == cname, Constituency.state_id == sid
        ).first()
        if existing:
            const_map[key] = existing.constituency_id
        else:
            c = Constituency(
                name=cname,
                base_name=row.get("constituency_base", cname),
                category=row.get("constituency_category", "general"),
                state_id=sid,
            )
            db.add(c)
            db.flush()
            const_map[key] = c.constituency_id
    print(f"  Constituencies: {len(const_map)}")

    # --- Members + Entitlements ---
    member_count = 0
    for _, row in clean.iterrows():
        sname = row["state"]
        cname = row["constituency"]
        sid = state_map.get(sname)
        cid = const_map.get(f"{cname}||{sid}")
        if not sid or not cid:
            continue
        member_key = row.get("member_key", f"{row['sr_no']}_{sname}_{cname}")
        existing = db.query(Member).filter(Member.member_key == member_key).first()
        if existing:
            mid = existing.member_id
        else:
            m = Member(
                sr_no=int(row["sr_no"]),
                state_id=sid,
                constituency_id=cid,
                mp_name_raw=str(row.get("mp_name_raw", row["mp_name"])),
                mp_name=str(row["mp_name"]),
                mp_name_clean=str(row.get("mp_name_clean", row["mp_name"])),
                member_key=member_key,
                name_quality_score=float(row.get("name_quality_score", 1.0)),
                has_title_prefix=bool(row.get("has_title_prefix", False)),
            )
            db.add(m)
            db.flush()
            mid = m.member_id
        ent_existing = db.query(Entitlement).filter(Entitlement.member_id == mid).first()
        if not ent_existing:
            amt_raw = str(row.get("allocated_amount_raw", ""))
            amt = row.get("allocated_amount")
            e = Entitlement(
                member_id=mid,
                allocated_amount=float(amt) if pd.notna(amt) else None,
                amount_missing=bool(row.get("amount_missing", True)),
                amount_has_paise=bool(row.get("amount_has_paise", False)),
                allocated_amount_raw=amt_raw if amt_raw and amt_raw != "nan" else None,
                source_file="Allocated Limit for Honble MPs.csv",
                dataset_version="raw-2026-08",
            )
            db.add(e)
        member_count += 1
    print(f"  Members + entitlements: {member_count}")

    # --- Features ---
    features = _load("mp_features.csv")
    feat_count = 0
    if not features.empty:
        for _, row in features.iterrows():
            mid = int(row["member_id"])
            existing = db.query(MpFeature).filter(MpFeature.member_id == mid).first()
            if existing:
                continue
            db.add(MpFeature(
                member_id=mid,
                benchmark_amount=float(row.get("benchmark_amount", 0)),
                benchmark_ratio=_safe_float(row, "benchmark_ratio"),
                deviation_from_benchmark_pct=_safe_float(row, "deviation_from_benchmark_pct"),
                state_deviation_pct=_safe_float(row, "state_deviation_pct"),
                state_percentile=_safe_float(row, "state_percentile"),
                national_percentile=_safe_float(row, "national_percentile"),
                paise_component=_safe_float(row, "paise_component"),
                excess_over_benchmark_cr=_safe_float(row, "excess_over_benchmark_cr"),
                shortfall_ratio=_safe_float(row, "shortfall_ratio"),
                benchmark_verdict=str(row.get("benchmark_verdict", "")),
                peer_state_n=int(row.get("peer_state_n", 0)),
                feature_version="v1",
            ))
            feat_count += 1
    print(f"  Features: {feat_count}")

    # --- Anomalies ---
    anomalies = _load("mp_anomalies.csv")
    anom_count = 0
    if not anomalies.empty:
        for _, row in anomalies.iterrows():
            mid = int(row["member_id"])
            existing = db.query(MemberAnomaly).filter(MemberAnomaly.member_id == mid).first()
            if existing:
                continue
            reasons_raw = row.get("anomaly_reasons", "")
            if pd.isna(reasons_raw) or reasons_raw == "":
                reasons = []
            else:
                reasons = [s.strip() for s in str(reasons_raw).split(";") if s.strip()]
            db.add(MemberAnomaly(
                member_id=mid,
                score_robust_z=float(row.get("score_robust_z", 0)),
                flag_robust_z=bool(row.get("flag_robust_z", False)),
                score_isolation_forest=float(row.get("score_isolation_forest", 0)),
                flag_isolation_forest=bool(row.get("flag_isolation_forest", False)),
                score_lof=float(row.get("score_lof", 0)),
                flag_lof=bool(row.get("flag_lof", False)),
                anomaly_votes=int(row.get("anomaly_votes", 0)),
                ensemble_score=float(row.get("ensemble_score", 0)),
                is_anomaly=bool(row.get("is_anomaly", False)),
                reasons=reasons,
                model_version="v1",
            ))
            anom_count += 1
    print(f"  Anomalies: {anom_count}")

    # --- Risk Scores ---
    risk_df = _load("mp_risk_scores.csv")
    risk_count = 0
    if not risk_df.empty:
        for _, row in risk_df.iterrows():
            mid = int(row["member_id"])
            existing = db.query(RiskScore).filter(RiskScore.member_id == mid).first()
            if existing:
                continue
            db.add(RiskScore(
                member_id=mid,
                risk_score=float(row.get("risk_score", 0)),
                risk_level=str(row.get("risk_level", "LOW")),
                financial_risk=float(row.get("financial_risk", 0)),
                data_quality_risk=float(row.get("data_quality_risk", 0)),
                duplicate_risk=float(row.get("duplicate_risk", 0)),
                interest_risk=float(row.get("interest_risk", 0)),
                max_duplicate_similarity=_safe_float(row, "max_duplicate_similarity"),
                flagged_duplicate_pair=bool(row.get("flagged_duplicate_pair", False)),
                risk_escalated=bool(row.get("risk_escalated", False)),
                model_version="v1",
            ))
            risk_count += 1
    print(f"  Risk scores: {risk_count}")

    # --- Explanations ---
    expl = _load("mp_explanations.csv")
    expl_count = 0
    if not expl.empty:
        for _, row in expl.iterrows():
            mid = int(row["member_id"])
            existing = db.query(MemberExplanation).filter(MemberExplanation.member_id == mid).first()
            if existing:
                continue
            reasons_raw = row.get("anomaly_reasons", "")
            if pd.isna(reasons_raw) or reasons_raw == "":
                reasons = []
            else:
                reasons = [s.strip() for s in str(reasons_raw).split(";") if s.strip()]
            db.add(MemberExplanation(
                member_id=mid,
                risk_factors=reasons,
                recommended_actions=[],
                lofo_attribution={},
                model_version="v1",
            ))
            expl_count += 1
    print(f"  Explanations: {expl_count}")

    # --- Duplicate Pairs ---
    dups = _load("duplicate_pairs.csv")
    dup_count = 0
    if not dups.empty:
        for _, row in dups.iterrows():
            mid_a = int(row["member_id_a"])
            mid_b = int(row["member_id_b"])
            existing = db.query(DuplicatePair).filter(
                DuplicatePair.member_id_a == mid_a, DuplicatePair.member_id_b == mid_b
            ).first()
            if existing:
                continue
            db.add(DuplicatePair(
                member_id_a=mid_a,
                member_id_b=mid_b,
                name_similarity=float(row.get("name_similarity", 0)),
                constituency_similarity=float(row.get("constituency_similarity", 0)),
                same_state=bool(row.get("same_state", False)),
                overall_similarity=float(row.get("overall_similarity", 0)),
                potential_duplicate=bool(row.get("potential_duplicate", False)),
                reason=str(row.get("duplicate_reason", "")),
                model_version="v1",
            ))
            dup_count += 1
    print(f"  Duplicate pairs: {dup_count}")

    # --- Admin User ---
    settings = get_settings()
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        db.add(User(
            username="admin",
            password_hash=hash_password(settings.seed_admin_password),
            full_name="Platform Administrator",
            role="ADMIN",
            active=True,
        ))
        print("  Admin user created (username: admin)")

    db.commit()
    print("Database seed complete.")


def _safe_float(row, col):
    v = row.get(col)
    if pd.isna(v):
        return None
    return float(v)


if __name__ == "__main__":
    print("Seeding database...")
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
