"""Investigation case schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CaseStatus(str):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    DISMISSED = "DISMISSED"
    RESOLVED = "RESOLVED"


class CasePriority(str):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    URGENT = "URGENT"


class InvestigationCaseCreate(BaseModel):
    member_id: int
    title: str = Field(..., min_length=3, max_length=500)
    description: Optional[str] = None
    priority: str = "MEDIUM"


class InvestigationCaseUpdate(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_to: Optional[int] = None
    resolution_notes: Optional[str] = None


class CaseNoteCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=5000)


class CaseNoteResponse(BaseModel):
    note_id: int
    case_id: int
    author_id: int
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class InvestigationCaseResponse(BaseModel):
    case_id: int
    member_id: int
    mp_name: Optional[str] = None
    state: Optional[str] = None
    constituency: Optional[str] = None
    title: str
    description: Optional[str] = None
    status: str
    priority: str
    created_by: int
    assigned_to: Optional[int] = None
    resolution_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    notes: list[CaseNoteResponse] = []

    model_config = {"from_attributes": True}


class InvestigationCaseListResponse(BaseModel):
    items: list[InvestigationCaseResponse]
    total: int
    page: int
    page_size: int
