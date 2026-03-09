"""API routes for trip planning and health checks."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from sse_starlette.sse import EventSourceResponse

from app.api.dependencies import get_orchestrator, get_settings_dependency
from app.agents.orchestrator import OrchestratorAgent
from app.config import Settings
from app.core.cache import get_cache_manager
from app.models.schemas import TravelPlanResponse, TripInput

router = APIRouter(prefix="/api", tags=["voyagemind"])


@router.get("/health")
async def healthcheck(settings: Settings = Depends(get_settings_dependency)) -> dict[str, object]:
	"""Expose a lightweight healthcheck for the backend."""
	cache = get_cache_manager()
	return {
		"status": "ok",
		"mock_mode": settings.mock_mode,
		"cache": cache.get_stats(),
	}


@router.post("/trips/plan", response_model=TravelPlanResponse)
async def plan_trip(
	trip_input: TripInput,
	orchestrator: OrchestratorAgent = Depends(get_orchestrator),
) -> TravelPlanResponse:
	"""Generate a complete trip plan."""
	return await orchestrator.plan_trip(trip_input)


@router.post("/trips/plan/stream")
async def stream_trip_plan(
	trip_input: TripInput,
	orchestrator: OrchestratorAgent = Depends(get_orchestrator),
) -> EventSourceResponse:
	"""Stream trip planning progress via server-sent events."""

	async def event_generator():
		async for event in orchestrator.stream_trip_plan(trip_input):
			yield {
				"event": event.type,
				"data": json.dumps(jsonable_encoder(event)),
			}

	return EventSourceResponse(event_generator())
