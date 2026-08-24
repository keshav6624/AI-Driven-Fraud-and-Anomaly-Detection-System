"""ML-powered API routes — the AI-driven endpoints."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.api.deps import CurrentUser
from backend.app.ml.loader import ml_loader
from backend.app.ml.inference import score_single_member, batch_inference, InferenceResult
from backend.app.ml.assistant import query as nl_query, AssistantResponse
from backend.app.models.orm import Member, State, Constituency, Entitlement
import pandas as pd

router = APIRouter(prefix="/ml", tags=["ml"])


# --- Request/Response schemas ---

class ScoreSingleRequest(BaseModel):
    mp_name: str = Field(..., min_length=2, max_length=200)
    state: str = Field(..., min_length=2, max_length=100)
    constituency: str = Field(..., min_length=2, max_length=200)
    allocated_amount: Optional[float] = Field(None, ge=0)


class InferenceResultResponse(BaseModel):
    member_id: int
    mp_name: str
    state: str
    constituency: str
    allocated_amount: Optional[float]
    ensemble_score: float
    is_anomaly: bool
    anomaly_votes: int
    anomaly_reasons: list[str]
    individual_scores: dict[str, float]
    risk_score: float
    risk_level: str
    risk_components: dict[str, float]
    risk_escalated: bool
    risk_factors: list[dict]
    recommended_actions: list[str]
    lofo_attribution: dict[str, float]
    duplicate_pairs: list[dict]


class BatchInferenceResponse(BaseModel):
    results: list[InferenceResultResponse]
    summary: dict
    model_version: str


class NLQueryRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=500)


class NLQueryResponse(BaseModel):
    answer: str
    sql: str
    intent: str
    result_count: int
    data: Optional[list[dict]] = None
    visualization_hint: Optional[str] = None


class RetrainResponse(BaseModel):
    status: str
    members_processed: int
    anomalies_detected: int
    model_version: str


# --- Endpoints ---

def _load_existing_data() -> pd.DataFrame:
    """Load the existing MP data from DB for context in live scoring."""
    from backend.app.database.session import SessionLocal
    db = SessionLocal()
    try:
        rows = (
            db.query(
                Member.member_id, Member.sr_no, Member.mp_name, Member.mp_name_clean,
                State.name.label("state"), Constituency.name.label("constituency"),
                Constituency.base_name.label("constituency_base"),
                Constituency.category.label("constituency_category"),
                Entitlement.allocated_amount, Entitlement.amount_missing,
                Entitlement.amount_has_paise, Member.has_title_prefix,
            )
            .join(State, Member.state_id == State.state_id)
            .join(Constituency, Member.constituency_id == Constituency.constituency_id)
            .outerjoin(Entitlement, Member.member_id == Entitlement.member_id)
            .all()
        )
        if not rows:
            return pd.DataFrame()
        data = pd.DataFrame([{
            "member_id": r.member_id,
            "sr_no": r.sr_no,
            "mp_name": r.mp_name,
            "mp_name_clean": r.mp_name_clean,
            "state": r.state,
            "constituency": r.constituency,
            "constituency_base": r.constituency_base,
            "constituency_category": r.constituency_category,
            "allocated_amount": r.allocated_amount,
            "amount_missing": r.amount_missing,
            "amount_has_paise": r.amount_has_paise,
            "has_title_prefix": r.has_title_prefix,
            "name_case_consistent": True,
            "name_has_double_space": False,
        } for r in rows])
        return data
    finally:
        db.close()


@router.post("/score", response_model=InferenceResultResponse)
def score_member(body: ScoreSingleRequest, _user: CurrentUser):
    """AI-driven: Score a single MP allocation in real-time.

    Runs the full ML pipeline (feature engineering → anomaly detection →
    risk scoring → explainability) against the existing dataset context.
    """
    try:
        existing = _load_existing_data()
        result = score_single_member(
            mp_name=body.mp_name,
            state=body.state.upper(),
            constituency=body.constituency,
            allocated_amount=body.allocated_amount,
            existing_batch=existing if not existing.empty else None,
        )
        return InferenceResultResponse(
            member_id=result.member_id,
            mp_name=result.mp_name,
            state=result.state,
            constituency=result.constituency,
            allocated_amount=result.allocated_amount,
            ensemble_score=result.ensemble_score,
            is_anomaly=result.is_anomaly,
            anomaly_votes=result.anomaly_votes,
            anomaly_reasons=result.anomaly_reasons,
            individual_scores=result.individual_scores,
            risk_score=result.risk_score,
            risk_level=result.risk_level,
            risk_components=result.risk_components,
            risk_escalated=result.risk_escalated,
            risk_factors=result.risk_factors,
            recommended_actions=result.recommended_actions,
            lofo_attribution=result.lofo_attribution,
            duplicate_pairs=result.duplicate_pairs,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scoring failed: {str(e)}")


@router.post("/batch", response_model=BatchInferenceResponse)
def run_batch_inference(_user: CurrentUser):
    """AI-driven: Re-run the full ML pipeline on all data.

    Produces fresh anomaly detection, risk scoring, and explainability
    results from the current dataset.
    """
    try:
        existing = _load_existing_data()
        if existing.empty:
            raise HTTPException(status_code=404, detail="No data in database")
        result = batch_inference(existing)
        return BatchInferenceResponse(
            results=[
                InferenceResultResponse(
                    member_id=r.member_id, mp_name=r.mp_name, state=r.state,
                    constituency=r.constituency, allocated_amount=r.allocated_amount,
                    ensemble_score=r.ensemble_score, is_anomaly=r.is_anomaly,
                    anomaly_votes=r.anomaly_votes, anomaly_reasons=r.anomaly_reasons,
                    individual_scores=r.individual_scores, risk_score=r.risk_score,
                    risk_level=r.risk_level, risk_components=r.risk_components,
                    risk_escalated=r.risk_escalated, risk_factors=r.risk_factors,
                    recommended_actions=r.recommended_actions,
                    lofo_attribution=r.lofo_attribution, duplicate_pairs=r.duplicate_pairs,
                )
                for r in result.results
            ],
            summary=result.summary,
            model_version=result.model_version,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Batch inference failed: {str(e)}")


@router.post("/ask", response_model=NLQueryResponse)
def nl_assistant(body: NLQueryRequest, user: CurrentUser, db: Annotated[Session, Depends(get_db)]):
    """AI-driven: Ask natural language questions about MPLADS data.

    The assistant interprets your question, generates SQL, executes it,
    and returns a human-readable answer with the underlying query.
    """
    result = nl_query(db, body.question, user.user_id)
    return NLQueryResponse(
        answer=result.answer,
        sql=result.sql,
        intent=result.intent,
        result_count=result.result_count,
        data=result.data,
        visualization_hint=result.visualization_hint,
    )


@router.post("/retrain", response_model=RetrainResponse)
def retrain_models(_user: CurrentUser):
    """AI-driven: Re-train all ML models with current data.

    Runs the full pipeline and updates the processed CSVs.
    """
    try:
        existing = _load_existing_data()
        if existing.empty:
            raise HTTPException(status_code=404, detail="No data in database")
        result = batch_inference(existing)
        ml_loader.reload()
        return RetrainResponse(
            status="completed",
            members_processed=len(result.results),
            anomalies_detected=result.summary["anomalies_detected"],
            model_version=result.model_version,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Retraining failed: {str(e)}")
