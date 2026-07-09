"""ORM models: Consent Registry, append-only Score Ledger, Feature Metadata, Alerts.

The Score Ledger is append-only by policy: the service layer only ever INSERTs. Every score is
reproducible from its feature_snapshot + model_version (audit / RBI requirement).
"""
from __future__ import annotations

import datetime as dt

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def _utcnow() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class ConsentRecord(Base):
    __tablename__ = "consent_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    consent_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    consent_handle: Mapped[str] = mapped_column(String(64))
    urn: Mapped[str] = mapped_column(String(32), index=True)
    pan_masked: Mapped[str] = mapped_column(String(16))
    gstin_masked: Mapped[str | None] = mapped_column(String(20), nullable=True)
    purpose: Mapped[str] = mapped_column(String(100))
    fi_types: Mapped[list] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")  # lifecycle state
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ScoreLedgerEntry(Base):
    """Append-only. Never updated or deleted."""
    __tablename__ = "score_ledger"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    score_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    urn: Mapped[str] = mapped_column(String(32), index=True)
    business_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    consent_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    mode: Mapped[str] = mapped_column(String(20), default="origination")
    model_version: Mapped[str] = mapped_column(String(64))
    pd: Mapped[float] = mapped_column(Float)
    composite_score: Mapped[float] = mapped_column(Float)
    tier: Mapped[str] = mapped_column(String(20), index=True)
    tier_label: Mapped[str] = mapped_column(String(40))
    confidence: Mapped[float] = mapped_column(Float)
    sub_scores: Mapped[dict] = mapped_column(JSON)
    reason_codes: Mapped[list] = mapped_column(JSON)
    pillars: Mapped[list] = mapped_column(JSON)
    available_sources: Mapped[dict] = mapped_column(JSON)
    feature_snapshot: Mapped[dict] = mapped_column(JSON)  # full 65-feature vector (reproducibility)
    segment: Mapped[str | None] = mapped_column(String(20), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(40), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow,
                                                    index=True)


class FeatureMetadata(Base):
    __tablename__ = "feature_metadata"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    model_version: Mapped[str] = mapped_column(String(64), index=True)
    selected_features: Mapped[list] = mapped_column(JSON)
    n_features: Mapped[int] = mapped_column(Integer)
    auc_roc: Mapped[float | None] = mapped_column(Float, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)


class AlertRecord(Base):
    __tablename__ = "alerts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    urn: Mapped[str] = mapped_column(String(32), index=True)
    type: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(Text)
    suggested_action: Mapped[str] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_utcnow,
                                                    index=True)
