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
    
    FUSION_WEIGHTS: Dict[str, float] = {
        "xgboost": 0.4,
        "isolation_forest": 0.2,
        "rule_engine": 0.25,
        "graph": 0.15
    }
    
    DECISION_THRESHOLDS: Dict[str, float] = {
        "block": 0.75,
        "flag": 0.45
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
