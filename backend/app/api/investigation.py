"""Investigation case routes."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.investigation import (
    InvestigationCaseCreate,
    InvestigationCaseUpdate,
    CaseNoteCreate,
    InvestigationCaseResponse,
    InvestigationCaseListResponse,
    CaseNoteResponse,
)
from backend.app.services import investigation_service
from backend.app.api.deps import InvestigatorOrAbove, CurrentUser

router = APIRouter(prefix="/investigations", tags=["investigations"])


@router.post("", response_model=InvestigationCaseResponse, status_code=201)
def create_case(
    body: InvestigationCaseCreate,
    user: InvestigatorOrAbove,
    db: Annotated[Session, Depends(get_db)],
):
    return investigation_service.create_case(db, body, user.user_id)


@router.get("", response_model=InvestigationCaseListResponse)
def list_cases(
    db: Annotated[Session, Depends(get_db)],
    _user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: Optional[str] = Query(None, alias="status"),
    priority: Optional[str] = None,
    member_id: Optional[int] = None,
):
    return investigation_service.list_cases(
        db, page=page, page_size=page_size,
        status=status_filter, priority=priority, member_id=member_id,
    )


@router.get("/{case_id}", response_model=InvestigationCaseResponse)
def get_case(case_id: int, db: Annotated[Session, Depends(get_db)], _user: CurrentUser):
    case = investigation_service.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


@router.patch("/{case_id}", response_model=InvestigationCaseResponse)
def update_case(
    case_id: int,
    body: InvestigationCaseUpdate,
    user: InvestigatorOrAbove,
    db: Annotated[Session, Depends(get_db)],
):
    case = investigation_service.update_case(db, case_id, body)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return case


@router.post("/{case_id}/notes", response_model=CaseNoteResponse, status_code=201)
def add_note(
    case_id: int,
    body: CaseNoteCreate,
    user: InvestigatorOrAbove,
    db: Annotated[Session, Depends(get_db)],
):
    case = investigation_service.get_case(db, case_id)
    if not case:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found")
    return investigation_service.add_note(db, case_id, body, user.user_id)
