"""Backend settings (12-factor, env-driven). No secrets in code — defaults are dev-only."""
from __future__ import annotations

import os
import secrets
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="MSME_", env_file=str(REPO_ROOT / ".env"),
                                      extra="ignore")

    app_name: str = "IDBIFin API"
    environment: str = "development"

    # --- persistence ---
    # Neon Postgres, supplied via MSME_DATABASE_URL (repo-root .env locally, Render env vars in
    # production). No hardcoded credentials and no local fallback — a real database is required.
    database_url: str = ""

    # --- ML artifacts ---
    # The backend ships its OWN trained-model copy (backend/model_artifacts) so it always serves a
    # known-good model with no retraining. Override MSME_ARTIFACT_DIR only to point at a newer model.
    artifact_dir: str = str(BACKEND_DIR / "model_artifacts")

    # --- auth (JWT / HS256) ---
    # SECURITY: set MSME_JWT_SECRET in every deployed environment (Render generates one via
    # render.yaml). If unset, a random per-process secret is generated so tokens never validate
    # across restarts by accident.
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60
    auth_enabled: bool = True

    # --- connectors / orchestration ---
    connector_timeout_seconds: float = 8.0
    raw_payload_dir: str = str(REPO_ROOT / "data" / "raw_payloads")

    # --- Celery (background + Mode-B jobs) ---
    # Runs tasks inline (eager) with an in-memory broker, so no external queue is required.
    celery_broker_url: str = "memory://"
    celery_result_backend: str = "cache+memory://"
    celery_task_always_eager: bool = True  # run inline; no separate worker/broker needed

    # --- CORS (allowed frontend origins, comma-separated) ---
    # Set MSME_CORS_ORIGINS to the deployed Vercel frontend URL(s).
    cors_origins: str = "https://idbi-fin.vercel.app"

    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def effective_jwt_secret(self) -> str:
        if self.jwt_secret:
            return self.jwt_secret
        # ephemeral dev secret (process-local); warns via /healthz.security
        return os.environ.setdefault("_MSME_EPHEMERAL_JWT", secrets.token_urlsafe(48))


@lru_cache
def get_settings() -> Settings:
    return Settings()
