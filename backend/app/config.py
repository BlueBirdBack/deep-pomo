import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    PROJECT_NAME: str = "DeepPomo"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://postgres:postgres@localhost/pomodoro_app"
    )

    # CORS settings
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:3000",  # Next.js frontend
        "http://localhost:8000",  # FastAPI backend
    ]


settings = Settings()
