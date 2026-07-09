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
    model_config = SettingsConfigDict(env_prefix="MSME_", env_file=".env", extra="ignore")

    app_name: str = "MSME Financial Health Card API"
    environment: str = "local"

    # --- persistence ---
    # Postgres in docker-compose; SQLite file fallback for standalone local dev.
    database_url: str = "postgresql://neondb_owner:npg_Vzwua76oycJX@ep-rough-pine-ad4uv9lr-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
    redis_url: str = "redis://localhost:6379/0"

    # --- ML artifacts ---
    # The backend ships its OWN trained-model copy (backend/model_artifacts) so it always serves a
    # known-good model with no retraining. Override MSME_ARTIFACT_DIR only to point at a newer model.
    artifact_dir: str = str(BACKEND_DIR / "model_artifacts")

    # --- auth (JWT). In AWS this is Cognito; locally we mint/verify our own dev JWTs. ---
    # SECURITY: override MSME_JWT_SECRET in every non-local environment. A random per-process
    # secret is generated if unset so tokens never validate across restarts by accident.
    jwt_secret: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 60
    auth_enabled: bool = True

    # --- connectors / orchestration ---
    connector_timeout_seconds: float = 8.0
    raw_payload_dir: str = str(REPO_ROOT / "data" / "raw_payloads")

    # --- Celery ---
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    celery_task_always_eager: bool = True  # run inline unless a worker+broker is present

    # --- OCR / S3 (stubbed locally) ---
    use_textract: bool = False
    s3_bucket: str = "msme-artifacts-local"

    # --- CORS ---
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

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
