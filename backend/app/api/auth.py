"""Authentication routes."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.database.session import get_db
from backend.app.schemas.auth import LoginRequest, TokenResponse, UserCreate, UserResponse
from backend.app.services import auth_service
from backend.app.api.deps import AdminUser

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Annotated[Session, Depends(get_db)]):
    result = auth_service.authenticate_user(db, body.username, body.password)
    if not result:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return TokenResponse(**result)


@router.post("/users", response_model=UserResponse, status_code=201)
def create_user(body: UserCreate, _admin: AdminUser, db: Annotated[Session, Depends(get_db)]):
    try:
        user = auth_service.create_user(db, body.username, body.password, body.full_name, body.role.value)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return UserResponse.model_validate(user)


@router.get("/users", response_model=list[UserResponse])
def list_users(_admin: AdminUser, db: Annotated[Session, Depends(get_db)]):
    users = auth_service.list_users(db)
    return [UserResponse.model_validate(u) for u in users]
