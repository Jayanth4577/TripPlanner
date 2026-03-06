"""
VoyageMind Backend Configuration Module

Loads and validates all environment variables using Pydantic.
Provides centralized configuration access throughout the application.
"""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings
from pydantic import Field, validator


class AWSConfig(BaseSettings):
    """AWS and Bedrock Configuration"""
    
    access_key_id: str = Field(..., alias="AWS_ACCESS_KEY_ID")
    secret_access_key: str = Field(..., alias="AWS_SECRET_ACCESS_KEY")
    region: str = Field(default="us-east-1", alias="AWS_REGION")
    bedrock_region: str = Field(default="us-east-1", alias="BEDROCK_REGION")
    bedrock_model_id: str = Field(default="nova-pro", alias="BEDROCK_MODEL_ID")

    class Config:
        env_file = ".env"
        case_sensitive = False


class DatabaseConfig(BaseSettings):
    """Database Configuration"""
    
    url: str = Field(default="sqlite:///./voyagemind.db", alias="DATABASE_URL")
    echo: bool = Field(default=False)
    pool_size: int = 20
    max_overflow: int = 10

    class Config:
        env_file = ".env"
        case_sensitive = False


class RedisConfig(BaseSettings):
    """Redis/Cache Configuration"""
    
    url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    ttl: int = Field(default=3600, alias="REDIS_TTL")
    max_connections: int = 50

    class Config:
        env_file = ".env"
        case_sensitive = False


class APIConfig(BaseSettings):
    """FastAPI Configuration"""
    
    host: str = Field(default="0.0.0.0", alias="API_HOST")
    port: int = Field(default=8000, alias="API_PORT")
    log_level: str = Field(default="info", alias="API_LOG_LEVEL")
    reload: bool = True
    workers: int = 1

    class Config:
        env_file = ".env"
        case_sensitive = False


class ExternalAPIsConfig(BaseSettings):
    """External APIs Configuration"""
    
    openweather_api_key: str = Field(default="", alias="OPENWEATHER_API_KEY")
    amadeus_client_id: str = Field(default="", alias="AMADEUS_CLIENT_ID")
    amadeus_client_secret: str = Field(default="", alias="AMADEUS_CLIENT_SECRET")

    class Config:
        env_file = ".env"
        case_sensitive = False


class SecurityConfig(BaseSettings):
    """Security Configuration"""
    
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")

    class Config:
        env_file = ".env"
        case_sensitive = False


class LoggingConfig(BaseSettings):
    """Logging Configuration"""
    
    level: str = Field(default="INFO", alias="LOG_LEVEL")
    format: str = Field(default="json", alias="LOG_FORMAT")

    class Config:
        env_file = ".env"
        case_sensitive = False


class Settings(BaseSettings):
    """Main Settings Class - Aggregates all configurations"""
    
    # Environment
    environment: Literal["development", "staging", "production"] = Field(
        default="development", alias="ENVIRONMENT"
    )
    debug: bool = Field(default=True, alias="DEBUG")
    
    # Sub-configurations
    aws: AWSConfig = Field(default_factory=AWSConfig)
    database: DatabaseConfig = Field(default_factory=DatabaseConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    external_apis: ExternalAPIsConfig = Field(default_factory=ExternalAPIsConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @validator("debug", always=True)
    def set_debug_mode(cls, v, values):
        """Set debug mode based on environment"""
        env = values.get("environment", "development")
        return env == "development"

    class Config:
        env_file = ".env"
        case_sensitive = False
        nested_init_by_alias = True


@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Uses lru_cache to ensure single instance throughout application.
    
    Returns:
        Settings: Configured settings instance
    """
    return Settings()
