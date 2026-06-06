"""Main FastAPI application."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.models import Base
from app.core.database import engine, init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — init DB and create dirs on startup."""
    # Create data directories
    settings.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    settings.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Initialize database
    await init_db()

    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
from app.api import upload, projects, chapters, export, demo

app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(projects.router, prefix="/api", tags=["Projects"])
app.include_router(chapters.router, prefix="/api", tags=["Chapters"])
app.include_router(export.router, prefix="/api", tags=["Export"])
app.include_router(demo.router, prefix="/api", tags=["Demo"])


@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": settings.APP_VERSION}
