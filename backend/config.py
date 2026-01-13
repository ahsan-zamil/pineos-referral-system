"""Application configuration using Pydantic settings."""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    DATABASE_URL: str = "postgresql://pineos:pineos_password@localhost:5432/pineos_referral"
    TEST_DATABASE_URL: str = "postgresql://pineos:pineos_password@localhost:5432/pineos_referral_test"
    
    # API
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    API_V1_PREFIX: str = "/api/v1"
    
    # Security
    SECRET_KEY: str = "your-secret-key-here-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # Optional: OpenAI for bonus feature
    OPENAI_API_KEY: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Global settings instance
settings = Settings()
