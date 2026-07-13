"""Pydantic v2 request/response schemas. The OCEN endpoint is an untrusted-input boundary — all
external input is strictly validated here."""
from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

# Indian identifier patterns (format validation only)
GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
URN_RE = re.compile(r"^UDYAM-[A-Z]{2}-[0-9]{2}-[0-9]{7}$")


class BorrowerIdentifiers(BaseModel):
    """Applicant identifiers submitted at origination (Mode A)."""
    urn: str = Field(..., description="Udyam Registration Number, e.g. UDYAM-MH-03-1234567")
    pan: str = Field(..., description="Business PAN")
    gstin: str | None = Field(None, description="GSTIN (optional; NTC firms may lack it)")
    business_name: str | None = Field(None, max_length=200)

    @field_validator("urn")
    @classmethod
    def _urn(cls, v: str) -> str:
        v = v.strip().upper()
        if not URN_RE.match(v):
            raise ValueError("URN must match UDYAM-XX-00-0000000")
        return v

    @field_validator("pan")
    @classmethod
    def _pan(cls, v: str) -> str:
        v = v.strip().upper()
        if not PAN_RE.match(v):
            raise ValueError("PAN must match AAAAA0000A")
        return v

    @field_validator("gstin")
    @classmethod
    def _gstin(cls, v: str | None) -> str | None:
        if v is None or v == "":
            return None
        v = v.strip().upper()
        if not GSTIN_RE.match(v):
            raise ValueError("GSTIN format invalid")
        return v


class ScoreRequest(BaseModel):
    identifiers: BorrowerIdentifiers
    consent_id: str | None = Field(None, description="Existing AA consent id; created if absent")
    include_scorecard: bool = True


class ReasonCode(BaseModel):
    feature: str
    label: str
    category: str
    shap: float
    direction: str
    impact: str
    value: float | None
    actionable: bool
    unit: str


class Pillar(BaseModel):
    pillar: str
    label: str
    primary_source: str
    sub_score: float
    display_weight: float
    base_weight: float
    available: bool


class HealthCard(BaseModel):
    pd: float
    composite_score: float
    tier: str
    tier_label: str
    action: str
    segment_label: str
    confidence: float
    pillars: list[Pillar]
    reason_codes: list[ReasonCode]
    model_version: str
    available_sources: dict[str, bool]


class ScoreResponse(BaseModel):
    score_id: str
    urn: str
    business_name: str | None
    mode: Literal["origination", "monitoring"] = "origination"
    latency_ms: int
    health_card: HealthCard
    scorecard: dict[str, Any] | None = None
    data_quality: dict[str, Any] | None = None
    created_at: str


# ---------------- OCEN ----------------
class OCENAssessRequest(BaseModel):
    """OCEN-style credit-assessment request from an LSP on ONDC (untrusted boundary)."""
    borrower: BorrowerIdentifiers
    loan_amount: float | None = Field(None, ge=0)
    tenure_months: int | None = Field(None, ge=1, le=360)
    purpose: str | None = Field(None, max_length=200)
    lsp_id: str = Field(..., max_length=64)


class OCENAssessResponse(BaseModel):
    assessment_id: str
    borrower_urn: str
    credit_score: float
    probability_of_default: float
    risk_tier: str
    recommended_action: str
    sub_scores: dict[str, float]
    reason_codes: list[dict[str, Any]]
    confidence: float
    model_version: str
    disclaimer: str


# ---------------- Consent ----------------
class ConsentRequest(BaseModel):
    identifiers: BorrowerIdentifiers
    purpose: str = Field("credit_assessment", max_length=100)
    fi_types: list[str] = Field(default_factory=lambda: ["DEPOSIT", "GST", "EPFO"])
    duration_days: int = Field(90, ge=1, le=365)


class ConsentResponse(BaseModel):
    consent_id: str
    consent_handle: str
    status: str
    purpose: str
    urn: str
    fi_types: list[str]
    created_at: str
    expires_at: str


# ---------------- Auth ----------------
class LoginRequest(BaseModel):
    username: str
    password: str


class RegisterRequest(BaseModel):
    """New-user sign-up (untrusted input — validated here)."""
    username: str = Field(..., min_length=3, max_length=64)
    password: str = Field(..., min_length=6, max_length=128)
    role: Literal["rm", "credit_officer", "admin"] = "rm"


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    expires_in: int


# ---------------- Alerts ----------------
class Alert(BaseModel):
    alert_id: str
    urn: str
    type: str
    severity: str
    message: str
    suggested_action: str
    created_at: str
