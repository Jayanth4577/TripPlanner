"""Trip orchestration for VoyageMind's backend API."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta
from typing import Any, AsyncGenerator
from uuid import uuid4

from app.core.bedrock_client import BedrockClient, get_bedrock_client
from app.models.schemas import (
	ActivityType,
	AgentStep,
	Attraction,
	DailyItinerary,
	FlightOption,
	FlightSegment,
	HotelOption,
	RiskLevel,
	StreamingResponse,
	TravelPlanResponse,
	TripInput,
	WeatherForecast,
)
from app.tools.flights import FlightsTool
from app.tools.hotels import HotelsTool
from app.tools.maps import MapsTool
from app.tools.weather import WeatherTool


class OrchestratorAgent:
	"""Builds a complete trip plan using the available tool layer."""

	def __init__(self, bedrock_client: BedrockClient | None = None):
		self.bedrock_client = bedrock_client or get_bedrock_client()
		self.flights_tool = FlightsTool()
		self.hotels_tool = HotelsTool()
		self.maps_tool = MapsTool()
		self.weather_tool = WeatherTool()

	async def plan_trip(self, trip_input: TripInput) -> TravelPlanResponse:
		trip_days = self._trip_days(trip_input)
		budget = self._budget_allocation(trip_input, len(trip_days))

		outbound_flights, return_flights, hotels_raw, weather_raw, attractions_raw = await asyncio.gather(
			self.flights_tool.search(
				destination=trip_input.destination,
				departure_date=trip_input.start_date.isoformat(),
				passengers=trip_input.travelers_count,
				max_price=budget["flight_per_person_cap"],
			),
			self.flights_tool.search(
				destination=trip_input.destination,
				departure_date=trip_input.end_date.isoformat(),
				passengers=trip_input.travelers_count,
				max_price=budget["flight_per_person_cap"],
			),
			self.hotels_tool.search(
				destination=trip_input.destination,
				check_in=trip_input.start_date.isoformat(),
				check_out=trip_input.end_date.isoformat(),
				guests=trip_input.travelers_count,
				max_price=budget["hotel_nightly_cap"],
			),
			self.weather_tool.get_forecast(
				location=trip_input.destination,
				start_date=trip_input.start_date,
				end_date=trip_input.end_date,
			),
			self.maps_tool.get_nearby_attractions(destination=trip_input.destination),
		)

		weather = [WeatherForecast(**item) for item in weather_raw]
		selected_hotel = self._select_hotel(hotels_raw, trip_input)
		itinerary = self._build_itinerary(trip_input, trip_days, weather, attractions_raw, selected_hotel)
		outbound = self._build_flight_option(outbound_flights[0]) if outbound_flights else None
		inbound = self._build_flight_option(return_flights[0]) if return_flights else None

		total_cost_breakdown = self._build_cost_breakdown(
			trip_input=trip_input,
			trip_days=trip_days,
			hotel=selected_hotel,
			outbound=outbound,
			inbound=inbound,
			itinerary=itinerary,
		)
		total_estimated_cost = round(sum(total_cost_breakdown.values()), 2)
		risk_warnings = self._build_risk_warnings(weather, total_estimated_cost, trip_input.budget_usd)
		contingency_plans = self._build_contingencies(risk_warnings, selected_hotel)

		return TravelPlanResponse(
			id=str(uuid4()),
			trip_input=trip_input,
			itinerary=itinerary,
			flights_outbound=outbound,
			flights_return=inbound,
			total_cost_breakdown=total_cost_breakdown,
			total_estimated_cost=total_estimated_cost,
			budget_remaining=round(trip_input.budget_usd - total_estimated_cost, 2),
			feasibility_score=self._calculate_feasibility(
				trip_input=trip_input,
				weather=weather,
				total_estimated_cost=total_estimated_cost,
				has_flights=outbound is not None and inbound is not None,
				has_hotel=selected_hotel is not None,
			),
			risk_warnings=risk_warnings,
			contingency_plans=contingency_plans,
		)

	async def stream_trip_plan(self, trip_input: TripInput) -> AsyncGenerator[StreamingResponse, None]:
		yield self._stream_event(
			event_type="step",
			step=AgentStep(
				step_number=1,
				action="validate_input",
				reasoning="Validated trip dates, traveler count, and budget constraints.",
			),
		)

		yield self._stream_event(
			event_type="update",
			payload={"message": "Fetching hotels, flights, weather, and attractions."},
		)

		plan = await self.plan_trip(trip_input)

		yield self._stream_event(
			event_type="step",
			step=AgentStep(
				step_number=2,
				action="synthesize_plan",
				reasoning="Combined tool responses into a budget-aware itinerary and contingency set.",
				tool_output={
					"itinerary_days": len(plan.itinerary),
					"total_estimated_cost": plan.total_estimated_cost,
					"risk_count": len(plan.risk_warnings),
				},
			),
		)
		yield StreamingResponse(type="plan", data={"plan": plan.model_dump(mode="json")})

	def _trip_days(self, trip_input: TripInput) -> list[date]:
		total_days = (trip_input.end_date - trip_input.start_date).days
		return [trip_input.start_date + timedelta(days=offset) for offset in range(total_days)]

	def _budget_allocation(self, trip_input: TripInput, total_days: int) -> dict[str, float]:
		safe_days = max(total_days, 1)
		return {
			"flight_per_person_cap": round((trip_input.budget_usd * 0.35) / trip_input.travelers_count, 2),
			"hotel_nightly_cap": round((trip_input.budget_usd * 0.4) / safe_days, 2),
			"daily_activity_cap": round((trip_input.budget_usd * 0.18) / safe_days, 2),
			"daily_transport_cap": round((trip_input.budget_usd * 0.07) / safe_days, 2),
		}

	def _select_hotel(self, hotels_raw: list[dict[str, Any]], trip_input: TripInput) -> HotelOption | None:
		if not hotels_raw:
			return None

		ranked = sorted(
			hotels_raw,
			key=lambda hotel: (
				abs(hotel.get("price_per_night", 0) - (trip_input.budget_usd * 0.4) / max((trip_input.end_date - trip_input.start_date).days, 1)),
				-hotel.get("rating", 0),
			),
		)
		selected = ranked[0]
		return HotelOption(
			id=selected.get("id", f"hotel-{uuid4().hex[:8]}"),
			name=selected.get("name", "Recommended stay"),
			location=selected.get("location", selected.get("city", trip_input.destination)),
			price_per_night=selected.get("price_per_night", 0),
			rating=selected.get("rating"),
			amenities=selected.get("amenities", []),
			distance_to_center_km=selected.get("distance_to_center_km"),
			image_url=selected.get("image_url"),
			booking_url=selected.get("booking_url"),
			latitude=selected.get("latitude"),
			longitude=selected.get("longitude"),
			reason="Best balance of nightly cost and rating.",
		)

	def _build_flight_option(self, payload: dict[str, Any]) -> FlightOption:
		return FlightOption(
			segments=[FlightSegment(**segment) for segment in payload.get("segments", [])],
			total_price_per_person=payload.get("total_price_per_person", 0),
			total_duration_minutes=payload.get("total_duration_minutes", 0),
			stops=payload.get("stops", 0),
			is_direct=payload.get("is_direct", False),
		)

	def _build_itinerary(
		self,
		trip_input: TripInput,
		trip_days: list[date],
		weather: list[WeatherForecast],
		attractions_raw: list[dict[str, Any]],
		hotel: HotelOption | None,
	) -> list[DailyItinerary]:
		itinerary: list[DailyItinerary] = []
		weather_by_day = {forecast.date: forecast for forecast in weather}
		attractions = [self._build_attraction(raw, trip_input.destination, index) for index, raw in enumerate(attractions_raw)]

		if not attractions:
			attractions = [self._fallback_attraction(trip_input.destination, ActivityType.CULTURE, 0)]

		indoor_pool = [attr for attr in attractions if attr.category in {ActivityType.INDOOR, ActivityType.CULTURE, ActivityType.FOOD}]
		outdoor_pool = [attr for attr in attractions if attr.category not in {ActivityType.INDOOR}]

		for index, trip_day in enumerate(trip_days):
			forecast = weather_by_day.get(trip_day)
			if forecast and forecast.risk_level == RiskLevel.HIGH:
				preferred_pool = indoor_pool or attractions
			else:
				preferred_pool = outdoor_pool or attractions
			morning = preferred_pool[index % len(preferred_pool)]
			afternoon = attractions[(index + 1) % len(attractions)]
			evening = self._fallback_attraction(trip_input.destination, ActivityType.FOOD, index)
			daily_cost = round((hotel.price_per_night if hotel else 0) + 25 + (8 * trip_input.travelers_count), 2)

			itinerary.append(
				DailyItinerary(
					date=trip_day,
					morning_activity=morning,
					afternoon_activity=afternoon,
					evening_activity=evening,
					hotel=hotel,
					estimated_cost_usd=daily_cost,
					notes=forecast.recommendation if forecast else None,
				)
			)

		return itinerary

	def _build_cost_breakdown(
		self,
		trip_input: TripInput,
		trip_days: list[date],
		hotel: HotelOption | None,
		outbound: FlightOption | None,
		inbound: FlightOption | None,
		itinerary: list[DailyItinerary],
	) -> dict[str, float]:
		hotel_total = round((hotel.price_per_night if hotel else 0) * len(trip_days), 2)
		outbound_total = round((outbound.total_price_per_person if outbound else 0) * trip_input.travelers_count, 2)
		inbound_total = round((inbound.total_price_per_person if inbound else 0) * trip_input.travelers_count, 2)
		activities_total = round(sum(item.estimated_cost_usd for item in itinerary) - hotel_total, 2)
		local_transport = round(12 * len(trip_days) * trip_input.travelers_count, 2)

		return {
			"flights": round(outbound_total + inbound_total, 2),
			"hotels": hotel_total,
			"activities": max(activities_total, 0),
			"local_transport": local_transport,
		}

	def _build_risk_warnings(
		self,
		weather: list[WeatherForecast],
		total_estimated_cost: float,
		budget_usd: float,
	) -> list[dict[str, Any]]:
		warnings: list[dict[str, Any]] = []

		for forecast in weather:
			if forecast.risk_level in {RiskLevel.MEDIUM, RiskLevel.HIGH}:
				warnings.append({
					"type": "weather",
					"date": forecast.date.isoformat(),
					"level": forecast.risk_level.value,
					"message": forecast.recommendation or f"Monitor {forecast.condition.lower()} conditions.",
				})

		if total_estimated_cost > budget_usd:
			warnings.append({
				"type": "budget",
				"level": "high",
				"message": "Current itinerary exceeds budget. Consider lowering hotel or activity spend.",
				"delta_usd": round(total_estimated_cost - budget_usd, 2),
			})

		return warnings

	def _build_contingencies(
		self,
		risk_warnings: list[dict[str, Any]],
		hotel: HotelOption | None,
	) -> list[dict[str, Any]]:
		contingencies: list[dict[str, Any]] = []

		for warning in risk_warnings:
			if warning["type"] == "weather":
				contingencies.append({
					"trigger": f"Weather risk on {warning['date']}",
					"fallback": "Swap outdoor sightseeing for museums, food halls, or covered markets.",
				})
			if warning["type"] == "budget" and hotel is not None:
				contingencies.append({
					"trigger": "Budget overrun",
					"fallback": f"Replace {hotel.name} with a lower nightly-rate property or trim one paid activity.",
				})

		if not contingencies:
			contingencies.append({
				"trigger": "Minor itinerary disruption",
				"fallback": "Use the free afternoon buffer to absorb delays or weather changes.",
			})

		return contingencies

	def _calculate_feasibility(
		self,
		trip_input: TripInput,
		weather: list[WeatherForecast],
		total_estimated_cost: float,
		has_flights: bool,
		has_hotel: bool,
	) -> float:
		score = 100.0
		if not has_flights:
			score -= 20
		if not has_hotel:
			score -= 20

		high_risk_days = sum(1 for forecast in weather if forecast.risk_level == RiskLevel.HIGH)
		score -= high_risk_days * 6

		if total_estimated_cost > trip_input.budget_usd:
			overrun_ratio = (total_estimated_cost - trip_input.budget_usd) / trip_input.budget_usd
			score -= min(overrun_ratio * 100, 35)

		return round(max(score, 0), 2)

	def _build_attraction(self, raw: dict[str, Any], destination: str, index: int) -> Attraction:
		category = self._map_activity_type(raw.get("category", "culture"))
		name = raw.get("name", f"{destination} highlight {index + 1}")
		return Attraction(
			id=raw.get("id", f"attr-{index + 1}"),
			name=name,
			category=category,
			location=destination,
			latitude=raw.get("latitude", 0),
			longitude=raw.get("longitude", 0),
			rating=raw.get("rating", 4.2),
			estimated_duration_hours=raw.get("estimated_duration_hours", 2.0),
			entrance_fee_usd=raw.get("entrance_fee_usd", 20.0 if category != ActivityType.FOOD else 15.0),
			description=raw.get("description"),
		)

	def _fallback_attraction(self, destination: str, category: ActivityType, index: int) -> Attraction:
		names = {
			ActivityType.FOOD: f"Dinner in central {destination}",
			ActivityType.CULTURE: f"{destination} cultural walk",
			ActivityType.INDOOR: f"Indoor stop in {destination}",
		}
		return Attraction(
			id=f"fallback-{category.value}-{index}",
			name=names.get(category, f"{destination} activity"),
			category=category,
			location=destination,
			latitude=0,
			longitude=0,
			rating=4.0,
			estimated_duration_hours=2.0,
			entrance_fee_usd=15.0,
		)

	def _map_activity_type(self, category: str) -> ActivityType:
		normalized = category.lower()
		if normalized in {"museum", "gallery", "temple"}:
			return ActivityType.INDOOR
		if normalized in {"food", "restaurant", "market"}:
			return ActivityType.FOOD
		if normalized in {"park", "viewpoint", "beach"}:
			return ActivityType.OUTDOOR
		return ActivityType.CULTURE

	def _stream_event(
		self,
		event_type: str,
		payload: dict[str, Any] | None = None,
		step: AgentStep | None = None,
	) -> StreamingResponse:
		data = payload or {}
		if step is not None:
			data = {"step": step.model_dump(mode="json")}
		return StreamingResponse(type=event_type, data=data)
