"""
SentinelRisk — FastAPI Application Entry Point

Creates and configures the FastAPI application:
  - Registers all API routers
  - Sets up CORS for frontend communication
  - Initializes the database on startup
  - Configures structured logging

Run with:
    cd backend
    uvicorn app.main:app --reload
"""

import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import get_settings
from backend.app.db.database import init_database
from backend.app.api.health import router as health_router
from backend.app.api.dataset import router as dataset_router
from backend.app.api.cases import router as cases_router
from backend.app.api.incidents import router as incidents_router
from backend.app.api.risk import router as risk_router
from backend.app.api.metrics import router as metrics_router
from backend.app.api.dashboard import router as dashboard_router
from backend.app.api.stream import router as stream_router
from backend.app.api.merchants import router as merchants_router
from backend.app.api.placeholders import (
    events_router,
    model_router,
)


def _setup_logging(level: str = "INFO"):
    """Configure application-wide logging."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — runs on startup and shutdown."""
    logger = logging.getLogger("sentinelrisk")
    logger.info("SentinelRisk backend starting...")

    # Initialize database tables
    init_database()
    logger.info("Database initialized.")

    logger.info("SentinelRisk backend ready.")
    yield
    logger.info("SentinelRisk backend shutting down.")


def create_app() -> FastAPI:
    """Application factory — creates and configures the FastAPI app."""
    settings = get_settings()

    _setup_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        description=settings.app_description,
        version=settings.app_version,
        lifespan=lifespan,
    )

    # CORS — allow frontend (Next.js on :3000) to call backend
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://127.0.0.1:3000",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register routers
    app.include_router(health_router, tags=["Health"])
    app.include_router(dataset_router)
    app.include_router(events_router)
    app.include_router(risk_router)
    app.include_router(cases_router)
    app.include_router(metrics_router)
    app.include_router(incidents_router)
    app.include_router(model_router)
    app.include_router(dashboard_router)
    app.include_router(stream_router)
    app.include_router(merchants_router)

    @app.get("/download", summary="Download complete SentinelRisk project archive")
    async def download_bundle():
        from pathlib import Path
        from fastapi.responses import FileResponse, JSONResponse
        bundle = Path("sentinelrisk_project_bundle.zip")
        if not bundle.exists():
            from scripts.create_bundle import create_bundle
            create_bundle()
        return FileResponse(
            path=str(bundle),
            filename="sentinelrisk_project_bundle.zip",
            media_type="application/zip",
        )

    return app


# Module-level app instance for uvicorn
app = create_app()
