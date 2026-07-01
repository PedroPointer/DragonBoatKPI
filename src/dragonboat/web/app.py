"""FastAPI application — Dragon Boat Analyzer web interface."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from dragonboat.config import settings
from dragonboat.database import init_db

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Dragon Boat Analyzer",
    description="Analisis de rendimiento Dragon Boat 200m",
    version="0.1.0",
)

# Mount web static files (base.css, etc.)
web_static = Path(__file__).parent / "static"
web_static.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(web_static)), name="web_static")

# Mount output directory for serving generated charts
output_dir = settings.resolved_output_dir
output_dir.mkdir(parents=True, exist_ok=True)
app.mount("/charts", StaticFiles(directory=str(output_dir)), name="charts")

# Photos directory
photos_dir = settings.resolved_output_dir.parent / "photos"
photos_dir.mkdir(parents=True, exist_ok=True)
app.mount("/photos", StaticFiles(directory=str(photos_dir)), name="photos")


@app.on_event("startup")
def on_startup():
    init_db()
    logger.info("Database initialized")


# Include routes
from dragonboat.web.routes import router  # noqa: E402
from dragonboat.web.deportistas_routes import router as deportistas_router  # noqa: E402

app.include_router(router)
app.include_router(deportistas_router)
