"""Project (Member allocation) routes."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.member import ProjectDetail, ProjectListResponse, MapPoint
from backend.app.services import member_service
from backend.app.api.deps import CurrentUser

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=ProjectListResponse)
def list_projects(
    db: Annotated[Session, Depends(get_db)],
    _user: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    state: Optional[str] = None,
    risk_level: Optional[str] = None,
    is_anomaly: Optional[bool] = None,
    search: Optional[str] = None,
    sort_by: str = "member_id",
    sort_order: str = "asc",
):
    return member_service.list_projects(
        db, page=page, page_size=page_size, state=state,
        risk_level=risk_level, is_anomaly=is_anomaly, search=search,
        sort_by=sort_by, sort_order=sort_order,
    )


@router.get("/{member_id}", response_model=ProjectDetail)
def get_project(member_id: int, db: Annotated[Session, Depends(get_db)], _user: CurrentUser):
    proj = member_service.get_project(db, member_id)
    if not proj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")
    return proj


@router.get("/map/points", response_model=list[MapPoint])
def map_points(
    db: Annotated[Session, Depends(get_db)],
    _user: CurrentUser,
    state: Optional[str] = None,
):
    return member_service.get_map_points(db, state=state)


@router.get("/meta/states", response_model=list[str])
def list_states(db: Annotated[Session, Depends(get_db)], _user: CurrentUser):
    return member_service.get_states(db)
