"""Weather tool with resilient mock fallback forecasts."""

from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from typing import Any

from app.config import get_settings

logger = logging.getLogger(__name__)

WEATHER_TOOL_SCHEMA: dict[str, Any] = {
	"toolSpec": {
		"name": "get_weather_forecast",
		"description": "Get a daily weather forecast for a destination.",
		"inputSchema": {
			"json": {
				"type": "object",
				"properties": {
					"location": {"type": "string"},
					"start_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
					"end_date": {"type": "string", "description": "ISO date YYYY-MM-DD"},
				},
				"required": ["location", "start_date", "end_date"],
			}
		},
	}
}

CITY_BASELINE = {
	"paris": 20,
	"london": 17,
	"tokyo": 24,
	"new york": 22,
	"rome": 25,
}

CITY_PATTERNS = {
	"paris": ["Clouds", "Rain", "Clear", "Clouds", "Clear"],
	"london": ["Rain", "Clouds", "Clouds", "Clear", "Rain"],
	"tokyo": ["Clear", "Clouds", "Rain", "Clear", "Clouds"],
	"new york": ["Clear", "Clouds", "Rain", "Clouds", "Clear"],
	"rome": ["Clear", "Clear", "Clouds", "Rain", "Clear"],
}


class WeatherTool:
	"""Weather forecast provider with a local deterministic fallback."""

	async def get_forecast(
		self,
		location: str,
		start_date: date | str,
		end_date: date | str,
	) -> list[dict[str, Any]]:
		settings = get_settings()
		start = self._coerce_date(start_date)
		end = self._coerce_date(end_date)

		if settings.mock_mode or not settings.openweather_api_key:
			return self._mock_forecast(location, start, end)

		logger.warning("Live weather integration is unavailable; falling back to mock forecast")
		return self._mock_forecast(location, start, end)

	def _mock_forecast(self, location: str, start_date: date, end_date: date) -> list[dict[str, Any]]:
		location_key = self._location_key(location)
		base_temp = CITY_BASELINE.get(location_key, 21)
		pattern = CITY_PATTERNS.get(location_key, ["Clear", "Clouds", "Rain", "Clear"])
		forecast = []
		total_days = (end_date - start_date).days

		for day_offset in range(total_days):
			current_day = start_date + timedelta(days=day_offset)
			condition = pattern[day_offset % len(pattern)]
			precipitation = 75 if condition == "Rain" else 25 if condition == "Clouds" else 5
			risk_level = "high" if precipitation >= 70 else "medium" if precipitation >= 25 else "low"
			forecast.append({
				"date": current_day.isoformat(),
				"temp_high_c": base_temp + (day_offset % 4),
				"temp_low_c": base_temp - 6 + (day_offset % 3),
				"condition": condition,
				"precipitation_chance": precipitation,
				"wind_speed_kmh": 10 + (day_offset * 3),
				"risk_level": risk_level,
				"recommendation": self._recommendation_for(condition, risk_level),
			})

		logger.info("Mock weather: %d forecast day(s) for %s", len(forecast), location)
		return forecast

	def _coerce_date(self, value: date | str) -> date:
		if isinstance(value, date):
			return value
		return datetime.fromisoformat(value).date()

	def _location_key(self, location: str) -> str:
		location_lower = location.lower()
		for key in CITY_BASELINE:
			if key in location_lower:
				return key
		return location_lower.strip()

	def _recommendation_for(self, condition: str, risk_level: str) -> str:
		if risk_level == "high":
			return "Plan indoor activities and leave buffer time for disruptions."
		if condition == "Clouds":
			return "Carry a light layer and keep a backup indoor stop nearby."
		return "Outdoor activities are reasonable for most of the day."
