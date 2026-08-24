"""FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.database.session import engine
from backend.app.models.orm import Base
from backend.app.api import auth, projects, analytics, map_routes, investigation, ml_routes


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="MPLAD-Sentinel",
    description="AI/ML platform for detecting anomalies and irregularities in MPLADS data",
    version="1.0.0",
    lifespan=lifespan,
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(projects.router)
app.include_router(analytics.router)
app.include_router(map_routes.router)
app.include_router(investigation.router)
app.include_router(ml_routes.router)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "mplad-sentinel"}


@app.get("/api/v1/health")
def api_health():
    return {"status": "ok", "version": "1.0.0"}
