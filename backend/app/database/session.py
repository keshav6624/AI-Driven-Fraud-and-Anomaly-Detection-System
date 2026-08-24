"""Database engine and session management (SQLAlchemy 2.x)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Allow `python -m backend.app...` and uvicorn module imports from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./data/mplad_dev.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
