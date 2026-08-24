"""FastAPI security dependencies — JWT auth and RBAC."""
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.database.session import get_db
from backend.app.models.orm import User
from backend.app.utils.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def _extract_payload(credentials: HTTPAuthorizationCredentials | None) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    settings = get_settings()
    try:
        return decode_token(credentials.credentials, settings.jwt_secret, settings.jwt_algorithm)
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token")


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    payload = _extract_payload(credentials)
    user_id = int(payload.get("sub", 0))
    user = db.query(User).filter(User.user_id == user_id, User.active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_role(*allowed_roles: str):
    def checker(user: Annotated[User, Depends(get_current_user)]) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient permissions")
        return user
    return checker


CurrentUser = Annotated[User, Depends(get_current_user)]
AdminUser = Annotated[User, Depends(require_role("ADMIN"))]
AnalystOrAbove = Annotated[User, Depends(require_role("ADMIN", "ANALYST"))]
InvestigatorOrAbove = Annotated[User, Depends(require_role("ADMIN", "ANALYST", "INVESTIGATOR"))]
