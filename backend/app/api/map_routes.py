"""Map routes — geospatial data for MapLibre."""
from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.member import MapPoint
from backend.app.services import member_service
from backend.app.api.deps import CurrentUser

router = APIRouter(prefix="/map", tags=["map"])


@router.get("/projects", response_model=list[MapPoint])
def map_projects(
    db: Annotated[Session, Depends(get_db)],
    _user: CurrentUser,
    state: Optional[str] = None,
):
    return member_service.get_map_points(db, state=state)


@router.get("/states")
def map_states(db: Annotated[Session, Depends(get_db)], _user: CurrentUser):
    states = member_service.get_states(db)
    return {"states": states}
