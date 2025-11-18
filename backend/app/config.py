import os
from typing import Optional

class Config:
    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://aismsuser:aismspass@localhost:5432/aismsdb")
    
    # Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    
    # Security
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    INGEST_API_KEY: str = os.getenv("INGEST_API_KEY", "dev-ingest-key")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days
    
    # Paths
    BASE_DIR: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    MODEL_PATH: str = os.getenv("MODEL_PATH", os.path.join(BASE_DIR, "models", "emotion_model.pt"))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    SESSION_LOG: str = os.path.join(DATA_DIR, "session_data.jsonl")
    
    # Backend URL
    INGEST_URL: str = os.getenv("INGEST_URL", "http://localhost:8001")
    
    # CORS
    ALLOWED_ORIGINS: list = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]

config = Config()