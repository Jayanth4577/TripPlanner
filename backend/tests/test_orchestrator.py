from datetime import date

import pytest

from app.agents.orchestrator import OrchestratorAgent
from app.models.schemas import TripInput


@pytest.mark.asyncio
async def test_plan_trip_returns_complete_mock_plan():
    orchestrator = OrchestratorAgent()
    request = TripInput(
        destination="Paris",
        start_date=date(2026, 6, 1),
        end_date=date(2026, 6, 4),
        budget_usd=2500,
        travelers_count=2,
    )

    plan = await orchestrator.plan_trip(request)

    assert len(plan.itinerary) == 3
    assert plan.flights_outbound is not None
    assert plan.flights_return is not None
    assert plan.total_cost_breakdown["hotels"] > 0
    assert plan.total_estimated_cost > 0
    assert plan.feasibility_score >= 0


@pytest.mark.asyncio
async def test_stream_trip_plan_emits_plan_event():
    orchestrator = OrchestratorAgent()
    request = TripInput(
        destination="London",
        start_date=date(2026, 7, 10),
        end_date=date(2026, 7, 13),
        budget_usd=2200,
        travelers_count=1,
    )

    event_types = []
    async for event in orchestrator.stream_trip_plan(request):
        event_types.append(event.type)

    assert "step" in event_types
    assert "plan" in event_types