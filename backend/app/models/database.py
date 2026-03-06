"""
VoyageMind Database Models and Configuration

Defines SQLAlchemy ORM models for persistent storage.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Boolean, JSON, Enum, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
import enum

from app.config import get_settings

# Database configuration
settings = get_settings()
DATABASE_URL = settings.database.url

engine = create_engine(
    DATABASE_URL,
    echo=settings.database.echo,
    pool_size=settings.database.pool_size,
    max_overflow=settings.database.max_overflow,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ==================== Enums ====================

class TravelerTypeEnum(str, enum.Enum):
    """Traveler type enum"""
    SOLO = "solo"
    COUPLE = "couple"
    FAMILY = "family"
    GROUP = "group"


class ActivityTypeEnum(str, enum.Enum):
    """Activity type enum"""
    ADVENTURE = "adventure"
    CULTURE = "culture"
    RELAXATION = "relaxation"
    FOOD = "food"
    NIGHTLIFE = "nightlife"
    INDOOR = "indoor"
    OUTDOOR = "outdoor"


class RiskLevelEnum(str, enum.Enum):
    """Risk level enum"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


# ==================== Database Models ====================

class User(Base):
    """User model for persistent storage"""
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(String(255), index=True, nullable=True)
    preferences = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    trips = relationship("Trip", back_populates="user", cascade="all, delete-orphan")
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, email={self.email})>"


class Session(Base):
    """User session model"""
    __tablename__ = "sessions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    conversation_history = Column(JSON, default=[])
    current_trip_id = Column(String, ForeignKey("trips.id"), nullable=True)
    preferences = Column(JSON, default={})
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_accessed_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="sessions")
    trip = relationship("Trip", back_populates="sessions")

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id})>"


class Trip(Base):
    """Travel trip model"""
    __tablename__ = "trips"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    destination = Column(String(255), nullable=False)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    budget_usd = Column(Float, nullable=False)
    travelers_count = Column(Integer, default=1, nullable=False)
    traveler_type = Column(Enum(TravelerTypeEnum), default=TravelerTypeEnum.SOLO)
    interests = Column(JSON, default=[])
    special_requirements = Column(Text, nullable=True)
    feasibility_score = Column(Float, default=0)
    status = Column(String(50), default="planning")  # planning, confirmed, completed, cancelled
    plan_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="trips")
    sessions = relationship("Session", back_populates="trip")
    itineraries = relationship("Itinerary", back_populates="trip", cascade="all, delete-orphan")
    flights = relationship("Flight", back_populates="trip", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Trip(id={self.id}, destination={self.destination}, user_id={self.user_id})>"


class Itinerary(Base):
    """Daily itinerary for a trip"""
    __tablename__ = "itineraries"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False)
    day_number = Column(Integer, nullable=False)
    date = Column(DateTime, nullable=False)
    morning_activity = Column(JSON, nullable=True)
    afternoon_activity = Column(JSON, nullable=True)
    evening_activity = Column(JSON, nullable=True)
    hotel = Column(JSON, nullable=True)
    estimated_cost_usd = Column(Float, default=0)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    trip = relationship("Trip", back_populates="itineraries")

    def __repr__(self):
        return f"<Itinerary(id={self.id}, trip_id={self.trip_id}, day={self.day_number})>"


class Flight(Base):
    """Flight booking record"""
    __tablename__ = "flights"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=False)
    flight_type = Column(String(20), nullable=False)  # outbound, return
    airline = Column(String(100), nullable=False)
    flight_number = Column(String(20), nullable=False)
    departure_time = Column(DateTime, nullable=False)
    arrival_time = Column(DateTime, nullable=False)
    departure_airport = Column(String(10), nullable=False)
    arrival_airport = Column(String(10), nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    price_per_person = Column(Float, nullable=False)
    stops = Column(Integer, default=0)
    is_booked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    trip = relationship("Trip", back_populates="flights")

    def __repr__(self):
        return f"<Flight(id={self.id}, flight_number={self.flight_number})>"


class Hotel(Base):
    """Hotel booking record"""
    __tablename__ = "hotels"

    id = Column(String, primary_key=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    price_per_night = Column(Float, nullable=False)
    rating = Column(Float, nullable=True)
    amenities = Column(JSON, default=[])
    distance_to_center_km = Column(Float, nullable=True)
    image_url = Column(String(500), nullable=True)
    booking_url = Column(String(500), nullable=True)
    is_booked = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Hotel(id={self.id}, name={self.name}, location={self.location})>"


class Attraction(Base):
    """Tourist attraction/activity"""
    __tablename__ = "attractions"

    id = Column(String, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    category = Column(Enum(ActivityTypeEnum), nullable=False)
    location = Column(String(255), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    rating = Column(Float, nullable=True)
    opening_hours = Column(String(255), nullable=True)
    estimated_duration_hours = Column(Float, nullable=True)
    entrance_fee_usd = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<Attraction(id={self.id}, name={self.name}, category={self.category})>"


class WeatherData(Base):
    """Cached weather forecast data"""
    __tablename__ = "weather_data"

    id = Column(String, primary_key=True, index=True)
    location = Column(String(255), nullable=False, index=True)
    forecast_date = Column(DateTime, nullable=False)
    temp_high_c = Column(Float, nullable=False)
    temp_low_c = Column(Float, nullable=False)
    condition = Column(String(100), nullable=False)
    precipitation_chance = Column(Float, default=0)
    wind_speed_kmh = Column(Float, nullable=False)
    risk_level = Column(Enum(RiskLevelEnum), default=RiskLevelEnum.LOW)
    recommendation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)

    def __repr__(self):
        return f"<WeatherData(location={self.location}, date={self.forecast_date})>"


class AgentLog(Base):
    """Log of agent actions and reasoning"""
    __tablename__ = "agent_logs"

    id = Column(String, primary_key=True, index=True)
    session_id = Column(String, ForeignKey("sessions.id"), nullable=True, index=True)
    trip_id = Column(String, ForeignKey("trips.id"), nullable=True, index=True)
    step_number = Column(Integer, nullable=False)
    action = Column(String(100), nullable=False)
    reasoning = Column(Text, nullable=True)
    tool_input = Column(JSON, nullable=True)
    tool_output = Column(JSON, nullable=True)
    status = Column(String(50), nullable=False)  # success, error, pending
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<AgentLog(id={self.id}, action={self.action}, status={self.status})>"


# ==================== Database Functions ====================

def get_db():
    """
    Dependency for getting database session.
    
    Yields:
        SessionLocal: Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all database tables (use with caution!)"""
    Base.metadata.drop_all(bind=engine)


def reset_database():
    """Reset database (drop and recreate all tables)"""
    drop_tables()
    create_tables()
