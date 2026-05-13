from pathlib import Path
from pydantic import BaseModel
import os
from datetime import timedelta

_backend_dir = Path(__file__).resolve().parent.parent
try:
    from dotenv import load_dotenv

    load_dotenv(_backend_dir / ".env")
except ImportError:
    pass

# Default: local PostgreSQL (Docker) — database runs separately from the API process.
# From repo root: `docker compose up -d` then start the API from backend/.
# Override with DATABASE_URL in backend/.env (see env.example). For SQLite only, set DATABASE_URL to a sqlite:///... URL.
_DEFAULT_POSTGRES = "postgresql://school:school@127.0.0.1:5432/school_management"


class Settings(BaseModel):
    app_name: str = "School Management API"
    secret_key: str = os.getenv("APP_SECRET_KEY", "super-secret-key")
    access_token_expire_minutes: int = 60 * 8
    algorithm: str = "HS256"
    database_url: str = os.getenv("DATABASE_URL") or _DEFAULT_POSTGRES
    allow_origins: list[str] = ["*"]  # Allow all origins for local network access

    @property
    def access_token_expiry(self) -> timedelta:
        return timedelta(minutes=self.access_token_expire_minutes)


settings = Settings()

