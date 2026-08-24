"""Pytest configuration and fixtures."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Ensure project root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

os.environ["DATABASE_URL"] = "sqlite:///./test_mplad.db"
os.environ["JWT_SECRET"] = "test-secret-key-for-testing-only"

from backend.app.models.orm import Base
from backend.app.database.session import get_db
from backend.app.main import app
from backend.app.utils.security import hash_password
from backend.app.models.orm import User


@pytest.fixture(scope="session")
def engine():
    db_path = Path("./test_mplad.db")
    db_path.unlink(missing_ok=True)
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    try:
        db_path.unlink(missing_ok=True)
    except PermissionError:
        pass


@pytest.fixture()
def db(engine):
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionLocal()
    yield session
    session.rollback()
    session.close()


@pytest.fixture()
def client(engine):
    SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture()
def seed_users(db):
    """Create a test admin user."""
    user = db.query(User).filter(User.username == "testadmin").first()
    if not user:
        user = User(
            username="testadmin",
            password_hash=hash_password("testpass123"),
            full_name="Test Admin",
            role="ADMIN",
            active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@pytest.fixture()
def auth_headers(client, seed_users):
    """Get JWT auth headers for the test admin."""
    r = client.post("/auth/login", json={"username": "testadmin", "password": "testpass123"})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
