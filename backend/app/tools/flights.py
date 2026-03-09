"""Flights tool with mock-first search results."""

from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

FLIGHTS_TOOL_SCHEMA: dict[str, Any] = {
	"toolSpec": {
		"name": "search_flights",
		"description": "Search for flights to a destination on a given date.",
		"inputSchema": {
			"json": {
				"type": "object",
				"properties": {
					"origin_airport": {"type": "string"},
					"destination": {"type": "string"},
					"departure_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
					"return_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
					"passengers": {"type": "integer"},
					"max_price": {"type": "number"},
				},
				"required": ["destination", "departure_date", "passengers"],
			}
		},
	}
}

DESTINATION_AIRPORTS = {
	"paris": "CDG",
	"london": "LHR",
	"tokyo": "HND",
	"new york": "JFK",
	"rome": "FCO",
}

DESTINATION_BASE_FARES = {
	"paris": 420,
	"london": 390,
	"tokyo": 920,
	"new york": 520,
	"rome": 470,
}

DESTINATION_DURATIONS = {
	"paris": 480,
	"london": 430,
	"tokyo": 840,
	"new york": 360,
	"rome": 540,
}


class FlightsTool:
	"""Flight search with deterministic mock data and safe fallback behavior."""

	async def search(
		self,
		destination: str,
		departure_date: str,
		return_date: str | None = None,
		passengers: int = 1,
		origin_airport: str = "HOME",
		max_price: float | None = None,
	) -> list[dict[str, Any]]:
		settings = get_settings()

		if settings.mock_mode or not settings.amadeus_api_key or not settings.amadeus_api_secret:
			return self._search_mock(destination, departure_date, passengers, origin_airport, max_price)

		logger.warning("Live flight search is not configured; falling back to mock results")
		return self._search_mock(destination, departure_date, passengers, origin_airport, max_price)

	def _search_mock(
		self,
		destination: str,
		departure_date: str,
		passengers: int,
		origin_airport: str,
		max_price: float | None,
	) -> list[dict[str, Any]]:
		destination_key = self._destination_key(destination)
		arrival_airport = DESTINATION_AIRPORTS.get(destination_key, "DST")
		base_fare = DESTINATION_BASE_FARES.get(destination_key, 450)
		base_duration = DESTINATION_DURATIONS.get(destination_key, 500)
		departure_time = datetime.fromisoformat(f"{departure_date}T09:00:00")

		options = [
			self._build_option(
				origin_airport=origin_airport,
				arrival_airport=arrival_airport,
				departure_time=departure_time,
				duration_minutes=base_duration,
				price_per_person=base_fare,
				airline="Voyage Air",
				flight_number="VM101",
				stops=0,
			),
			self._build_option(
				origin_airport=origin_airport,
				arrival_airport=arrival_airport,
				departure_time=departure_time + timedelta(hours=3),
				duration_minutes=base_duration + 95,
				price_per_person=max(base_fare - 80, 180),
				airline="Budget Hopper",
				flight_number="BH203",
				stops=1,
			),
			self._build_option(
				origin_airport=origin_airport,
				arrival_airport=arrival_airport,
				departure_time=departure_time + timedelta(hours=6),
				duration_minutes=base_duration + 40,
				price_per_person=base_fare + 130,
				airline="Sky Premium",
				flight_number="SP411",
				stops=0,
			),
		]

		if max_price is not None:
			capped_options = [
				option for option in options if option["total_price_per_person"] <= max_price * 1.15
			]
			if capped_options:
				options = capped_options

		logger.info(
			"Mock flights: %d options for %s on %s (%d passenger(s))",
			len(options),
			destination,
			departure_date,
			passengers,
		)
		return options

	def _build_option(
		self,
		origin_airport: str,
		arrival_airport: str,
		departure_time: datetime,
		duration_minutes: int,
		price_per_person: float,
		airline: str,
		flight_number: str,
		stops: int,
	) -> dict[str, Any]:
		arrival_time = departure_time + timedelta(minutes=duration_minutes)
		segment = {
			"departure_airport": origin_airport,
			"arrival_airport": arrival_airport,
			"departure_time": departure_time.isoformat(),
			"arrival_time": arrival_time.isoformat(),
			"airline": airline,
			"flight_number": flight_number,
			"duration_minutes": duration_minutes,
			"price_per_person": round(price_per_person, 2),
		}
		return {
			"segments": [segment],
			"total_price_per_person": round(price_per_person, 2),
			"total_duration_minutes": duration_minutes,
			"stops": stops,
			"is_direct": stops == 0,
		}

	def _destination_key(self, destination: str) -> str:
		destination_lower = destination.lower()
		for key in DESTINATION_AIRPORTS:
			if key in destination_lower:
				return key
		return destination_lower.strip()
