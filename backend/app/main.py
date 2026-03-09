"""FastAPI application entrypoint for VoyageMind."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.core.cache import get_cache_manager
from app.models.database import create_tables

settings = get_settings()
logging.basicConfig(
	level=getattr(logging, settings.log_level.upper(), logging.INFO),
	format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
	"""Initialize optional infrastructure without blocking app startup."""
	get_cache_manager()
	try:
		create_tables()
	except Exception as exc:  # pragma: no cover - depends on external infra
		logger.warning("Database initialization skipped: %s", exc)
	yield


app = FastAPI(
	title="VoyageMind Backend",
	description="Agentic travel planning backend powered by Amazon Nova and mock-safe tools.",
	version="0.1.0",
	lifespan=lifespan,
)

app.add_middleware(
	CORSMiddleware,
	allow_origins=settings.cors_origins,
	allow_credentials=True,
	allow_methods=["*"],
	allow_headers=["*"],
)

app.include_router(router)


@app.get("/")
async def root() -> dict[str, str]:
	"""Simple root endpoint for local sanity checks."""
	return {"service": "VoyageMind backend", "status": "ready"}
