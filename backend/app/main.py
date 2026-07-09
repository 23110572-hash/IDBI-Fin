"""FastAPI application entrypoint."""
from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db import init_db, session_scope
from .routers import (
    alerts_router,
    auth_router,
    bill_router,
    consent_router,
    ocen_router,
    score_router,
)

_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    _register_model_metadata()
    _warm_scorer()
    yield


def _register_model_metadata() -> None:
    """Record the active model's selected features / AUC in feature_metadata (idempotent)."""
    meta_path = Path(_settings.artifact_dir) / "model_metadata.json"
    if not meta_path.exists():
        return
    meta = json.loads(meta_path.read_text())
    from sqlalchemy import select

    from .models import FeatureMetadata
    with session_scope() as s:
        exists = s.execute(select(FeatureMetadata).where(
            FeatureMetadata.model_version == meta["model_version"])).scalar_one_or_none()
        if not exists:
            s.add(FeatureMetadata(
                model_version=meta["model_version"],
                selected_features=meta["selected_features"],
                n_features=meta["n_features"], auc_roc=meta.get("auc_roc"),
                notes="Single XGBoost decision model; WOE scorecard is a parallel artifact."))


def _warm_scorer() -> None:
    try:
        from .scoring_service import _scorer
        _scorer()
    except Exception as exc:  # model not trained yet — endpoints will surface a clear error
        print(f"[startup] scorer not warmed: {exc}. Run `python -m msme_ml.train` in /ml.")


app = FastAPI(
    title=_settings.app_name,
    version="0.1.0",
    description=(
        "MSME Financial Health Card — single XGBoost decision model (Score = 100·(1−PD)), SHAP "
        "reason codes + 5 grouped sub-scores, parallel WOE scorecard, AA-first / OCEN-compliant. "
        "Two modes: A (origination, real-time) and B (portfolio monitoring, batch)."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_list(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

for r in (auth_router.router, consent_router.router, score_router.router, ocen_router.router,
          bill_router.router, alerts_router.router):
    app.include_router(r)


@app.get("/", tags=["health"])
async def root():
    return {"service": _settings.app_name, "docs": "/docs", "health": "/healthz"}


@app.get("/healthz", tags=["health"])
async def healthz():
    meta_path = Path(_settings.artifact_dir) / "model_metadata.json"
    model_ready = meta_path.exists()
    model_version = None
    auc = None
    if model_ready:
        meta = json.loads(meta_path.read_text())
        model_version = meta.get("model_version")
        auc = meta.get("auc_roc")
    return {
        "status": "ok",
        "environment": _settings.environment,
        "model_ready": model_ready,
        "model_version": model_version,
        "auc_roc": auc,
        "security": {
            "auth_enabled": _settings.auth_enabled,
            "jwt_secret_configured": bool(_settings.jwt_secret),
            "warning": None if _settings.jwt_secret else
            "Using an ephemeral dev JWT secret. Set MSME_JWT_SECRET in non-local environments.",
        },
    }
