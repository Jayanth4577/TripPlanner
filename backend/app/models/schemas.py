"""
VoyageMind Data Models and Schemas

Defines Pydantic models for API requests/responses and database entities.
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum

from pydantic import BaseModel, Field, EmailStr, validator


# ==================== Enums ====================

class TravelerType(str, Enum):
    """Type of traveler"""
    SOLO = "solo"
    COUPLE = "couple"
    FAMILY = "family"
    GROUP = "group"


class ActivityType(str, Enum):
    """Activity categories"""
    ADVENTURE = "adventure"
    CULTURE = "culture"
    RELAXATION = "relaxation"
    FOOD = "food"
    NIGHTLIFE = "nightlife"
    INDOOR = "indoor"
    OUTDOOR = "outdoor"


class RiskLevel(str, Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ==================== User & Session ====================

class UserBase(BaseModel):
    """Base user model"""
    name: str = Field(..., min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    preferences: Optional[Dict[str, Any]] = None


class UserCreate(UserBase):
    """User creation request"""
    pass


class User(UserBase):
    """User response model"""
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ==================== Trip Planning ====================

class TripInput(BaseModel):
    """Main trip planning input request"""
    
    destination: str = Field(..., description="Travel destination (city or country)")
    start_date: date = Field(..., description="Trip start date")
    end_date: date = Field(..., description="Trip end date")
    budget_usd: float = Field(..., gt=0, description="Total budget in USD")
    travelers_count: int = Field(default=1, ge=1, le=100)
    traveler_type: TravelerType = Field(default=TravelerType.SOLO)
    interests: List[ActivityType] = Field(default_factory=lambda: [ActivityType.CULTURE])
    special_requirements: Optional[str] = Field(default=None, max_length=500)
    user_id: Optional[str] = None
    
    @validator("end_date")
    def validate_dates(cls, v, values):
        """Ensure end_date is after start_date"""
        start = values.get("start_date")
        if start and v <= start:
            raise ValueError("end_date must be after start_date")
        return v

    class Config:
        json_schema_extra = {
            "example": {
                "destination": "Paris",
                "start_date": "2026-06-01",
                "end_date": "2026-06-10",
                "budget_usd": 3000,
                "travelers_count": 2,
                "traveler_type": "couple",
                "interests": ["culture", "food"],
                "special_requirements": "Vegetarian options preferred"
            }
        }


# ==================== Flight Data ====================

class FlightSegment(BaseModel):
    """Single flight segment"""
    departure_airport: str
    arrival_airport: str
    departure_time: datetime
    arrival_time: datetime
    airline: str
    flight_number: str
    duration_minutes: int
    price_per_person: float


class FlightOption(BaseModel):
    """Complete flight itinerary (possibly with connections)"""
    segments: List[FlightSegment]
    total_price_per_person: float
    total_duration_minutes: int
    stops: int
    is_direct: bool

    class Config:
        from_attributes = True


# ==================== Hotel Data ====================

class HotelOption(BaseModel):
    """Hotel accommodation option"""
    id: str
    name: str
    location: str
    price_per_night: float
    rating: Optional[float] = Field(None, ge=0, le=5)
    amenities: List[str] = Field(default_factory=list)
    distance_to_center_km: Optional[float] = None
    image_url: Optional[str] = None
    booking_url: Optional[str] = None

    class Config:
        from_attributes = True


# ==================== Weather Data ====================

class WeatherForecast(BaseModel):
    """Weather forecast for a specific day"""
    date: date
    temp_high_c: float
    temp_low_c: float
    condition: str
    precipitation_chance: float = Field(0, ge=0, le=100)
    wind_speed_kmh: float
    risk_level: RiskLevel = RiskLevel.LOW
    recommendation: Optional[str] = None


# ==================== Activity & Attraction ====================

class Attraction(BaseModel):
    """Tourist attraction or activity"""
    id: str
    name: str
    category: ActivityType
    location: str
    latitude: float
    longitude: float
    rating: Optional[float] = Field(None, ge=0, le=5)
    opening_hours: Optional[str] = None
    estimated_duration_hours: Optional[float] = None
    entrance_fee_usd: Optional[float] = None
    description: Optional[str] = None


class DailyItinerary(BaseModel):
    """Single day's itinerary"""
    date: date
    morning_activity: Optional[Attraction] = None
    afternoon_activity: Optional[Attraction] = None
    evening_activity: Optional[Attraction] = None
    hotel: Optional[HotelOption] = None
    estimated_cost_usd: float = 0
    notes: Optional[str] = None


# ==================== Travel Plan ====================

class TravelPlan(BaseModel):
    """Complete travel plan generated by orchestrator"""
    id: str
    trip_input: TripInput
    itinerary: List[DailyItinerary]
    flights_outbound: Optional[FlightOption] = None
    flights_return: Optional[FlightOption] = None
    total_cost_breakdown: Dict[str, float]
    total_estimated_cost: float
    budget_remaining: float
    feasibility_score: float = Field(ge=0, le=100)
    risk_warnings: List[Dict[str, Any]] = Field(default_factory=list)
    contingency_plans: Optional[List[Dict[str, Any]]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Config:
        from_attributes = True


class TravelPlanResponse(TravelPlan):
    """Travel plan response for API"""
    pass


# ==================== Streaming & Agent Response ====================

class AgentStep(BaseModel):
    """Single reasoning step from agent"""
    step_number: int
    action: str  # e.g., "search_flights", "analyze_weather"
    reasoning: str
    tool_input: Optional[Dict[str, Any]] = None
    tool_output: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class StreamingResponse(BaseModel):
    """Base model for streaming responses"""
    type: str  # "step", "update", "plan", "error"
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ==================== Session & Memory ====================

class SessionData(BaseModel):
    """User session data"""
    session_id: str
    user_id: str
    current_trip: Optional[str] = None
    conversation_history: List[Dict[str, str]] = Field(default_factory=list)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    last_accessed_at: datetime

    class Config:
        from_attributes = True


# ==================== Error Responses ====================

class ErrorResponse(BaseModel):
    """Error response model"""
    status: str = "error"
    message: str
    error_code: str
    details: Optional[Dict[str, Any]] = None


class ValidationError(ErrorResponse):
    """Validation error response"""
    status: str = "validation_error"
