from typing import Optional, Dict, List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application configuration settings."""
    MONGO_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "fraud_shield_ai"
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "gemini" # Options: gemini, openai
    WS_BROADCAST_INTERVAL: float = 1.0
    CORS_ORIGINS: List[str] = ["*"]
    LOG_LEVEL: str = "INFO"

    # JWT Auth
    JWT_SECRET: str = "change-me-in-production-use-openssl-rand-hex-32"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480  # 8 hours
    
    FUSION_WEIGHTS: Dict[str, float] = {
        "xgboost": 0.55,
        "isolation_forest": 0.20,
        "rule_engine": 0.15,
        "graph": 0.10
    }
    
    DECISION_THRESHOLDS: Dict[str, float] = {
        "block": 0.80,
        "flag": 0.50
    }

    model_config = SettingsConfigDict(
        env_prefix="FRAUD_SHIELD_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()


def get_settings() -> Settings:
    """Get the application settings singleton."""
    return settings
