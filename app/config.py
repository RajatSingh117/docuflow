import os
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    APP_NAME: str = "DocuFlow"
    APP_ENV: str = "development"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    SECRET_KEY: str = "docuflow-secret-key-development-mode-secure-2026"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    DATABASE_URL: str = "sqlite:///./docuflow.db"
    STORAGE_DIR: str = "./storage"
    MAX_UPLOAD_SIZE_MB: int = 20

    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"
    TESSERACT_CMD: str = "tesseract"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def uploads_path(self) -> Path:
        path = Path(self.STORAGE_DIR) / "uploads"
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def reports_path(self) -> Path:
        path = Path(self.STORAGE_DIR) / "reports"
        path.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
