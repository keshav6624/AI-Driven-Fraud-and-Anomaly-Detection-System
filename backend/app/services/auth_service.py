"""Authentication service — user management and token operations."""
from __future__ import annotations

from sqlalchemy.orm import Session

from backend.app.models.orm import User
from backend.app.schemas.auth import Role
from backend.app.utils.security import hash_password, verify_password, create_token
from backend.app.config import get_settings


def authenticate_user(db: Session, username: str, password: str) -> dict | None:
    user = db.query(User).filter(User.username == username, User.active.is_(True)).first()
    if not user or not verify_password(password, user.password_hash):
        return None
    settings = get_settings()
    token = create_token(
        subject=str(user.user_id),
        role=user.role,
        secret=settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
        expires_minutes=settings.access_token_expire_minutes,
    )
    return {
        "access_token": token,
        "token_type": "bearer",
        "role": user.role,
        "username": user.username,
    }


def create_user(db: Session, username: str, password: str, full_name: str, role: str) -> User:
    existing = db.query(User).filter(User.username == username).first()
    if existing:
        raise ValueError(f"Username '{username}' already exists")
    user = User(
        username=username,
        password_hash=hash_password(password),
        full_name=full_name,
        role=role,
        active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.user_id == user_id).first()


def list_users(db: Session, skip: int = 0, limit: int = 50) -> list[User]:
    return db.query(User).offset(skip).limit(limit).all()
