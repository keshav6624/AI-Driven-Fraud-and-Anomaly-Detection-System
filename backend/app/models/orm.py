"""SQLAlchemy ORM models mirroring database/migrations/001_init.sql.

JSONB columns use a JSON variant so the same models run on PostgreSQL
(production, via the SQL migration) and SQLite (dev/test, via create_all).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

JsonType = JSONB().with_variant(JSON(), "sqlite")

ROLE_ENUM = Enum("ADMIN", "ANALYST", "INVESTIGATOR", "VIEWER", name="user_role",
                 native_enum=False, create_constraint=True)
RISK_ENUM = Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", name="risk_level_t",
                 native_enum=False, create_constraint=True)
CASE_STATUS_ENUM = Enum("OPEN", "UNDER_REVIEW", "VERIFIED", "DISMISSED", "RESOLVED",
                        name="case_status_t", native_enum=False, create_constraint=True)
CASE_PRIORITY_ENUM = Enum("LOW", "MEDIUM", "HIGH", "URGENT", name="case_priority_t",
                          native_enum=False, create_constraint=True)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class State(Base):
    __tablename__ = "states"
    state_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text, unique=True)

    members_rel = relationship("Member", back_populates="state_rel")


class Constituency(Base):
    __tablename__ = "constituencies"
    constituency_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    base_name: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text, default="general")
    state_id: Mapped[int] = mapped_column(ForeignKey("states.state_id"))
    __table_args__ = (UniqueConstraint("name", "state_id", name="uq_constituency_state"),)


class Member(Base):
    __tablename__ = "members"
    member_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    sr_no: Mapped[int] = mapped_column(Integer, unique=True)
    state_id: Mapped[int] = mapped_column(ForeignKey("states.state_id"), index=True)
    constituency_id: Mapped[int] = mapped_column(
        ForeignKey("constituencies.constituency_id"), index=True
    )
    mp_name_raw: Mapped[str] = mapped_column(Text)
    mp_name: Mapped[str] = mapped_column(Text)
    mp_name_clean: Mapped[str] = mapped_column(Text, index=True)
    member_key: Mapped[str] = mapped_column(Text, unique=True)
    name_quality_score: Mapped[float] = mapped_column(Float)
    has_title_prefix: Mapped[bool] = mapped_column(Boolean, default=False)

    state_rel = relationship("State")
    constituency_rel = relationship("Constituency")
    entitlement = relationship("Entitlement", uselist=False, back_populates="member")
    features = relationship("MpFeature", uselist=False, back_populates="member")
    anomaly = relationship("MemberAnomaly", uselist=False, back_populates="member")
    risk = relationship("RiskScore", uselist=False, back_populates="member")
    explanation = relationship("MemberExplanation", uselist=False, back_populates="member")


class Entitlement(Base):
    __tablename__ = "entitlements"
    entitlement_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.member_id", ondelete="CASCADE"), unique=True
    )
    allocated_amount: Mapped[float | None] = mapped_column(Float, nullable=True, index=True)
    amount_missing: Mapped[bool] = mapped_column(Boolean)
    amount_has_paise: Mapped[bool] = mapped_column(Boolean)
    allocated_amount_raw: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_file: Mapped[str] = mapped_column(Text)
    dataset_version: Mapped[str] = mapped_column(Text)
    loaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    member = relationship("Member", back_populates="entitlement")


class MpFeature(Base):
    __tablename__ = "mp_features"
    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.member_id", ondelete="CASCADE"), primary_key=True
    )
    benchmark_amount: Mapped[float] = mapped_column(Float)
    benchmark_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    deviation_from_benchmark_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    state_deviation_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    state_percentile: Mapped[float | None] = mapped_column(Float, nullable=True)
    national_percentile: Mapped[float | None] = mapped_column(Float, nullable=True)
    paise_component: Mapped[float | None] = mapped_column(Float, nullable=True)
    excess_over_benchmark_cr: Mapped[float | None] = mapped_column(Float, nullable=True)
    shortfall_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    benchmark_verdict: Mapped[str] = mapped_column(Text)
    peer_state_n: Mapped[int] = mapped_column(Integer)
    feature_version: Mapped[str] = mapped_column(Text)

    member = relationship("Member", back_populates="features")


class MemberAnomaly(Base):
    __tablename__ = "member_anomalies"
    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.member_id", ondelete="CASCADE"), primary_key=True
    )
    score_robust_z: Mapped[float] = mapped_column(Float)
    flag_robust_z: Mapped[bool] = mapped_column(Boolean)
    score_isolation_forest: Mapped[float] = mapped_column(Float)
    flag_isolation_forest: Mapped[bool] = mapped_column(Boolean)
    score_lof: Mapped[float] = mapped_column(Float)
    flag_lof: Mapped[bool] = mapped_column(Boolean)
    anomaly_votes: Mapped[int] = mapped_column(Integer)
    ensemble_score: Mapped[float] = mapped_column(Float)
    is_anomaly: Mapped[bool] = mapped_column(Boolean, index=True)
    reasons: Mapped[list] = mapped_column(JsonType, default=list)
    model_version: Mapped[str] = mapped_column(Text)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    member = relationship("Member", back_populates="anomaly")

    __table_args__ = (
        Index("idx_anomalies_ensemble", "ensemble_score"),
    )


class RiskScore(Base):
    __tablename__ = "risk_scores"
    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.member_id", ondelete="CASCADE"), primary_key=True
    )
    risk_score: Mapped[float] = mapped_column(Float)
    risk_level: Mapped[str] = mapped_column(RISK_ENUM)
    financial_risk: Mapped[float] = mapped_column(Float)
    data_quality_risk: Mapped[float] = mapped_column(Float)
    duplicate_risk: Mapped[float] = mapped_column(Float)
    interest_risk: Mapped[float] = mapped_column(Float)
    max_duplicate_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    flagged_duplicate_pair: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_escalated: Mapped[bool] = mapped_column(Boolean, default=False)
    model_version: Mapped[str] = mapped_column(Text)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    member = relationship("Member", back_populates="risk")

    __table_args__ = (
        Index("idx_risk_level_score", "risk_level", "risk_score"),
    )


class MemberExplanation(Base):
    __tablename__ = "member_explanations"
    member_id: Mapped[int] = mapped_column(
        ForeignKey("members.member_id", ondelete="CASCADE"), primary_key=True
    )
    risk_factors: Mapped[list] = mapped_column(JsonType, default=list)
    recommended_actions: Mapped[list] = mapped_column(JsonType, default=list)
    lofo_attribution: Mapped[dict] = mapped_column(JsonType, default=dict)
    model_version: Mapped[str] = mapped_column(Text)

    member = relationship("Member", back_populates="explanation")


class DuplicatePair(Base):
    __tablename__ = "duplicate_pairs"
    pair_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id_a: Mapped[int] = mapped_column(ForeignKey("members.member_id", ondelete="CASCADE"))
    member_id_b: Mapped[int] = mapped_column(ForeignKey("members.member_id", ondelete="CASCADE"))
    name_similarity: Mapped[float] = mapped_column(Float)
    constituency_similarity: Mapped[float] = mapped_column(Float)
    same_state: Mapped[bool] = mapped_column(Boolean)
    overall_similarity: Mapped[float] = mapped_column(Float)
    potential_duplicate: Mapped[bool] = mapped_column(Boolean, index=True)
    reason: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(Text)

    __table_args__ = (
        CheckConstraint("member_id_a < member_id_b", name="ck_pair_order"),
    )


class User(Base):
    __tablename__ = "users"
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(Text, unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    full_name: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(ROLE_ENUM, default="VIEWER")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class InvestigationCase(Base):
    __tablename__ = "investigation_cases"
    case_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    member_id: Mapped[int] = mapped_column(ForeignKey("members.member_id"), index=True)
    title: Mapped[str] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(CASE_STATUS_ENUM, default="OPEN", index=True)
    priority: Mapped[str] = mapped_column(CASE_PRIORITY_ENUM, default="MEDIUM")
    created_by: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    assigned_to: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id"), nullable=True
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow
    )

    notes = relationship(
        "CaseNote", back_populates="case", cascade="all, delete-orphan"
    )


class CaseNote(Base):
    __tablename__ = "case_notes"
    note_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    case_id: Mapped[int] = mapped_column(
        ForeignKey("investigation_cases.case_id", ondelete="CASCADE"), index=True
    )
    author_id: Mapped[int] = mapped_column(ForeignKey("users.user_id"))
    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    case = relationship("InvestigationCase", back_populates="notes")


class ModelRun(Base):
    __tablename__ = "model_runs"
    run_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_type: Mapped[str] = mapped_column(Text)
    model_version: Mapped[str] = mapped_column(Text)
    dataset_version: Mapped[str] = mapped_column(Text)
    feature_version: Mapped[str] = mapped_column(Text)
    metrics: Mapped[dict] = mapped_column(JsonType, default=dict)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    executed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class AssistantQueryLog(Base):
    __tablename__ = "assistant_query_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.user_id"), nullable=True
    )
    question: Mapped[str] = mapped_column(Text)
    intent: Mapped[str] = mapped_column(Text)
    sql_text: Mapped[str] = mapped_column(Text)
    result_count: Mapped[int] = mapped_column(Integer)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
