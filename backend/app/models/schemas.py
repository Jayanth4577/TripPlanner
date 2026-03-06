"""Pydantic schemas for VoyageMind data models."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Shared / Common
# ---------------------------------------------------------------------------

class Coordinates(BaseModel):
    latitude: float = 0.0
    longitude: float = 0.0


# ---------------------------------------------------------------------------
# Accommodation
# ---------------------------------------------------------------------------

class AccommodationRequest(BaseModel):
    """Input for the Accommodation Agent."""

    destination: str
    check_in: date
    check_out: date
    budget: float = Field(..., gt=0, description="Total accommodation budget in USD")
    travelers: int = Field(1, ge=1)
    latitude: float = 0.0
    longitude: float = 0.0
    preferences: list[str] = Field(default_factory=list, description="e.g. ['pool', 'wifi', 'breakfast']")


class HotelOption(BaseModel):
    """A single hotel recommendation."""

    name: str
    price_per_night: float
    rating: float = 0.0
    distance_to_center_km: float = 0.0
    latitude: float = 0.0
    longitude: float = 0.0
    amenities: list[str] = Field(default_factory=list)
    reason: str = ""


class AccommodationResult(BaseModel):
    """Output from the Accommodation Agent."""

    hotels: list[HotelOption]
    reasoning: str = ""
    reasoning_steps: list[dict[str, Any]] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Attractions / Maps
# ---------------------------------------------------------------------------

class Attraction(BaseModel):
    name: str
    latitude: float
    longitude: float
    category: str = ""


class DistanceEntry(BaseModel):
    attraction_name: str
    distance_km: float


# ---------------------------------------------------------------------------
# Trip (top-level)
# ---------------------------------------------------------------------------

class TripRequest(BaseModel):
    """User-submitted trip planning request."""

    destination: str
    start_date: date
    end_date: date
    budget: float = Field(..., gt=0)
    travelers: int = Field(1, ge=1)
    preferences: list[str] = Field(default_factory=list)
    latitude: float = 0.0
    longitude: float = 0.0